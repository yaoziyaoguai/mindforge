"""TopicPresenter 测试。

验证审批边界、摘要提取、字段透出、边界情况。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from mindforge.cards import CardSummary
from mindforge.topic_presenter import (
    build_topic_view,
    list_topics,
    _extract_safe_summary,
    _extract_paragraphs,
    _truncate_text,
)


def _make_card(
    tmp_path: Path,
    filename: str,
    *,
    status: str = "human_approved",
    track: str = "React",
    knowledge_type: str = "concept",
    human_note: str | None = None,
    body: str = "",
    **extra,
) -> CardSummary:
    """Helper：在 tmp_path 下创建真实 .md 卡片并返回 CardSummary。"""
    from mindforge.cards import iter_cards

    cards_dir = tmp_path / "cards"
    cards_dir.mkdir(parents=True)

    card_path = cards_dir / filename
    fm = {
        "id": filename.replace(".md", ""),
        "title": filename.replace(".md", ""),
        "status": status,
        "track": track,
        "tags": ["test"],
        "source_type": "plain_markdown",
        "source_title": "Test Source",
        "value_score": 5,
        "created_at": "2026-05-10T00:00:00",
        "knowledge_type": knowledge_type,
        "relations": [{"type": "references", "target_id": "card-x"}],
        **extra,
    }
    if human_note:
        fm["human_note"] = human_note

    yaml_lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    text = f"---\n{yaml_lines}\n---\n\n{body}"
    card_path.write_text(text, encoding="utf-8")

    result = iter_cards(tmp_path, "cards")
    assert result.cards, f"iter_cards 应读到卡片: {filename}"
    return result.cards[0]


# ============================================================================
# approval boundary
# ============================================================================


def test_ai_draft_excluded():
    """ai_draft 卡片不进入 topic 视图。"""
    draft = CardSummary(
        id="d1", title="Draft", status="ai_draft",
        path=Path("d1.md"), rel_path="d1.md",
        projects=(), tags=(), source_type=None, track="React",
    )
    approved = CardSummary(
        id="a1", title="Approved", status="human_approved",
        path=Path("a1.md"), rel_path="a1.md",
        projects=(), tags=(), source_type=None, track="React",
    )

    view = build_topic_view("React", [draft, approved])
    assert len(view["cards"]) == 1
    assert view["cards"][0]["id"] == "a1"


def test_mixed_approval_only_returns_approved():
    """mixed ai_draft + human_approved 只返回 approved。"""
    cards = [
        CardSummary(id=f"c{i}", title=f"C{i}", status=s, path=Path(f"c{i}.md"),
                     rel_path=f"c{i}", projects=(), tags=(), source_type=None,
                     track="React")
        for i, s in enumerate(["ai_draft", "human_approved", "ai_draft", "human_approved"])
    ]
    view = build_topic_view("React", cards)
    assert view["total_approved_cards"] == 2
    for c in view["cards"]:
        assert c["approval_state"] == "human_approved"


def test_trashed_excluded():
    """trashed 卡片不进入 topic 视图。"""
    trashed = CardSummary(
        id="t1", title="Trashed", status="trashed",
        path=Path("t1.md"), rel_path="t1.md",
        projects=(), tags=(), source_type=None, track="React",
    )
    approved = CardSummary(
        id="a1", title="Approved", status="human_approved",
        path=Path("a1.md"), rel_path="a1.md",
        projects=(), tags=(), source_type=None, track="React",
    )
    view = build_topic_view("React", [trashed, approved])
    assert len(view["cards"]) == 1


# ============================================================================
# summary extraction
# ============================================================================


def test_summary_extracts_from_ai_summary_section(tmp_path: Path):
    """summary 从 ## AI Summary 段落提取。"""
    card = _make_card(tmp_path, "c1.md", body="""
## AI Summary

This card describes React hooks patterns and best practices.

## Details

More content here.
""")
    summary = _extract_safe_summary(card)
    assert "React hooks patterns" in summary


def test_summary_fallback_to_first_paragraph(tmp_path: Path):
    """无 AI Summary 时回退到第一个非空段落。"""
    card = _make_card(tmp_path, "c1.md", body="""
React hooks are a fundamental pattern in modern React development.

## Details

More content.
""")
    summary = _extract_safe_summary(card)
    assert "React hooks are a fundamental pattern" in summary


def test_summary_truncates_long_text(tmp_path: Path):
    """过长摘要被截断到 max_chars。"""
    long_text = "React " * 200
    card = _make_card(tmp_path, "c1.md", body=f"## AI Summary\n\n{long_text}\n")
    summary = _extract_safe_summary(card, max_chars=100)
    assert len(summary) <= 103  # max_chars + "…"


def test_summary_empty_when_no_body(tmp_path: Path):
    """卡片无 body 时 summary 为空字符串。"""
    card = _make_card(tmp_path, "c1.md", body="")
    summary = _extract_safe_summary(card)
    assert summary == ""


def test_summary_strips_markdown_headers(tmp_path: Path):
    """summary 不包含 markdown 标题行。"""
    card = _make_card(tmp_path, "c1.md", body="""
## Some Section

- [ ] A task item

Real content paragraph here.

## Another Section
""")
    summary = _extract_safe_summary(card)
    assert "Real content paragraph here" in summary
    assert "A task item" not in summary  # checklist excluded


# ============================================================================
# view model fields
# ============================================================================


def test_view_model_includes_all_required_fields(tmp_path: Path):
    """view dict 包含所有必要字段。"""
    card = _make_card(tmp_path, "c1.md", body="## AI Summary\n\nTest summary.\n")
    view = build_topic_view("React", [card])

    c = view["cards"][0]
    assert c["id"] == "c1"
    assert c["title"] == "c1"
    assert c["knowledge_type"] == "concept"
    assert c["relations"] == [{"type": "references", "target_id": "card-x"}]
    assert c["tags"] == ["test"]
    assert c["summary"] != ""
    assert "Test summary" in c["summary"]
    assert c["human_note"] is None
    assert c["approval_state"] == "human_approved"
    assert c["value_score"] == 5
    assert c["source_title"] == "Test Source"
    assert c["source_type"] == "plain_markdown"
    assert c["track"] == "React"
    assert c["created_at"] is not None
    assert c["created_at"] is not None and "2026-05-10" in c["created_at"]


def test_human_note_transparency(tmp_path: Path):
    """human_note 正确透出到视图。"""
    card = _make_card(tmp_path, "c1.md", human_note="Approved with minor corrections", body="# Test\n")
    view = build_topic_view("React", [card])
    assert view["cards"][0]["human_note"] == "Approved with minor corrections"


def test_source_fields_transparency(tmp_path: Path):
    """source_title / source_type 正确透出。"""
    card = _make_card(tmp_path, "c1.md", body="# Test\n")
    view = build_topic_view("React", [card])
    c = view["cards"][0]
    assert c["source_title"] == "Test Source"
    assert c["source_type"] == "plain_markdown"


# ============================================================================
# topic listing
# ============================================================================


def test_list_topics_aggregates_unique():
    """list_topics 返回去重排序的 topic 列表。"""
    cards = [
        CardSummary(id="1", title="T1", status="human_approved", path=Path("1.md"),
                     rel_path="1", projects=(), tags=(), source_type=None, track="React"),
        CardSummary(id="2", title="T2", status="human_approved", path=Path("2.md"),
                     rel_path="2", projects=(), tags=(), source_type=None, track="Python"),
        CardSummary(id="3", title="T3", status="human_approved", path=Path("3.md"),
                     rel_path="3", projects=(), tags=(), source_type=None, track="React"),
    ]
    topics = list_topics(cards)
    assert topics == ["Python", "React"]


def test_list_topics_excludes_drafts():
    """list_topics 不包含只有 ai_draft 卡片的 topic。"""
    cards = [
        CardSummary(id="1", title="D1", status="ai_draft", path=Path("1.md"),
                     rel_path="1", projects=(), tags=(), source_type=None, track="OnlyDraft"),
        CardSummary(id="2", title="A1", status="human_approved", path=Path("2.md"),
                     rel_path="2", projects=(), tags=(), source_type=None, track="Real"),
    ]
    topics = list_topics(cards)
    assert topics == ["Real"]


def test_list_topics_empty():
    """无 approved 卡片时返回空列表。"""
    assert list_topics([]) == []


# ============================================================================
# edge cases
# ============================================================================


def test_no_cards_for_topic():
    """topic 无匹配卡片时返回空视图。"""
    view = build_topic_view("NonexistentTopic", [])
    assert view["topic"] == "NonexistentTopic"
    assert view["total_approved_cards"] == 0
    assert view["cards"] == []


def test_no_matching_track():
    """卡片 track 不匹配时不出现在视图中。"""
    card = CardSummary(
        id="c1", title="C1", status="human_approved",
        path=Path("c1.md"), rel_path="c1",
        projects=(), tags=(), source_type=None, track="OtherTrack",
    )
    view = build_topic_view("React", [card])
    assert view["total_approved_cards"] == 0


def test_unknown_knowledge_type_fallback():
    """unknown knowledge_type fallback 到 'concept'。"""
    card = CardSummary(
        id="c1", title="C1", status="human_approved",
        path=Path("c1.md"), rel_path="c1",
        projects=(), tags=(), source_type=None, track="React",
        knowledge_type="",  # empty → fallback to "concept"
    )
    view = build_topic_view("React", [card])
    assert view["type_counts"].get("concept", 0) == 1


def test_malformed_metadata_does_not_crash():
    """missing optional fields 不导致崩溃。"""
    card = CardSummary(
        id=None, title=None, status="human_approved",
        path=Path("c1.md"), rel_path="c1",
        projects=(), tags=(), source_type=None, track="React",
        knowledge_type="concept",
        created_at=None, approved_at=None,
        human_note=None, source_title=None,
    )
    view = build_topic_view("React", [card])
    c = view["cards"][0]
    assert c["id"] is None
    assert c["title"] is None
    assert c["created_at"] is None
    assert c["approved_at"] is None


def test_null_fields_have_clear_semantics():
    """缺失字段为 None，不编造值。"""
    card = CardSummary(
        id="c1", title="C1", status="human_approved",
        path=Path("c1.md"), rel_path="c1",
        projects=(), tags=(), source_type=None, track="React",
        created_at=None, approved_at=None,
        human_note=None, source_title=None,
    )
    view = build_topic_view("React", [card])
    c = view["cards"][0]
    assert c["source_title"] is None
    assert c["human_note"] is None
    assert c["created_at"] is None
    assert c["approved_at"] is None


# ============================================================================
# helper unit tests
# ============================================================================


def test_extract_paragraphs_skips_headings():
    """提取段落时跳过标题行。"""
    body = "# Title\n\nFirst paragraph.\n\n## Section\n\nSecond paragraph.\n"
    paras = _extract_paragraphs(body)
    assert "First paragraph." in paras
    assert "Title" not in paras


def test_truncate_text_short():
    """短文本不截断。"""
    assert _truncate_text("Hello", 100) == "Hello"


def test_truncate_text_long():
    """长文本截断并附加…。"""
    result = _truncate_text("a b c d e f g h i j", 10)
    assert len(result) <= 13
    assert result.endswith("…")
