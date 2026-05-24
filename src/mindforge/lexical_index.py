"""v0.3 — BM25 lexical recall（纯本地词法检索）。

设计契约（详见 README.md 的 lexical recall 说明）：

1. **零依赖、纯本地**：不调用 LLM、不读 .env、不联网、不引入向量库。
2. **安全索引**：只索引 Knowledge Card 自身的安全字段与 AI 已生成的结构化
   摘要 section（``## AI Summary`` / ``## Action Items`` / ``## Principles``
   / ``## Known Risks``）。**绝不**索引：
   - 原始 source raw_text
   - ``## Source Excerpt`` 段（卡片内的原文回引片段）
   - ``## Human Note`` 段（人类私笔记）
   - prompts / completions / runs / state.json
   - .env / api key
3. **结果可解释**：``--explain`` 给出每个命中卡片在每个字段的命中 token 与
   贡献分；这是为了让用户判断"这条命中是不是噪声"。
4. **字段权重**：通过"加权词袋"近似 BM25F —— 每个字段的 token 在虚拟文档中
   按权重重复出现，再走标准 BM25。这是简洁但可解释的权衡，v0.3 不上 BM25F 全式。
5. **不污染 Knowledge Card**：构建索引完全只读。
6. **索引产物只在本地**：``.mindforge/index/bm25.json``；通过 ``.gitignore``
   防止误提交。
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .cards import CardSummary, extract_section, iter_cards, read_card_body
from .config import MindForgeConfig

SCHEMA_VERSION = 1

# 默认字段权重（v0.3 hardcoded，未来可移到 mindforge.yaml）
# 设计直觉：title / track / projects 命中比 tag / source_type 命中更"中要害"。
DEFAULT_FIELD_WEIGHTS: dict[str, float] = {
    "title": 5.0,
    "source_title": 3.0,
    "track": 4.0,
    "projects": 4.0,
    "tags": 3.0,
    "source_type": 1.0,
    "principles": 2.0,
    "known_risks": 2.0,
    "body_summary": 1.0,
    "body_actions": 1.0,
    "body_principles": 1.0,
    "body_risks": 1.0,
}

# v0.3.1 — 用户友好别名 → 内部 field 名映射。
# 这是为了让 mindforge.yaml 的 search.bm25.fields 用更直觉的 key 名，而内部
# 仍可继续用语义化 field 名做索引拆分（body_summary vs body_actions 等）。
USER_FIELD_ALIASES: dict[str, str] = {
    "title": "title",
    "source_title": "source_title",
    "learning_tracks": "track",     # YAML 用 plural；内部用 singular
    "track": "track",
    "projects": "projects",
    "tags": "tags",
    "source_type": "source_type",
    "principles": "principles",
    "known_risks": "known_risks",
    # body 段：用户配置 "summary" / "action_items" / "principles_body" / "risks_body"
    # 默认配置的 "summary" / "action_items" 关联 body_summary / body_actions
    "summary": "body_summary",
    "action_items": "body_actions",
}

# 允许从 card body 中索引的 section（白名单）。
# 任何未在此清单的 section 都不会进入索引；尤其包括 Source Excerpt 与 Human Note。
INDEXED_BODY_SECTIONS: dict[str, str] = {
    "AI Summary": "body_summary",
    "Action Items": "body_actions",
    "Principles": "body_principles",
    "Known Risks": "body_risks",
}

# BM25 超参，业内常用默认。
DEFAULT_K1 = 1.5
DEFAULT_B = 0.75


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


_ASCII_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
# CJK 范围（简化）：日韩中常用块。逐字切分以兼顾中文检索精度。
_CJK_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")

# v2.2 \u2014 \u82f1\u6587\u505c\u7528\u8bcd\u8868\uff08NLTK \u6807\u51c6\u505c\u7528\u8bcd\u5b50\u96c6\uff0c\u8986\u76d6\u6700\u5e38\u89c1\u82f1\u8bed\u529f\u80fd\u8bcd\uff09\u3002
# \u505c\u7528\u8bcd\u8fc7\u6ee4\u9ed8\u8ba4\u542f\u7528\uff0c\u53ef\u901a\u8fc7 tokenize(..., filter_stopwords=False) \u5173\u95ed\u3002
_ENGLISH_STOP_WORDS: set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "shall", "not", "no", "nor", "so", "as", "its", "it",
    "this", "that", "these", "those", "am", "each", "every", "all", "both", "few",
    "more", "most", "other", "some", "such", "only", "own", "same", "than", "too",
    "very", "just", "about", "above", "after", "again", "also", "any", "because",
    "before", "between", "into", "through", "during", "under", "over", "up", "down",
    "out", "off", "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "my", "your", "he", "she", "they", "we", "you", "him", "his", "her",
    "them", "their", "our", "me", "us", "who", "whom", "which", "what",
}


def tokenize(
    text: str,
    *,
    filter_stopwords: bool = True,
) -> list[str]:
    """ASCII 单词 + CJK 单字混合分词（小写化）。

    v0.3 最小可用分词器，v2.2 增强英文停用词过滤。

    - ASCII：按 ``[A-Za-z0-9]+`` 抓词，全部 lowercase；
    - CJK：每个汉字/假名/谚文字视为一个 token；
    - 默认过滤英文停用词（常见功能词）。

    不做 stemming / 词形还原。索引规模小（个人知识库），简单可解释。
    """
    if not text:
        return []
    out: list[str] = []
    for w in _ASCII_TOKEN_RE.findall(text):
        low = w.lower()
        if filter_stopwords and low in _ENGLISH_STOP_WORDS:
            continue
        out.append(low)
    for ch in _CJK_CHAR_RE.findall(text):
        out.append(ch)
    return out


# ---------------------------------------------------------------------------
# Indexed doc
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndexedDoc:
    """单卡的索引快照（可序列化）。

    fields：每个字段名 → token 列表。doc_len 是按 field_weights 加权后的虚拟
    文档长度（用于 BM25 长度归一化）。
    """

    rel_path: str
    id: str | None
    title: str | None
    status: str
    track: str | None
    projects: tuple[str, ...]
    tags: tuple[str, ...]
    source_type: str | None
    created_at: str | None  # ISO 字符串，避免 datetime 反序列化
    mtime: float
    fields: dict[str, list[str]] = field(default_factory=dict)
    doc_len: float = 0.0


@dataclass
class BM25Index:
    schema_version: int
    built_at: str
    field_weights: dict[str, float]
    k1: float
    b: float
    avgdl: float
    docs: list[IndexedDoc]
    tokenizer_name: str = "ascii_word_plus_cjk_char_v1"
    config_hash: str = ""              # v0.3.1：构建时的配置指纹，便于检测 stale

    # ── 持久化 ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "built_at": self.built_at,
            "tokenizer_name": self.tokenizer_name,
            "config_hash": self.config_hash,
            "field_weights": self.field_weights,
            "k1": self.k1,
            "b": self.b,
            "avgdl": self.avgdl,
            "docs": [asdict(d) for d in self.docs],
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> "BM25Index":
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != SCHEMA_VERSION:
            raise IndexFormatError(
                f"index schema_version={data.get('schema_version')} 不被本版本支持"
                f"（当前期望 {SCHEMA_VERSION}）；请重跑 `mindforge index rebuild`。"
            )
        docs = [
            IndexedDoc(
                rel_path=d["rel_path"],
                id=d.get("id"),
                title=d.get("title"),
                status=d["status"],
                track=d.get("track"),
                projects=tuple(d.get("projects") or ()),
                tags=tuple(d.get("tags") or ()),
                source_type=d.get("source_type"),
                created_at=d.get("created_at"),
                mtime=float(d.get("mtime") or 0.0),
                fields={k: list(v) for k, v in (d.get("fields") or {}).items()},
                doc_len=float(d.get("doc_len") or 0.0),
            )
            for d in data.get("docs") or []
        ]
        return cls(
            schema_version=data["schema_version"],
            built_at=data["built_at"],
            field_weights={k: float(v) for k, v in (data.get("field_weights") or DEFAULT_FIELD_WEIGHTS).items()},
            k1=float(data.get("k1") or DEFAULT_K1),
            b=float(data.get("b") or DEFAULT_B),
            avgdl=float(data.get("avgdl") or 0.0),
            docs=docs,
            tokenizer_name=str(data.get("tokenizer_name") or "ascii_word_plus_cjk_char_v1"),
            config_hash=str(data.get("config_hash") or ""),
        )


class IndexFormatError(Exception):
    pass


class IndexNotFoundError(FileNotFoundError):
    pass


# ---------------------------------------------------------------------------
# 构建索引
# ---------------------------------------------------------------------------


def build_index(
    cards: Iterable[CardSummary],
    *,
    field_weights: dict[str, float] | None = None,
    k1: float = DEFAULT_K1,
    b: float = DEFAULT_B,
    indexed_body_sections: dict[str, str] | None = None,
    config_hash: str = "",
) -> BM25Index:
    """从 CardSummary 列表构建 BM25 索引。

    安全设计：构建过程**只**调用 ``read_card_body`` + ``extract_section``，
    且 section 名严格走白名单（``INDEXED_BODY_SECTIONS``）。
    任何不在白名单的 section 永远不会进入索引（包括 Source Excerpt / Human Note）。
    """
    fw = dict(field_weights or DEFAULT_FIELD_WEIGHTS)
    body_sections = dict(indexed_body_sections or INDEXED_BODY_SECTIONS)

    docs: list[IndexedDoc] = []
    for c in cards:
        fields: dict[str, list[str]] = {}
        # frontmatter 安全字段
        if c.title:
            fields["title"] = tokenize(c.title)
        if c.source_title:
            fields["source_title"] = tokenize(c.source_title)
        if c.track:
            fields["track"] = tokenize(c.track)
        if c.projects:
            fields["projects"] = tokenize(" ".join(c.projects))
        if c.tags:
            fields["tags"] = tokenize(" ".join(c.tags))
        if c.source_type:
            fields["source_type"] = tokenize(c.source_type)
        if c.principles:
            fields["principles"] = tokenize(" ".join(c.principles))
        if c.known_risks:
            fields["known_risks"] = tokenize(" ".join(c.known_risks))

        # body 白名单 section
        try:
            body = read_card_body(c.path)
        except OSError:
            body = ""
        for section_title, field_name in body_sections.items():
            sec = extract_section(body, section_title) if body else None
            if sec:
                fields[field_name] = tokenize(sec)

        # 加权 doc_len = sum(weight * len(tokens))
        dl = 0.0
        for fname, toks in fields.items():
            dl += float(fw.get(fname, 1.0)) * len(toks)

        try:
            mtime = c.path.stat().st_mtime
        except OSError:
            mtime = 0.0

        docs.append(
            IndexedDoc(
                rel_path=c.rel_path,
                id=c.id,
                title=c.title,
                status=c.status,
                track=c.track,
                projects=tuple(c.projects),
                tags=tuple(c.tags),
                source_type=c.source_type,
                created_at=c.created_at.isoformat() if c.created_at else None,
                mtime=mtime,
                fields=fields,
                doc_len=dl,
            )
        )

    avgdl = (sum(d.doc_len for d in docs) / len(docs)) if docs else 0.0
    return BM25Index(
        schema_version=SCHEMA_VERSION,
        built_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        field_weights=fw,
        k1=k1,
        b=b,
        avgdl=avgdl,
        docs=docs,
        config_hash=config_hash,
    )


# ---------------------------------------------------------------------------
# v0.3.1 — 配置桥接：用户友好别名 → 内部 field 名；构建配置指纹
# ---------------------------------------------------------------------------


def resolve_field_weights(user_fields: dict[str, float] | None) -> dict[str, float]:
    """把 ``mindforge.yaml.search.bm25.fields`` 的"用户别名 → 权重"映射解析成
    内部 ``DEFAULT_FIELD_WEIGHTS`` 的 field 名 → 权重。

    设计：
    - 缺失或空 → 完整返回 ``DEFAULT_FIELD_WEIGHTS``（新用户零配置即可用）；
    - 命中别名 → 用用户给的权重覆盖默认；
    - 权重 == 0 → 显式从结果移除（=该字段不索引，符合 v0.3.1 协议）；
    - 未知别名 → 静默忽略（避免拼写错误把整个 search 配置打挂）。
    """
    if not user_fields:
        return dict(DEFAULT_FIELD_WEIGHTS)
    resolved: dict[str, float] = dict(DEFAULT_FIELD_WEIGHTS)
    for alias, w in user_fields.items():
        internal = USER_FIELD_ALIASES.get(alias)
        if internal is None:
            continue
        if w <= 0:
            resolved.pop(internal, None)
        else:
            resolved[internal] = float(w)
    return resolved


def compute_config_hash(
    *, field_weights: dict[str, float], k1: float, b: float,
    tokenizer_name: str = "ascii_word_plus_cjk_char_v1",
    indexed_body_sections: dict[str, str] | None = None,
) -> str:
    """v0.3.1：基于"会影响索引内容/打分"的所有配置算 sha256(8) 短指纹。

    用途：``index status`` 比对当前配置 vs 索引内 ``config_hash``；不一致 →
    stale，提示重建。**绝不**把任何卡片正文 / query / .env 加入此哈希源。
    """
    import hashlib

    payload = {
        "schema_version": SCHEMA_VERSION,
        "tokenizer": tokenizer_name,
        "field_weights": {k: round(float(v), 6) for k, v in sorted(field_weights.items())},
        "k1": round(float(k1), 6),
        "b": round(float(b), 6),
        "body_sections": dict(sorted((indexed_body_sections or INDEXED_BODY_SECTIONS).items())),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldHit:
    field: str
    term_counts: dict[str, int]   # term -> raw tf in this field
    weight: int
    contribution: float           # 该字段对该卡片总分的贡献


@dataclass(frozen=True)
class SearchHit:
    doc: IndexedDoc
    score: float
    field_hits: tuple[FieldHit, ...]


def _search_candidates(
    docs: Iterable[IndexedDoc],
    *,
    status_filter: str | None,
    track: str | None,
    project: str | None,
    tag_set: set[str],
    source_type: str | None,
    since: datetime | None,
    until: datetime | None,
) -> list[IndexedDoc]:
    """先做结构化字段过滤，再进入 BM25 打分。

    这个边界很重要：过滤只看索引内的安全元数据字段，不读取卡片正文、
    source raw_text 或任何运行态文件，保持 recall 的本地词法检索契约。
    """
    candidates: list[IndexedDoc] = []
    for d in docs:
        if status_filter is not None and d.status != status_filter:
            continue
        if track is not None and d.track != track:
            continue
        if project is not None and project not in d.projects:
            continue
        if source_type is not None and d.source_type != source_type:
            continue
        if tag_set:
            doc_tags = {t.lower() for t in d.tags}
            if not tag_set.issubset(doc_tags):
                continue
        if since is not None or until is not None:
            dt = _parse_iso(d.created_at)
            if since is not None and (dt is None or dt < since):
                continue
            if until is not None and (dt is None or dt > until):
                continue
        candidates.append(d)
    return candidates


def _idf_by_query_term(candidates: list[IndexedDoc], query_terms: list[str]) -> dict[str, float]:
    """在过滤后的候选集合上重算 IDF，让解释分数贴近当前查询范围。"""
    n_docs = len(candidates)
    query_term_set = set(query_terms)
    df: Counter[str] = Counter()
    for d in candidates:
        seen: set[str] = set()
        for toks in d.fields.values():
            for t in toks:
                if t in query_term_set:
                    seen.add(t)
        for t in seen:
            df[t] += 1
    return {
        t: math.log((n_docs - df[t] + 0.5) / (df[t] + 0.5) + 1.0)
        for t in query_terms
    }


def _score_candidate(
    index: BM25Index,
    doc: IndexedDoc,
    query_terms: list[str],
    idf: dict[str, float],
    *,
    avgdl: float,
) -> SearchHit | None:
    """计算单张卡片的 BM25 分数和字段级 explain。

    Search 的公开行为只需要一组有序命中；把单卡打分独立出来后，
    BM25 数学、字段贡献解释、外层查询编排三者各自清晰。
    """
    per_field_counts: dict[str, Counter[str]] = {}
    weighted_tf: Counter[str] = Counter()
    for fname, toks in doc.fields.items():
        w = index.field_weights.get(fname, 1)
        cnt: Counter[str] = Counter()
        for t in toks:
            if t in idf:
                cnt[t] += 1
        if cnt:
            per_field_counts[fname] = cnt
            for t, n in cnt.items():
                weighted_tf[t] += w * n

    if not weighted_tf:
        return None

    dl = doc.doc_len if doc.doc_len > 0 else 1.0
    score = 0.0
    per_term_score: dict[str, float] = {}
    for t in query_terms:
        tf = weighted_tf.get(t, 0)
        if tf == 0:
            continue
        denom = tf + index.k1 * (1.0 - index.b + index.b * dl / avgdl)
        s = idf[t] * (tf * (index.k1 + 1.0)) / denom if denom > 0 else 0.0
        per_term_score[t] = s
        score += s

    field_hits = _field_hits_from_counts(
        index=index,
        per_field_counts=per_field_counts,
        weighted_tf=weighted_tf,
        per_term_score=per_term_score,
    )
    return SearchHit(doc=doc, score=score, field_hits=tuple(field_hits))


def _field_hits_from_counts(
    *,
    index: BM25Index,
    per_field_counts: dict[str, Counter[str]],
    weighted_tf: Counter[str],
    per_term_score: dict[str, float],
) -> list[FieldHit]:
    """把总分按字段贡献近似分摊，用于 ``--explain`` 可解释输出。"""
    field_hits: list[FieldHit] = []
    for fname, cnt in per_field_counts.items():
        w = index.field_weights.get(fname, 1)
        contrib = 0.0
        for t, n in cnt.items():
            wt = weighted_tf[t]
            if wt > 0:
                contrib += per_term_score.get(t, 0.0) * (w * n) / wt
        field_hits.append(
            FieldHit(field=fname, term_counts=dict(cnt), weight=w, contribution=contrib)
        )
    field_hits.sort(key=lambda h: h.contribution, reverse=True)
    return field_hits


def search(
    index: BM25Index,
    query: str,
    *,
    status_filter: str | None = "human_approved",
    include_drafts: bool = False,
    track: str | None = None,
    project: str | None = None,
    tags: Iterable[str] = (),
    source_type: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 20,
) -> list[SearchHit]:
    """对索引执行 BM25 搜索；先 pre-filter 再打分。

    - ``include_drafts=True`` 或 ``status_filter in (None, "all")`` → 不限状态；
    - 其他过滤器与 ``filter_cards`` 语义一致；
    - 空 query 返回空（不退化为全量）；想列全量请用 ``mindforge recall`` 不带 ``--query``。
    """
    q_terms = tokenize(query)
    if not q_terms:
        return []

    eff_status = None if (include_drafts or status_filter in (None, "all")) else status_filter
    tag_set = {t.lower() for t in tags if t}
    candidates = _search_candidates(
        index.docs,
        status_filter=eff_status,
        track=track,
        project=project,
        tag_set=tag_set,
        source_type=source_type,
        since=since,
        until=until,
    )

    if not candidates:
        return []

    unique_q = list(dict.fromkeys(q_terms))   # 保序去重
    idf = _idf_by_query_term(candidates, unique_q)

    avgdl = index.avgdl or 1.0

    hits: list[SearchHit] = []
    for d in candidates:
        hit = _score_candidate(index, d, unique_q, idf, avgdl=avgdl)
        if hit is not None:
            hits.append(hit)

    hits.sort(key=lambda h: (-h.score, h.doc.rel_path))
    return hits[:limit]


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# v0.3.1 — hybrid ranking（仍是纯本地规则；不是 RAG）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HybridHit:
    """hybrid 打分结果。把 BM25 / value_score / review_due 三路分量都带回。

    设计原则：
    - **本地规则**，不是 RAG / embedding；
    - 三路分量先各自 min-max 归一到 [0,1]，再按 weights 加权求和；
    - 缺失分量按 0 处理（不失败）。
    """

    base: SearchHit
    bm25_score: float
    bm25_norm: float
    value_norm: float
    review_due_norm: float
    final_score: float


def hybrid_search(
    index: BM25Index,
    query: str,
    *,
    weights: dict[str, float] | None = None,
    cards: Iterable[CardSummary] | None = None,
    now: datetime | None = None,
    status_filter: str | None = "human_approved",
    include_drafts: bool = False,
    track: str | None = None,
    project: str | None = None,
    tags: Iterable[str] = (),
    source_type: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 20,
) -> list[HybridHit]:
    """hybrid 排序：bm25 + value_score + review_due 三路加权。

    ``cards`` 可选；如果提供，hybrid 会用 CardSummary 中的 value_score /
    review_after 做归一化（因为索引里只存安全字段子集，不存这些）。如果
    不提供，则相应分量按 0 处理。

    review_due 信号：
    - review_after <= now              → 1.0（已到期，应优先复习）
    - review_after >  now（在 30 天内）→ 1.0 - days/30
    - 缺失 / >30 天                    → 0.0
    """
    w = dict(weights or {"bm25": 0.75, "value_score": 0.15, "review_due": 0.10})
    w_bm = float(w.get("bm25", 0.0))
    w_val = float(w.get("value_score", 0.0))
    w_rev = float(w.get("review_due", 0.0))

    base_hits = search(
        index, query,
        status_filter=status_filter,
        include_drafts=include_drafts,
        track=track, project=project, tags=tags, source_type=source_type,
        since=since, until=until, limit=10_000,    # 先全集再 hybrid 排序裁剪
    )
    if not base_hits:
        return []

    # 用 CardSummary 旁路获取 value_score / review_after（索引内不存）
    extra: dict[str, CardSummary] = {}
    if cards is not None:
        for c in cards:
            extra[c.rel_path] = c

    now = now or datetime.now().astimezone()

    # min-max 归一 BM25 到 [0,1]
    bm_scores = [h.score for h in base_hits]
    bm_max = max(bm_scores) or 1.0
    bm_min = min(bm_scores)
    bm_range = (bm_max - bm_min) or 1.0

    out: list[HybridHit] = []
    for h in base_hits:
        bm_norm = (h.score - bm_min) / bm_range if bm_range > 0 else 0.0
        c = extra.get(h.doc.rel_path)
        # value_score：假设业务范围 0~10；缺失按 0
        vs = (c.value_score if (c and c.value_score is not None) else 0)
        val_norm = max(0.0, min(1.0, vs / 10.0))
        # review_due：归一到 [0,1]，30 天衰减窗口
        rev_norm = 0.0
        if c and c.review_after is not None:
            ra = c.review_after
            try:
                if ra.tzinfo is None:
                    ra = ra.astimezone()
                delta_days = (ra - now).total_seconds() / 86400.0
            except (TypeError, ValueError):
                delta_days = None
            if delta_days is not None:
                if delta_days <= 0:
                    rev_norm = 1.0
                elif delta_days < 30:
                    rev_norm = max(0.0, 1.0 - delta_days / 30.0)

        final = w_bm * bm_norm + w_val * val_norm + w_rev * rev_norm
        out.append(HybridHit(
            base=h,
            bm25_score=h.score,
            bm25_norm=bm_norm,
            value_norm=val_norm,
            review_due_norm=rev_norm,
            final_score=final,
        ))

    out.sort(key=lambda x: (-x.final_score, x.base.doc.rel_path))
    return out[:limit]


# ---------------------------------------------------------------------------
# 索引文件路径与 staleness
# ---------------------------------------------------------------------------


def default_index_path(workdir: Path) -> Path:
    """返回索引文件标准路径：<workdir>/index/bm25.json。"""
    return workdir / "index" / "bm25.json"


@dataclass(frozen=True)
class IndexStaleness:
    fresh: bool
    indexed_count: int
    current_count: int
    added: tuple[str, ...]      # rel_path 列表（仅前若干）
    removed: tuple[str, ...]
    changed: tuple[str, ...]    # mtime 漂移


@dataclass(frozen=True)
class RebuildIndexResult:
    """一次本地 BM25 index rebuild 的结构化结果。

    中文学习型说明：approve 成功后默认刷新 recall index，但这不是新的知识
    状态转换，也不接触 LLM / .env / source 原文。把 rebuild 封装成纯本地 helper，
    可以避免 CLI 和 approve 分别复制索引构建流程。
    """

    path: Path
    card_count: int
    avgdl: float
    config_hash: str
    built_at: str
    scan_error_count: int


def rebuild_index_for_config(cfg: MindForgeConfig) -> RebuildIndexResult:
    """基于当前 active vault 全量刷新本地 BM25 index；不联网、不调 LLM。"""

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    field_weights = resolve_field_weights(cfg.search.bm25.fields)
    config_hash = compute_config_hash(
        field_weights=field_weights,
        k1=cfg.search.bm25.k1,
        b=cfg.search.bm25.b,
    )
    index = build_index(
        scan.cards,
        field_weights=field_weights,
        k1=cfg.search.bm25.k1,
        b=cfg.search.bm25.b,
        config_hash=config_hash,
    )
    path = default_index_path(cfg.state.workdir)
    index.save(path)
    return RebuildIndexResult(
        path=path,
        card_count=len(index.docs),
        avgdl=index.avgdl,
        config_hash=config_hash,
        built_at=index.built_at,
        scan_error_count=len(scan.errors),
    )


def diff_index(index: BM25Index | None, current_cards: Iterable[CardSummary]) -> IndexStaleness:
    """对比索引与当前 cards，给出 added / removed / changed 列表（仅前 20 项）。

    fresh = no add/remove/change。
    """
    cur = {c.rel_path: c for c in current_cards}
    if index is None:
        return IndexStaleness(
            fresh=False,
            indexed_count=0,
            current_count=len(cur),
            added=tuple(sorted(cur)[:20]),
            removed=(),
            changed=(),
        )
    indexed = {d.rel_path: d for d in index.docs}
    added = sorted(set(cur) - set(indexed))
    removed = sorted(set(indexed) - set(cur))
    changed: list[str] = []
    for rp, d in indexed.items():
        cc = cur.get(rp)
        if cc is None:
            continue
        try:
            cur_mtime = cc.path.stat().st_mtime
        except OSError:
            continue
        # 1 秒容差，规避 fs mtime 精度
        if abs(cur_mtime - d.mtime) > 1.0:
            changed.append(rp)
    fresh = not (added or removed or changed)
    return IndexStaleness(
        fresh=fresh,
        indexed_count=len(indexed),
        current_count=len(cur),
        added=tuple(added[:20]),
        removed=tuple(removed[:20]),
        changed=tuple(sorted(changed)[:20]),
    )


__all__ = [
    "SCHEMA_VERSION",
    "DEFAULT_FIELD_WEIGHTS",
    "USER_FIELD_ALIASES",
    "INDEXED_BODY_SECTIONS",
    "DEFAULT_K1",
    "DEFAULT_B",
    "tokenize",
    "BM25Index",
    "IndexedDoc",
    "FieldHit",
    "SearchHit",
    "HybridHit",
    "IndexFormatError",
    "IndexNotFoundError",
    "IndexStaleness",
    "RebuildIndexResult",
    "build_index",
    "rebuild_index_for_config",
    "search",
    "hybrid_search",
    "default_index_path",
    "diff_index",
    "resolve_field_weights",
    "compute_config_hash",
]
