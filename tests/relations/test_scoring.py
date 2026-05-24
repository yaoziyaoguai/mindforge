"""v1.2 Relation Scoring — 加权评分单元测试。"""

from mindforge.relations.scoring import (
    RelationWeights,
    compute_tag_strength,
    compute_source_strength,
    compute_wiki_strength,
    compute_recency_bonus,
    compute_multi_factor_strength,
)


class TestTagStrength:
    def test_single_tag_is_base_weight(self):
        strength = compute_tag_strength(1)
        assert abs(strength - 0.5) < 0.001

    def test_two_tags_adds_bonus(self):
        strength = compute_tag_strength(2)
        assert abs(strength - 0.6) < 0.001  # 0.5 + 0.1

    def test_three_tags_adds_double_bonus(self):
        strength = compute_tag_strength(3)
        assert abs(strength - 0.7) < 0.001  # 0.5 + 0.2

    def test_four_tags_capped_at_triple_bonus(self):
        strength = compute_tag_strength(5)
        assert abs(strength - 0.8) < 0.001  # 0.5 + 0.3 (capped)

    def test_tag_strength_never_exceeds_095(self):
        w = RelationWeights(tag_base=0.9)
        strength = compute_tag_strength(4, w)
        assert strength <= 0.95


class TestWikiStrength:
    def test_single_section_is_base_weight(self):
        strength = compute_wiki_strength(1)
        assert strength == 0.7

    def test_two_sections_adds_bonus(self):
        strength = compute_wiki_strength(2)
        assert abs(strength - 0.8) < 0.001  # 0.7 + 0.1


class TestSourceStrength:
    def test_source_strength_is_fixed(self):
        strength = compute_source_strength(1)
        assert strength == 0.8
        strength = compute_source_strength(3)
        assert strength == 0.8  # source strength 固定


class TestRecencyBonus:
    def test_none_date_returns_zero(self):
        bonus = compute_recency_bonus(None)
        assert bonus == 0.0

    def test_recent_date_returns_full_bonus(self):
        bonus = compute_recency_bonus("2026-05-20T00:00:00", now_iso="2026-05-25T00:00:00")
        assert bonus == 0.1  # 5 days, within 30

    def test_old_date_returns_zero(self):
        bonus = compute_recency_bonus("2025-01-01T00:00:00", now_iso="2026-05-25T00:00:00")
        assert bonus == 0.0  # over 90 days


class TestMultiFactorStrength:
    def test_base_is_returned_with_no_extras(self):
        strength = compute_multi_factor_strength(0.5)
        assert abs(strength - 0.5) < 0.001

    def test_recency_bonus_is_added(self):
        strength = compute_multi_factor_strength(0.5, recency_bonus=0.1)
        assert strength == 0.6

    def test_clamped_low(self):
        strength = compute_multi_factor_strength(0.01, recency_bonus=0.0)
        assert strength == 0.05

    def test_clamped_high(self):
        strength = compute_multi_factor_strength(1.0, recency_bonus=0.1)
        assert strength <= 0.99
