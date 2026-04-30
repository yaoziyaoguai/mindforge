"""Recall CLI presenter。

中文学习型说明：presenter 是 CLI 输出层，可以依赖 Rich，也可以把 service
结构化结果渲染成 json / markdown / table / compact 文本；但它不能做 BM25
排序、include_drafts 过滤、config/path 解析或任何文件写入，避免重新把业务
逻辑塞回 CLI 巨石。
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from .recall_service import (
    RecallSearchResult,
    recall_hit_next_action,
    recall_hit_to_safe_dict,
    recall_no_result_next_action,
    recall_search_summary,
)


@dataclass(frozen=True)
class RecallRenderContext:
    """CLI 已经计算好的展示上下文。

    中文学习型说明：query hash、日期原始字符串这些值属于 CLI 参数与 telemetry
    边界，presenter 只把它们放进输出 payload，不重新解析参数、不读配置。
    """

    keyword_provided: bool
    keyword_hash: str | None
    since: str | None
    until: str | None


def build_recall_json_payload(result: RecallSearchResult, context: RecallRenderContext) -> dict[str, Any]:
    """生成 recall JSON 输出 payload；不做检索、不写文件。"""
    query = result.query
    items = [
        recall_hit_to_safe_dict(
            hit,
            explain=query.explain,
            ranking=query.ranking,
            index_stale=result.index.stale,
            weight_source=result.weight_source,
        )
        for hit in result.hits
    ]
    return {
        "version": 1,
        "engine": "bm25",
        "ranking": query.ranking,
        "weight_source": result.weight_source,
        "active_weights": result.active_weights,
        "index_stale": result.index.stale,
        "index": {
            "source": result.index.source,
            "used_disk": result.index.used_disk,
            "path": str(result.index.path),
            "suggest_rebuild": result.index.suggest_rebuild,
            "card_counts": result.index.card_counts,
        },
        "query": {
            "track": query.track,
            "project": query.project,
            "tags": list(query.tags),
            "query_provided": context.keyword_provided,
            "query_hash": context.keyword_hash,
            "status_filter": query.status,
            "include_drafts": query.include_drafts,
            "since": context.since,
            "until": context.until,
            "limit": query.limit,
        },
        "count": result.count,
        "items": items,
    }


def render_recall_result(
    *,
    console: Console,
    result: RecallSearchResult,
    output_format: str,
    context: RecallRenderContext,
) -> None:
    """把 recall service 结果渲染到终端，保持 CLI 外部语义不变。"""
    if output_format == "json":
        print(_json.dumps(build_recall_json_payload(result, context), ensure_ascii=False, indent=2))
        return
    if output_format == "markdown":
        print(format_recall_markdown(result))
        return
    if output_format == "table":
        _render_recall_table(console, result)
        return
    _render_recall_compact(console, result)


def format_recall_markdown(result: RecallSearchResult) -> str:
    """生成 markdown 输出；方便 presenter-level tests 不依赖 CLI 黑盒。"""
    lines: list[str] = [
        f"# Recall · {result.count} 项 ({result.label})",
        "",
        recall_search_summary(result).rstrip(),
    ]
    if not result.hits:
        lines.extend(["_(no cards matched)_", "", recall_no_result_next_action(result.index.card_counts)])
        return "\n".join(lines) + "\n"
    for rank, hit in enumerate(result.hits, start=1):
        score_str = f"score={hit.score:.3f}"
        lines.append(
            f"- **#{rank} [{hit.id or Path(hit.rel_path).stem}]** {hit.title or '(untitled)'}  "
            f"`{score_str}` `source={hit.source_type or '-'}` "
            f"`status={hit.status_label}` `track={hit.track or '-'}` "
            f"`terms={hit.matched_terms}` `path={hit.rel_path}`"
        )
        if result.query.explain and hit.final_score is not None:
            lines.append(
                f"    - hybrid: bm25={hit.bm25_norm:.3f}·{hit.bm25_score:.3f}, "
                f"value={hit.value_norm:.3f}, review_due={hit.review_due_norm:.3f} "
                f"→ final={hit.final_score:.3f}"
            )
        if result.query.explain:
            for field in hit.field_hits:
                terms = ", ".join(f"{t}×{n}" for t, n in field.term_counts.items())
                lines.append(f"    - {field.field} (w={field.weight}, +{field.contribution:.3f}): {terms}")
    lines.extend(["", recall_hit_next_action()])
    return "\n".join(lines) + "\n"


def _render_recall_table(console: Console, result: RecallSearchResult) -> None:
    print(recall_search_summary(result).rstrip())
    if not result.hits:
        console.print("[yellow]没有匹配的卡片。[/yellow]")
        console.print(f"[dim]{recall_no_result_next_action(result.index.card_counts)}[/dim]")
        return
    table = Table(title=f"Recall · {result.count} 项 ({result.label})")
    table.add_column("rank", justify="right")
    table.add_column("score", justify="right")
    table.add_column("title")
    table.add_column("source")
    table.add_column("status")
    table.add_column("matched terms")
    table.add_column("next")
    for rank, hit in enumerate(result.hits, start=1):
        table.add_row(
            str(rank),
            f"{hit.score:.3f}",
            hit.title or "(untitled)",
            hit.source_type or "-",
            hit.status_label,
            hit.matched_terms,
            "review weekly",
        )
    console.print(table)
    console.print(f"[dim]{recall_hit_next_action()}[/dim]")


def _render_recall_compact(console: Console, result: RecallSearchResult) -> None:
    print(recall_search_summary(result).rstrip())
    if not result.hits:
        console.print("[yellow]没有匹配的卡片。[/yellow]")
        print(recall_no_result_next_action(result.index.card_counts))
        return
    console.print(f"[bold]Recall[/bold] · {result.count} 项 ({result.label})")
    for rank, hit in enumerate(result.hits, start=1):
        console.print(
            f"- score={hit.score:.3f} · rank=#{rank} · {hit.id or Path(hit.rel_path).stem} · "
            f"{hit.title or '(untitled)'} · source={hit.source_type or '-'} · "
            f"status={hit.status_label} · terms={hit.matched_terms}"
        )
        if result.query.explain:
            console.print(f"    [dim]why[/dim] {hit.why_this_matched}")
            if hit.final_score is not None:
                console.print(
                    f"    [dim]hybrid[/dim] bm25={hit.bm25_norm:.3f}·{hit.bm25_score:.3f} "
                    f"value={hit.value_norm:.3f} review_due={hit.review_due_norm:.3f} "
                    f"→ final={hit.final_score:.3f}"
                )
            for field in hit.field_hits:
                terms = ", ".join(f"{t}×{n}" for t, n in field.term_counts.items())
                console.print(
                    f"    [dim]{field.field}[/dim] w={field.weight} +{field.contribution:.3f}: {terms}"
                )
    console.print(f"[dim]{recall_hit_next_action()}[/dim]")
