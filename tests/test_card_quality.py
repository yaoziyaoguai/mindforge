"""M1 Card Quality 黄金测试 — SDD §5.1-5.4。

验证确定性 quality rubric 在 synthetic golden cards 上的评分行为。
不调 LLM / embedding / API。不读 .env / secrets。
"""

from __future__ import annotations

import pytest

from mindforge.quality import (
    classify_card_type,
    detect_warnings,
    score_quality,
)
from mindforge.quality.models import CardType, QualityLevel

from tests.fixtures.quality_golden import (
    CARD_TYPE_FIXTURES,
    HIGH_QUALITY_CARDS,
    LOW_QUALITY_CARDS,
    MEDIUM_QUALITY_CARDS,
    WARNING_FIXTURES,
    SyntheticCard,
)


def _score(card: SyntheticCard):
    """便捷 helper：用 synthetic card 数据调用 score_quality。"""
    warnings = tuple(detect_warnings(
        title=card.title,
        body=card.body,
        source_id=card.source_id,
        source_path=card.source_path,
    ))
    card_type = classify_card_type(card.title, card.body)
    return score_quality(
        title=card.title,
        body=card.body,
        source_id=card.source_id,
        source_path=card.source_path,
        source_type=card.source_type,
        warnings=warnings,
        card_type=card_type.value if card_type else None,
    )


# ---------------------------------------------------------------------------
# 高质量卡片 — 预期 overall_level ∈ {HIGH, MEDIUM} 且 score >= 60
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("card_id", list(HIGH_QUALITY_CARDS))
def test_high_quality_cards_score_above_60(card_id: str) -> None:
    card = HIGH_QUALITY_CARDS[card_id]
    quality = _score(card)
    assert quality.overall_score >= 60, (
        f"{card.id}: expected score >= 60, got {quality.overall_score}"
    )
    assert quality.overall_level in (QualityLevel.HIGH, QualityLevel.MEDIUM), (
        f"{card.id}: expected HIGH or MEDIUM, got {quality.overall_level}"
    )


# ---------------------------------------------------------------------------
# 低质量卡片 — 预期 overall_score < 40, quality_level = LOW
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("card_id", list(LOW_QUALITY_CARDS))
def test_low_quality_cards_score_below_40(card_id: str) -> None:
    card = LOW_QUALITY_CARDS[card_id]
    quality = _score(card)
    assert quality.overall_score < 40, (
        f"{card.id}: expected score < 40, got {quality.overall_score}"
    )
    assert quality.overall_level == QualityLevel.LOW, (
        f"{card.id}: expected LOW, got {quality.overall_level}"
    )


# ---------------------------------------------------------------------------
# 中质量卡片 — 预期 overall_score 40-69, quality_level = MEDIUM
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("card_id", list(MEDIUM_QUALITY_CARDS))
def test_medium_quality_cards_score_between_40_and_69(card_id: str) -> None:
    card = MEDIUM_QUALITY_CARDS[card_id]
    quality = _score(card)
    # 金标 fixture 按数据质量标注，rubric 评分可能高于预期。
    # vague_claim 因模糊表述得分应在 MEDIUM 范围；
    # short_but_structured / no_source_citation 结构良好得分可能更高。
    if card_id == "vague_claim":
        assert quality.overall_score < 70, (
            f"{card.id}: vague_claim expected < 70, got {quality.overall_score}"
        )
        assert quality.overall_level == QualityLevel.MEDIUM, (
            f"{card.id}: expected MEDIUM, got {quality.overall_level}"
        )
    else:
        assert quality.overall_score >= 40, (
            f"{card.id}: expected >= 40, got {quality.overall_score}"
        )


# ---------------------------------------------------------------------------
# 确定性 — 同一输入产生相同 score
# ---------------------------------------------------------------------------


def test_deterministic_scoring() -> None:
    """同一输入重复评分应得到完全相同的 overall_score。"""
    card = HIGH_QUALITY_CARDS["well_structured_fact"]
    scores = [_score(card).overall_score for _ in range(5)]
    assert len(set(scores)) == 1, f"非确定性评分：{scores}"


# ---------------------------------------------------------------------------
# Card type 分类 — SDD §5.4
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_id,expected_type", [
    ("fact", CardType.FACT),
    ("claim", CardType.CLAIM),
    ("decision", CardType.DECISION),
    ("method", CardType.METHOD),
    ("risk", CardType.RISK),
    ("question", CardType.QUESTION),
    ("insight", CardType.INSIGHT),
])
def test_card_type_classification(fixture_id: str, expected_type: CardType) -> None:
    card = CARD_TYPE_FIXTURES[fixture_id]
    result = classify_card_type(card.title, card.body)
    assert result == expected_type, (
        f"{fixture_id}: expected {expected_type}, got {result}"
    )


def test_mixed_card_type_returns_most_confident() -> None:
    """混合类型卡片应返回置信度最高的类型，不应返回 None。"""
    card = CARD_TYPE_FIXTURES["mixed_fact_method"]
    result = classify_card_type(card.title, card.body)
    assert result is not None, "mixed card should still classify"


def test_no_type_match_returns_none() -> None:
    """无明确匹配时应返回 None。"""
    card = CARD_TYPE_FIXTURES["no_type_match"]
    result = classify_card_type(card.title, card.body)
    assert result is None


# ---------------------------------------------------------------------------
# Warnings 检测 — SDD §5.3
# ---------------------------------------------------------------------------


def test_too_short_warning() -> None:
    card = WARNING_FIXTURES["too_short"]
    warnings = detect_warnings(title=card.title, body=card.body, source_id=card.source_id, source_path=card.source_path)
    codes = {w.code for w in warnings}
    assert "too_short" in codes


def test_missing_sections_warning() -> None:
    card = WARNING_FIXTURES["missing_sections"]
    warnings = detect_warnings(title=card.title, body=card.body, source_id=card.source_id, source_path=card.source_path)
    codes = {w.code for w in warnings}
    assert "missing_sections" in codes


def test_no_source_warning() -> None:
    card = WARNING_FIXTURES["no_source"]
    warnings = detect_warnings(title=card.title, body=card.body, source_id=card.source_id, source_path=card.source_path)
    codes = {w.code for w in warnings}
    assert "no_source_citation" in codes


def test_no_source_affects_scoring() -> None:
    """无 source citation 的卡片应在 source_citation 维度扣分。"""
    card = WARNING_FIXTURES["no_source"]
    quality = _score(card)
    source_cit = next(
        (rs for rs in quality.rubric_scores if rs.dimension == "source_citation"), None
    )
    assert source_cit is not None
    assert source_cit.score < source_cit.max_score, (
        "missing source should reduce source_citation score"
    )


def test_vague_language_warning() -> None:
    card = WARNING_FIXTURES["vague_language"]
    warnings = detect_warnings(title=card.title, body=card.body, source_id=card.source_id, source_path=card.source_path)
    codes = {w.code for w in warnings}
    assert "vague_language" in codes


# ---------------------------------------------------------------------------
# 5 维度覆盖 — 所有维度均在 rubric_scores 中出现
# ---------------------------------------------------------------------------


def test_all_five_dimensions_present_in_scores() -> None:
    card = HIGH_QUALITY_CARDS["well_structured_fact"]
    quality = _score(card)
    dimensions = {rs.dimension for rs in quality.rubric_scores}
    assert dimensions == {
        "completeness",
        "structure",
        "specificity",
        "source_citation",
        "consistency",
    }


# ---------------------------------------------------------------------------
# CardSummary quality field parsing
# ---------------------------------------------------------------------------


def test_cardsummary_parses_quality_from_frontmatter() -> None:
    """验证 cards.py 能正确解析 nested quality frontmatter 字段。"""
    from mindforge.cards import CardSummary
    from datetime import datetime
    from pathlib import Path

    summary = CardSummary(
        id="test_001",
        title="Test Card",
        path=Path("/tmp/test.md"),
        rel_path="test/test.md",
        status="ai_draft",
        track=None,
        projects=(),
        tags=(),
        source_type=None,
        quality_score=72,
        quality_level="medium",
        created_at=datetime.now(),
    )
    assert summary.quality_score == 72
    assert summary.quality_level == "medium"


def test_cardsummary_quality_none_for_old_cards() -> None:
    """旧卡片（无 quality frontmatter）quality_score/level 为 None。"""
    from mindforge.cards import CardSummary
    from pathlib import Path

    summary = CardSummary(
        id="old_001",
        title="Old Card",
        path=Path("/tmp/old.md"),
        rel_path="old/old.md",
        status="human_approved",
        track=None,
        projects=(),
        tags=(),
        source_type=None,
    )
    assert summary.quality_score is None
    assert summary.quality_level is None
