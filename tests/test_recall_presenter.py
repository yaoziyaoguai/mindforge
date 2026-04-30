"""v0.7.13 — Recall presenter 边界测试。

学习要点：presenter 只负责把 recall_service 的结构化结果渲染成人能读的
输出。它可以依赖 Rich，但不能重新做 BM25 排序、读取配置/文件或触发 LLM。
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from rich.console import Console

from mindforge.recall_presenter import (
    RecallRenderContext,
    build_recall_json_payload,
    format_recall_markdown,
    render_recall_result,
)
from mindforge.recall_service import (
    RecallFieldExplain,
    RecallHitResult,
    RecallIndexInfo,
    RecallQuery,
    RecallSearchResult,
)


def _query(*, explain: bool = False) -> RecallQuery:
    return RecallQuery(
        query="agent",
        track=None,
        project=None,
        tags=(),
        source_type=None,
        status="human_approved",
        include_drafts=True,
        since=None,
        until=None,
        limit=2,
        output_format="compact",
        explain=explain,
    )


def _result(*, explain: bool = False, hits: bool = True) -> RecallSearchResult:
    hit_items: tuple[RecallHitResult, ...] = ()
    if hits:
        hit_items = (
            RecallHitResult(
                score=1.25,
                id="agent-approved",
                title="Agent Runtime Checkpoint",
                rel_path="20-Knowledge-Cards/agent-approved.md",
                status="human_approved",
                status_label="human_approved",
                track="agent-runtime",
                projects=(),
                tags=("agent",),
                source_type="markdown",
                created_at="2026-04-30",
                matched_terms="agent",
                matched_terms_list=("agent",),
                matched_fields=("title",),
                field_hits=(
                    RecallFieldExplain(
                        field="title",
                        weight=2.0,
                        contribution=1.25,
                        term_counts={"agent": 1},
                    ),
                ),
                why_this_matched="top field=title; terms=agent",
            ),
        )
    return RecallSearchResult(
        query=_query(explain=explain),
        hits=hit_items,
        index=RecallIndexInfo(
            source="memory-temp",
            used_disk=False,
            path=Path(".mindforge/index/bm25.json"),
            stale=False,
            suggest_rebuild=True,
            card_counts={"human_approved": 1, "ai_draft": 1, "total": 2},
        ),
        warnings=(),
        weight_source="n/a",
        active_weights=None,
    )


def _context() -> RecallRenderContext:
    return RecallRenderContext(keyword_provided=True, keyword_hash="abc123", since=None, until=None)


def test_recall_presenter_builds_json_payload_without_business_ranking() -> None:
    """JSON presenter 保留 CLI 语义，但只消费已排序结果，不重新计算排名。"""
    payload = build_recall_json_payload(_result(), _context())

    assert payload["engine"] == "bm25"
    assert payload["query"]["query_hash"] == "abc123"
    assert payload["items"][0]["id"] == "agent-approved"
    assert payload["items"][0]["score"] == 1.25


def test_recall_presenter_markdown_normal_and_no_result() -> None:
    """markdown 输出覆盖命中与空状态；next action 来自结构化结果边界。"""
    normal = format_recall_markdown(_result())
    empty = format_recall_markdown(_result(hits=False))

    assert "# Recall · 1 项" in normal
    assert "Agent Runtime Checkpoint" in normal
    assert "下一步" in normal
    assert "_(no cards matched)_" in empty
    assert "mindforge process" in empty or "mindforge approve" in empty


def test_recall_presenter_renders_explain_compact(capsys) -> None:
    """compact explain 只渲染 service 给出的 why/field，不生成新的 explain 逻辑。"""
    stream = io.StringIO()
    console = Console(file=stream, force_terminal=False, color_system=None, width=100)

    render_recall_result(console=console, result=_result(explain=True), output_format="compact", context=_context())
    stdout = capsys.readouterr().out
    rendered = stream.getvalue()

    assert "Search query: agent" in stdout
    assert "Agent Runtime Checkpoint" in rendered
    assert "top field=title" in rendered
    assert "title w=2.0" in rendered


def test_recall_presenter_json_output_keeps_shape(capsys) -> None:
    """json 渲染仍输出稳定 version/count/items schema。"""
    console = Console(file=io.StringIO(), force_terminal=False, color_system=None)

    render_recall_result(console=console, result=_result(), output_format="json", context=_context())
    payload = json.loads(capsys.readouterr().out)

    assert payload["version"] == 1
    assert payload["count"] == 1
    assert payload["items"][0]["id"] == "agent-approved"


def test_recall_presenter_boundary_no_typer_file_or_llm_dependency() -> None:
    """presenter 可以依赖 Rich，但不能依赖 Typer、文件读写、LLM 或检索算法。"""
    source = Path("src/mindforge/recall_presenter.py").read_text(encoding="utf-8")

    assert "import typer" not in source
    assert "load_mindforge_config" not in source
    assert "build_providers" not in source
    assert "LLMClient" not in source
    assert ".write_text(" not in source
    assert ".read_text(" not in source
    assert "run_bm25_recall" not in source
    assert "hybrid_search" not in source
    assert "lx.search" not in source
