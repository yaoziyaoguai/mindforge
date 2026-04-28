"""v0.3 — BM25 lexical recall（纯本地词法检索）。

设计契约（详见 docs/M5_4_LEXICAL_RECALL_PROTOCOL.md）：

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

from .cards import CardSummary, extract_section, read_card_body

SCHEMA_VERSION = 1

# 默认字段权重（v0.3 hardcoded，未来可移到 mindforge.yaml）
# 设计直觉：title / track / projects 命中比 tag / source_type 命中更"中要害"。
DEFAULT_FIELD_WEIGHTS: dict[str, int] = {
    "title": 5,
    "source_title": 3,
    "track": 4,
    "projects": 4,
    "tags": 3,
    "source_type": 1,
    "principles": 2,
    "known_risks": 2,
    "body_summary": 1,
    "body_actions": 1,
    "body_principles": 1,
    "body_risks": 1,
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


def tokenize(text: str) -> list[str]:
    """ASCII 单词 + CJK 单字混合分词（小写化）。

    v0.3 故意做最小可用的分词器：
    - ASCII：按 ``[A-Za-z0-9]+`` 抓词，全部 lowercase；
    - CJK：每个汉字/假名/谚文字视为一个 token；
    - 其他符号忽略。

    不做 stemming / 停用词 / 词形还原。索引规模小（个人知识库），简单可解释。
    """
    if not text:
        return []
    out: list[str] = []
    for w in _ASCII_TOKEN_RE.findall(text):
        out.append(w.lower())
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
    field_weights: dict[str, int]
    k1: float
    b: float
    avgdl: float
    docs: list[IndexedDoc]
    tokenizer_name: str = "ascii_word_plus_cjk_char_v1"

    # ── 持久化 ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "built_at": self.built_at,
            "tokenizer_name": self.tokenizer_name,
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
            field_weights=dict(data.get("field_weights") or DEFAULT_FIELD_WEIGHTS),
            k1=float(data.get("k1") or DEFAULT_K1),
            b=float(data.get("b") or DEFAULT_B),
            avgdl=float(data.get("avgdl") or 0.0),
            docs=docs,
            tokenizer_name=str(data.get("tokenizer_name") or "ascii_word_plus_cjk_char_v1"),
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
    field_weights: dict[str, int] | None = None,
    k1: float = DEFAULT_K1,
    b: float = DEFAULT_B,
    indexed_body_sections: dict[str, str] | None = None,
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
            dl += float(fw.get(fname, 1)) * len(toks)

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
    )


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

    # pre-filter
    candidates: list[IndexedDoc] = []
    for d in index.docs:
        if eff_status is not None and d.status != eff_status:
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

    if not candidates:
        return []

    # df 在过滤后语料上重算 → 更贴合用户当前查询子集
    N = len(candidates)
    unique_q = list(dict.fromkeys(q_terms))   # 保序去重
    df: Counter[str] = Counter()
    # 按 (doc, term) 是否出现来累加 df —— 每个字段都算入 doc 总词袋
    for d in candidates:
        seen: set[str] = set()
        for toks in d.fields.values():
            for t in toks:
                if t in unique_q:
                    seen.add(t)
        for t in seen:
            df[t] += 1
    idf = {t: math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1.0) for t in unique_q}

    avgdl = index.avgdl or 1.0
    k1 = index.k1
    b = index.b

    hits: list[SearchHit] = []
    for d in candidates:
        # weighted_tf[term] = sum_field weight[field] * tf_in_field
        per_field_counts: dict[str, Counter[str]] = {}
        weighted_tf: Counter[str] = Counter()
        for fname, toks in d.fields.items():
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
            continue

        dl = d.doc_len if d.doc_len > 0 else 1.0
        score = 0.0
        per_term_score: dict[str, float] = {}
        for t in unique_q:
            tf = weighted_tf.get(t, 0)
            if tf == 0:
                continue
            denom = tf + k1 * (1.0 - b + b * dl / avgdl)
            s = idf[t] * (tf * (k1 + 1.0)) / denom if denom > 0 else 0.0
            per_term_score[t] = s
            score += s

        # 组装 explain：把总分按字段贡献近似分摊。
        # 近似公式：field_contrib = sum_t (per_term_score[t] * (w * fcount[t]) / weighted_tf[t])
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

        hits.append(SearchHit(doc=d, score=score, field_hits=tuple(field_hits)))

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
    "INDEXED_BODY_SECTIONS",
    "DEFAULT_K1",
    "DEFAULT_B",
    "tokenize",
    "BM25Index",
    "IndexedDoc",
    "FieldHit",
    "SearchHit",
    "IndexFormatError",
    "IndexNotFoundError",
    "IndexStaleness",
    "build_index",
    "search",
    "default_index_path",
    "diff_index",
]
