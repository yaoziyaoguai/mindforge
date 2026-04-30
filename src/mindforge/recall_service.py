"""Recall / BM25 query path 的 service 层。

本模块不依赖 Typer / Rich / console，不读取 `.env`，不调用 LLM，也不做
embedding / RAG。它只读取本地 Knowledge Card 安全字段和本地 BM25 index，
返回 CLI 可以渲染的结构化结果。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from . import lexical_index as lx
from .cards import CardSummary, iter_cards
from .config import MindForgeConfig


class RecallServiceError(ValueError):
    """Recall service 的用户输入错误。

    中文学习型说明：service 不知道 Typer exit code，也不打印 Rich 文案；它只
    抛出带人类可读 message 的错误，由 CLI 统一映射为 exit code 和输出样式。
    """


@dataclass(frozen=True)
class RecallQuery:
    query: str
    track: str | None
    project: str | None
    tags: tuple[str, ...]
    source_type: str | None
    status: str
    include_drafts: bool
    since: datetime | None
    until: datetime | None
    limit: int
    output_format: str
    explain: bool
    ranking: str = "bm25"
    weight_bm25: float | None = None
    weight_value_score: float | None = None
    weight_review_due: float | None = None


@dataclass(frozen=True)
class RecallFieldExplain:
    field: str
    weight: float
    contribution: float
    term_counts: dict[str, int]


@dataclass(frozen=True)
class RecallHitResult:
    """单条 recall 命中的安全结构。

    中文学习型说明：这里不包含 source 原文、Source Excerpt、Human Note 或
    LLM 运行记录，只携带 CLI 已经允许展示的索引安全字段和解释分量。
    """

    score: float
    id: str | None
    title: str | None
    rel_path: str
    status: str
    status_label: str
    track: str | None
    projects: tuple[str, ...]
    tags: tuple[str, ...]
    source_type: str | None
    created_at: str | None
    matched_terms: str
    matched_terms_list: tuple[str, ...]
    matched_fields: tuple[str, ...]
    field_hits: tuple[RecallFieldExplain, ...]
    why_this_matched: str
    bm25_score: float | None = None
    bm25_norm: float | None = None
    value_norm: float | None = None
    review_due_norm: float | None = None
    final_score: float | None = None


@dataclass(frozen=True)
class RecallIndexInfo:
    source: str
    used_disk: bool
    path: Path
    stale: bool
    suggest_rebuild: bool
    card_counts: dict[str, int]


@dataclass(frozen=True)
class RecallSearchResult:
    query: RecallQuery
    hits: tuple[RecallHitResult, ...]
    index: RecallIndexInfo
    warnings: tuple[str, ...]
    weight_source: str
    active_weights: dict[str, float] | None

    @property
    def count(self) -> int:
        return len(self.hits)

    @property
    def label(self) -> str:
        label = "engine=bm25"
        if self.query.ranking != "bm25":
            label += f" ranking={self.query.ranking}"
        if self.query.ranking == "hybrid":
            label += f" weights={self.weight_source}"
        return label


def run_bm25_recall(cfg: MindForgeConfig, query: RecallQuery) -> RecallSearchResult:
    """执行本地词法 recall，返回结构化结果。

    中文学习型说明：这一步是 query-path recall 的 use-case 层。它可以读取本地
    卡片和本地 index，但不会写 index、不会写 runs、不会上传 telemetry；RunLogger
    仍由 CLI 负责，避免 service 产生隐藏副作用。
    """
    if query.ranking not in ("bm25", "hybrid"):
        raise RecallServiceError(f"--ranking 仅支持 bm25 | hybrid，收到 {query.ranking!r}")

    idx_path = lx.default_index_path(cfg.state.workdir)
    card_scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    stats = recall_local_stats(card_scan.cards)
    fw = lx.resolve_field_weights(cfg.search.bm25.fields)
    cur_k1 = cfg.search.bm25.k1
    cur_b = cfg.search.bm25.b
    cur_hash = lx.compute_config_hash(field_weights=fw, k1=cur_k1, b=cur_b)
    warnings: list[str] = []

    index: lx.BM25Index
    used_disk = False
    index_stale = False
    index_source = "memory-temp"
    if idx_path.exists():
        try:
            index = lx.BM25Index.load(idx_path)
            if index.config_hash and index.config_hash != cur_hash:
                index_stale = True
                index_source = "memory-rebuilt-stale"
                if query.output_format != "json":
                    warnings.append(
                        "提示：磁盘索引的 config_hash 与当前配置不一致；"
                        "本次内存即时重建。建议运行 `mindforge index rebuild`。"
                    )
                index = lx.build_index(card_scan.cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash)
            else:
                used_disk = True
                index_source = "disk"
        except (lx.IndexFormatError, OSError, ValueError) as e:
            index_source = "memory-rebuilt-error"
            warnings.append(f"索引文件不可用（{e}）；改为内存即时构建。")
            index = lx.build_index(card_scan.cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash)
    else:
        if query.output_format != "json":
            warnings.append(
                "提示：尚无索引文件，本次内存即时构建。"
                "建议运行 `mindforge index rebuild` 以加速后续查询。"
            )
        index = lx.build_index(card_scan.cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash)

    if query.ranking == "hybrid":
        active_weights, weight_source = _active_hybrid_weights(cfg, query)
        hybrid_hits = lx.hybrid_search(
            index,
            query.query,
            weights=active_weights,
            cards=card_scan.cards,
            status_filter=query.status,
            include_drafts=query.include_drafts,
            track=query.track,
            project=query.project,
            tags=query.tags,
            source_type=query.source_type,
            since=query.since,
            until=query.until,
            limit=query.limit,
        )
        hits = tuple(_from_hybrid_hit(hh) for hh in hybrid_hits)
    else:
        active_weights = None
        weight_source = "n/a"
        raw_hits = lx.search(
            index,
            query.query,
            status_filter=query.status,
            include_drafts=query.include_drafts,
            track=query.track,
            project=query.project,
            tags=query.tags,
            source_type=query.source_type,
            since=query.since,
            until=query.until,
            limit=query.limit,
        )
        hits = tuple(_from_search_hit(h) for h in raw_hits)

    return RecallSearchResult(
        query=query,
        hits=hits,
        index=RecallIndexInfo(
            source=index_source,
            used_disk=used_disk,
            path=idx_path,
            stale=index_stale,
            suggest_rebuild=recall_should_suggest_rebuild(index_source, index_stale),
            card_counts=stats,
        ),
        warnings=tuple(warnings),
        weight_source=weight_source,
        active_weights=active_weights,
    )


def _active_hybrid_weights(cfg: MindForgeConfig, query: RecallQuery) -> tuple[dict[str, float], str]:
    cfg_w = dict(cfg.search.hybrid.weights)
    overrides_given = [w is not None for w in (query.weight_bm25, query.weight_value_score, query.weight_review_due)]
    weight_source = "cli_override" if any(overrides_given) else "config"
    if query.weight_bm25 is not None:
        cfg_w["bm25"] = query.weight_bm25
    if query.weight_value_score is not None:
        cfg_w["value_score"] = query.weight_value_score
    if query.weight_review_due is not None:
        cfg_w["review_due"] = query.weight_review_due
    for key, value in cfg_w.items():
        if not isinstance(value, (int, float)) or value < 0:
            raise RecallServiceError(f"非法 hybrid 权重 {key}={value!r}：必须是 >= 0 的数值")
    if all(value == 0 for value in cfg_w.values()):
        raise RecallServiceError("非法 hybrid 权重：三路权重不能同时为 0")
    return cfg_w, weight_source


def _from_hybrid_hit(hit: lx.HybridHit) -> RecallHitResult:
    base = _from_search_hit(hit.base)
    why = (
        f"{base.why_this_matched}; hybrid: bm25_norm={hit.bm25_norm:.2f}, "
        f"value={hit.value_norm:.2f}, review_due={hit.review_due_norm:.2f} "
        f"→ {hit.final_score:.3f}"
    )
    return replace(
        base,
        score=hit.final_score,
        why_this_matched=why,
        bm25_score=hit.bm25_score,
        bm25_norm=hit.bm25_norm,
        value_norm=hit.value_norm,
        review_due_norm=hit.review_due_norm,
        final_score=hit.final_score,
    )


def _from_search_hit(hit: lx.SearchHit) -> RecallHitResult:
    doc = hit.doc
    field_hits = tuple(
        RecallFieldExplain(
            field=fh.field,
            weight=fh.weight,
            contribution=fh.contribution,
            term_counts=dict(fh.term_counts),
        )
        for fh in hit.field_hits
    )
    matched_terms = _hit_terms_from_fields(field_hits)
    return RecallHitResult(
        score=hit.score,
        id=doc.id,
        title=doc.title,
        rel_path=doc.rel_path,
        status=doc.status,
        status_label=recall_status_label(doc.status),
        track=doc.track,
        projects=tuple(doc.projects),
        tags=tuple(doc.tags),
        source_type=doc.source_type,
        created_at=doc.created_at,
        matched_terms=matched_terms,
        matched_terms_list=tuple(term for term in matched_terms.split(",") if term and term != "-"),
        matched_fields=tuple(fh.field for fh in field_hits),
        field_hits=field_hits,
        why_this_matched=why_matched(field_hits),
    )


def recall_local_stats(cards: tuple[CardSummary, ...] | list[CardSummary]) -> dict[str, int]:
    """汇总 recall 空状态需要的本地计数；只读 CardSummary 安全字段。"""
    stats = {"total": 0, "human_approved": 0, "ai_draft": 0, "other": 0}
    for card in cards:
        stats["total"] += 1
        if card.status == "human_approved":
            stats["human_approved"] += 1
        elif card.status == "ai_draft":
            stats["ai_draft"] += 1
        else:
            stats["other"] += 1
    return stats


def recall_should_suggest_rebuild(index_source: str, index_stale: bool) -> bool:
    return index_stale or index_source != "disk"


def recall_search_summary(result: RecallSearchResult) -> str:
    """生成 recall 搜索摘要；stdout 可显示 query，但 telemetry 仍只写 hash。"""
    stats = result.index.card_counts
    index_label = "disk index" if result.index.used_disk else "temporary in-memory index"
    suggest = "yes" if result.index.suggest_rebuild else "no"
    return (
        f"Search query: {result.query.query}\n"
        f"Index: {index_label} (source={result.index.source}, suggest_rebuild={suggest}, path={result.index.path})\n"
        f"Cards: approved={stats['human_approved']} ai_draft={stats['ai_draft']} total={stats['total']}\n"
        "Boundary: local lexical recall only; no RAG, no embedding, no LLM, no .env, no upload.\n"
    )


def recall_status_label(status: str) -> str:
    """把状态翻译成搜索风险提示，明确 draft 不是正式长期记忆。"""
    if status == "human_approved":
        return "human_approved/approved knowledge"
    if status == "ai_draft":
        return "ai_draft/risky draft"
    return status


def recall_hit_next_action() -> str:
    return (
        "下一步：用 `mindforge review weekly` 安排复习；需要更多材料时运行 "
        "`mindforge process --profile fake --limit 1`，再手动 approve。"
    )


def recall_no_result_next_action(stats: dict[str, int] | None = None) -> str:
    """recall 无结果时的恢复建议；保持纯本地、不调用 LLM。"""
    counts = ""
    if stats is not None:
        counts = f"当前 approved cards={stats['human_approved']}，ai_draft={stats['ai_draft']}。"
    return (
        f"{counts}下一步：运行 `mindforge index rebuild`；如只有草稿，先运行 "
        "`mindforge approve list`；如资料不足，继续 process。也可以缩短 query、"
        "换同义词，或改用更具体的 title/track 关键词。"
    )


def recall_hit_to_safe_dict(hit: RecallHitResult, *, explain: bool, ranking: str, index_stale: bool, weight_source: str) -> dict[str, Any]:
    """RecallHitResult → JSON 安全 dict；只暴露白名单字段。"""
    out: dict[str, Any] = {
        "score": round(hit.score, 6),
        "id": hit.id,
        "title": hit.title,
        "rel_path": hit.rel_path,
        "status": hit.status,
        "track": hit.track,
        "projects": list(hit.projects),
        "tags": list(hit.tags),
        "source_type": hit.source_type,
        "created_at": hit.created_at,
    }
    if hit.final_score is not None:
        out.update(
            {
                "bm25_score": round(hit.bm25_score or 0.0, 6),
                "bm25_norm": round(hit.bm25_norm or 0.0, 6),
                "value_norm": round(hit.value_norm or 0.0, 6),
                "review_due_norm": round(hit.review_due_norm or 0.0, 6),
                "final_score": round(hit.final_score, 6),
                "score": round(hit.final_score, 6),
            }
        )
    if explain:
        out["explain"] = [
            {
                "field": field.field,
                "weight": field.weight,
                "contribution": round(field.contribution, 6),
                "terms": dict(field.term_counts),
            }
            for field in hit.field_hits
        ]
        out["why_this_matched"] = hit.why_this_matched
        out["matched_terms"] = list(hit.matched_terms_list)
        out["matched_fields"] = list(hit.matched_fields)
        out["ranking_mode"] = ranking
        out["index_stale"] = index_stale
        out["weight_source"] = weight_source
    return out


def _hit_terms_from_fields(fields: tuple[RecallFieldExplain, ...]) -> str:
    terms: list[str] = []
    for field in fields:
        for term in field.term_counts:
            if term not in terms:
                terms.append(term)
    return ",".join(terms[:6]) or "-"


def why_matched(fields: tuple[RecallFieldExplain, ...]) -> str:
    if not fields:
        return "no field hits"
    top = max(fields, key=lambda field: field.contribution)
    terms = ",".join(top.term_counts.keys())
    return f"top field={top.field}(w={top.weight}, +{top.contribution:.3f}) terms={terms}"
