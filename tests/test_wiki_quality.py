"""M2 Wiki Quality golden tests —— 确定性质量评分和报告生成。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from mindforge.wiki.wiki_quality import (
    compute_coverage,
    compute_faithfulness_score,
    compute_knowledge_gaps,
    detect_stale_sections,
    SectionReference,
)


# ──────────────────────────────────────────────
# Coverage Tests
# ──────────────────────────────────────────────

def test_coverage_all_used():
    unused, reasons = compute_coverage(
        approved_ids=["c1", "c2", "c3"],
        used_ids=["c1", "c2", "c3"],
        reason_map={},
    )
    assert unused == []
    assert reasons == {}


def test_coverage_some_unused():
    unused, reasons = compute_coverage(
        approved_ids=["c1", "c2", "c3", "c4"],
        used_ids=["c1", "c3"],
        reason_map={"c2": "low quality", "c4": "not relevant"},
    )
    assert set(unused) == {"c2", "c4"}
    assert reasons["c2"] == "low quality"
    assert reasons["c4"] == "not relevant"


def test_coverage_all_unused():
    unused, reasons = compute_coverage(
        approved_ids=["c1", "c2"],
        used_ids=[],
        reason_map={"c1": "default", "c2": "default"},
    )
    assert set(unused) == {"c1", "c2"}


def test_coverage_empty():
    unused, reasons = compute_coverage([], [], {})
    assert unused == []
    assert reasons == {}


# ──────────────────────────────────────────────
# Faithfulness Tests
# ──────────────────────────────────────────────

def test_faithfulness_perfect_match():
    """完全相同文本应得高分。"""
    text = "machine learning is a subset of artificial intelligence"
    score = compute_faithfulness_score(text, {"c1": text})
    assert score > 0.8, f"expected high score, got {score}"


def test_faithfulness_no_overlap():
    """完全不同文本应得很低分。"""
    score = compute_faithfulness_score(
        "quantum computing uses qubits",
        {"c1": "machine learning uses neural networks"},
    )
    assert score < 0.2, f"expected low score, got {score}"


def test_faithfulness_partial_overlap():
    """部分重叠文本应得中等分数。"""
    score = compute_faithfulness_score(
        "machine learning improves data analysis",
        {"c1": "machine learning is used for pattern recognition"},
    )
    assert 0.2 < score < 0.8, f"expected medium score, got {score}"


def test_faithfulness_empty_section():
    score = compute_faithfulness_score("", {"c1": "some content"})
    assert score == 0.0


def test_faithfulness_empty_cards():
    score = compute_faithfulness_score("some text", {})
    assert score == 0.0


def test_faithfulness_multiple_cards():
    """多卡片时应合并所有 card terms。"""
    score = compute_faithfulness_score(
        "python and javascript are programming languages used for web development",
        {
            "c1": "python is a programming language used for data science",
            "c2": "javascript runs in browsers for web development",
        },
    )
    assert score > 0.25, f"expected reasonable score, got {score}"


def test_faithfulness_whitespace_only():
    score = compute_faithfulness_score("   \n  \t ", {"c1": "content"})
    assert score == 0.0


# ──────────────────────────────────────────────
# Staleness Detection Tests
# ──────────────────────────────────────────────

def test_staleness_detected():
    refs = [SectionReference("ML Basics", ("c1",), "primary")]
    stale = detect_stale_sections(
        refs,
        new_card_titles={"Introduction to ML"},
        topic_keywords={"ML Basics": {"ml", "machine", "learning"}},
    )
    assert "ML Basics" in stale


def test_staleness_no_match():
    refs = [SectionReference("ML Basics", ("c1",), "primary")]
    stale = detect_stale_sections(
        refs,
        new_card_titles={"Quantum Physics 101"},
        topic_keywords={"ML Basics": {"ml", "machine", "learning"}},
    )
    assert stale == []


def test_staleness_empty_inputs():
    refs = [SectionReference("Section A", ("c1",), "primary")]
    assert detect_stale_sections(refs) == []
    assert detect_stale_sections(refs, new_card_titles=set()) == []
    assert detect_stale_sections(refs, topic_keywords={}) == []


# ──────────────────────────────────────────────
# Knowledge Gap Detection Tests
# ──────────────────────────────────────────────

def test_knowledge_gaps_detected():
    gaps = compute_knowledge_gaps(
        section_titles=["Machine Learning", "Data Engineering"],
        used_tags={"ml", "python"},
        topic_keywords={
            "Deep Learning": {"deep", "neural"},
            "Machine Learning": {"ml", "machine", "learning"},
            "Data Engineering": {"data", "pipeline"},
        },
    )
    assert "Deep Learning" in gaps
    assert "Machine Learning" not in gaps
    assert "Data Engineering" not in gaps


def test_knowledge_gaps_none():
    gaps = compute_knowledge_gaps(
        section_titles=["All Topics Covered"],
        used_tags={"ml", "python"},
        topic_keywords={"All Topics Covered": {"topics", "covered"}},
    )
    assert gaps == []


def test_knowledge_gaps_empty():
    gaps = compute_knowledge_gaps([], set(), {})
    assert gaps == []


# ──────────────────────────────────────────────
# Quality Report Appendix Generation Tests
# ──────────────────────────────────────────────

def _make_card(
    id: str,
    title: str,
    track: str = "track1",
    tags: tuple[str, ...] = (),
    status: str = "human_approved",
) -> object:
    """构造最少字段的 CardSummary。"""
    from mindforge.cards import CardSummary
    return CardSummary(
        id=id,
        title=title,
        status=status,
        path=Path(f"/tmp/{id}.md"),
        rel_path=f"{id}.md",
        track=track,
        tags=tags,
        source_path="/tmp/source.md",
        source_title="Test Source",
        source_type="plain_markdown",
        source_content_hash="abc",
        value_score=5,
        projects=(),
    )


def test_quality_appendix_generation():
    """验证 _generate_quality_report_appendix 生成正确格式的 appendix。"""
    from mindforge.wiki_service import _generate_quality_report_appendix

    wiki_content = (
        "# MindForge Main Wiki\n"
        "> This wiki is generated from human-approved knowledge cards.\n"
        "> Last rebuilt: 2026-05-24\n\n"
        "## Overview\n\n"
        "## track1\n\n"
        "<!-- WIKI_SECTION_START card=c1 -->\n"
        "### Card One\n\n"
        "This card discusses machine learning basics and neural networks.\n\n"
        "<!-- WIKI_SECTION_END -->\n"
        "---\n\n"
        "<!-- WIKI_SECTION_START card=c2 -->\n"
        "### Card Two\n\n"
        "Data engineering pipelines and ETL processes.\n\n"
        "<!-- WIKI_SECTION_END -->\n"
        "---\n\n"
    )

    cards = [
        _make_card("c1", "Card One", tags=("ml", "neural-networks")),
        _make_card("c2", "Card Two", tags=("data-engineering", "python")),
        _make_card("c3", "Card Three", track="track2", tags=("quantum",)),
    ]

    appendix = _generate_quality_report_appendix(wiki_content, cards)

    assert "Wiki Quality Report" in appendix
    assert "WIKI_QUALITY_REPORT_START" in appendix
    assert "WIKI_QUALITY_REPORT_END" in appendix
    assert "WIKI_QUALITY_JSON" in appendix
    assert "Coverage" in appendix
    assert "Faithfulness" in appendix

    # 验证 JSON 可解析
    m = re.search(r"<!-- WIKI_QUALITY_JSON\n(.*?)\n-->", appendix, re.DOTALL)
    assert m is not None, "Missing WIKI_QUALITY_JSON"
    data = json.loads(m.group(1))

    assert data["coverage"]["total"] == 3
    assert "c1" in data["used_cards"]
    assert "c2" in data["used_cards"]
    assert len(data["unused_cards"]) == 1
    assert data["unused_cards"][0]["id"] == "c3"


def test_quality_appendix_no_cards():
    """无 approved cards 时也不应崩溃。"""
    from mindforge.wiki_service import _generate_quality_report_appendix

    wiki_content = "# Wiki\n\n## Overview\n\n"
    appendix = _generate_quality_report_appendix(wiki_content, [])

    assert "Wiki Quality Report" in appendix
    m = re.search(r"<!-- WIKI_QUALITY_JSON\n(.*?)\n-->", appendix, re.DOTALL)
    assert m is not None
    data = json.loads(m.group(1))
    assert data["coverage"]["total"] == 0


def test_quality_appendix_no_sections():
    """Wiki 无 section 时的处理。"""
    from mindforge.wiki_service import _generate_quality_report_appendix

    wiki_content = "# Wiki\n\n## Overview\n\nNo sections yet.\n"
    card = _make_card("c1", "Only Card")

    appendix = _generate_quality_report_appendix(wiki_content, [card])
    m = re.search(r"<!-- WIKI_QUALITY_JSON\n(.*?)\n-->", appendix, re.DOTALL)
    assert m is not None
    data = json.loads(m.group(1))
    # No sections used → all approved cards are unused
    assert len(data["unused_cards"]) == 1


def test_quality_json_structure():
    """验证 quality JSON 包含所有预期字段。"""
    from mindforge.wiki_service import _generate_quality_report_appendix

    wiki_content = (
        "# Wiki\n\n"
        "<!-- WIKI_SECTION_START card=c1 -->\n"
        "### Card One\n\nSome content here.\n\n"
        "<!-- WIKI_SECTION_END -->\n"
        "---\n\n"
    )
    cards = [_make_card("c1", "Card One", tags=("ml",))]

    appendix = _generate_quality_report_appendix(wiki_content, cards)
    m = re.search(r"<!-- WIKI_QUALITY_JSON\n(.*?)\n-->", appendix, re.DOTALL)
    assert m is not None
    data = json.loads(m.group(1))

    # 所有顶层字段应存在
    assert "coverage" in data
    assert "unused_cards" in data
    assert "used_cards" in data
    assert "faithfulness" in data
    assert "faithfulness_issues" in data
    assert "stale_sections" in data
    assert "knowledge_gaps" in data
    assert "conflicting_claims" in data
    assert "section_count" in data

    # 类型检查
    assert isinstance(data["coverage"]["rate"], (int, float))
    assert isinstance(data["faithfulness"]["average"], (int, float))
    assert isinstance(data["unused_cards"], list)
    assert isinstance(data["used_cards"], list)


def test_deterministic_quality_same_input_same_output():
    """相同输入应产生完全相同的 quality report。"""
    from mindforge.wiki_service import _generate_quality_report_appendix

    wiki_content = (
        "# Wiki\n\n"
        "<!-- WIKI_SECTION_START card=c1 -->\n"
        "### Card One\n\nMachine learning fundamentals.\n\n"
        "<!-- WIKI_SECTION_END -->\n"
    )
    cards = [_make_card("c1", "Card One", tags=("ml",))]

    r1 = _generate_quality_report_appendix(wiki_content, cards)
    r2 = _generate_quality_report_appendix(wiki_content, cards)
    assert r1 == r2, "相同输入应产生相同输出"
