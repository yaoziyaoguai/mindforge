"""Pipeline insufficient_content guard tests."""

from __future__ import annotations

import pytest

from mindforge.process_service import summarize_outcome
from mindforge.processors.pipeline import Pipeline, _check_insufficient_content
from mindforge.sources.base import SourceDocument, compute_content_hash


class _NoLLMClient:
    """任何 LLM 调用都会让测试失败，用来证明 pre-triage skip 不触碰 provider。"""

    calls = 0

    def __getattr__(self, name: str):
        self.calls += 1
        raise AssertionError(f"LLM client must not be used for insufficient_content skip: {name}")


class _NoopLogger:
    def emit(self, *args, **kwargs) -> None:  # pragma: no cover - skip path 不应调用
        raise AssertionError("RunLogger must not emit stage events for pre-triage skip")


def _doc(raw_text: str, *, title: str = "Test Source") -> SourceDocument:
    return SourceDocument(
        source_id=f"source-{compute_content_hash(raw_text)}",
        source_type="plain_markdown",
        source_path="00-Inbox/ManualNotes/source.md",
        title=title,
        raw_text=raw_text,
        content_hash=compute_content_hash(raw_text),
        adapter_name="PlainMarkdownAdapter",
    )


def _pipeline(client: _NoLLMClient) -> Pipeline:
    return Pipeline(
        client=client,  # type: ignore[arg-type]
        logger=_NoopLogger(),  # type: ignore[arg-type]
        prompts_dir="unused",
        prompt_versions=object(),
        triage_threshold=5,
        learning_tracks_text="",
    )


@pytest.mark.parametrize(
    "raw_text",
    [
        "",
        "   \n\t  ",
        "!!! --- ...",
        "ok",
        "hi",
        "n/a",
        "none",
        "null",
    ],
)
def test_insufficient_content_gracefully_skips_before_llm(raw_text: str) -> None:
    """明显无信息量内容应进入可审计 skipped 结果，而不是 failed 或静默丢失。"""

    client = _NoLLMClient()
    doc = _doc(raw_text)
    outcome = _pipeline(client).run(doc)
    result = summarize_outcome(
        outcome,
        doc,
        adapter_name="PlainMarkdownAdapter",
        dry_run=False,
    )

    assert client.calls == 0
    assert outcome.status == "skipped"
    assert outcome.status != "failed"
    assert outcome.skip_reason == "insufficient_content"
    assert result.status == "skipped"
    assert result.skip_reason == "insufficient_content"
    assert result.source_dict["source_id"] == doc.source_id


@pytest.mark.parametrize(
    "raw_text",
    [
        "todo",
        "wip",
        "test",
        "会议纪要",
        "ABC-123",
        "MindForge",
        "API Plan",
    ],
)
def test_insufficient_content_guard_does_not_kill_short_meaningful_content(raw_text: str) -> None:
    """短内容可能是标题、ID、专有名词或中文笔记名，不能在 LLM 前被误杀。"""

    assert _check_insufficient_content(_doc(raw_text, title=raw_text)) is None
