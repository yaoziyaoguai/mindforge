"""M1 quality suggestions tests — SDD §5.3, RFC §7 FR1.5。

验证 regenerate / split / merge 建议规则。
"""
from tests.fixtures.quality_golden import (
    HIGH_QUALITY_CARDS,
    LOW_QUALITY_CARDS,
    SyntheticCard,
)


def _score_and_suggest(card: SyntheticCard):
    """完整的 quality scoring + suggestion 流程。"""
    from mindforge.quality.rubric import score_quality
    from mindforge.quality.warnings import detect_warnings
    from mindforge.quality.suggestions import generate_suggestions

    warnings = detect_warnings(
        title=card.title,
        body=card.body,
        source_id=card.source_id,
        source_path=card.source_path,
    )
    quality = score_quality(
        title=card.title,
        body=card.body,
        source_id=card.source_id,
        source_path=card.source_path,
        source_type=card.source_type,
        warnings=warnings,
    )
    return generate_suggestions(quality)


class TestSuggestions:
    """维护建议测试。"""

    def test_high_quality_card_no_regenerate_suggestion(self):
        """高质量卡片不应有 regenerate suggestion。"""
        card = HIGH_QUALITY_CARDS["well_structured_fact"]
        result = _score_and_suggest(card)
        assert result.regenerate_suggestion is None

    def test_low_quality_card_has_regenerate_suggestion(self):
        """低质量卡片应有 regenerate suggestion。"""
        card = LOW_QUALITY_CARDS["extremely_short"]
        result = _score_and_suggest(card)
        assert result.regenerate_suggestion is not None
        assert "regenerate" in result.regenerate_suggestion.lower()

    def test_no_structure_card_has_regenerate_suggestion(self):
        """无结构卡片应有 regenerate suggestion。"""
        card = LOW_QUALITY_CARDS["no_structure_at_all"]
        result = _score_and_suggest(card)
        assert result.regenerate_suggestion is not None

    def test_self_contradicting_card_has_regenerate_suggestion(self):
        """自相矛盾卡片应有 regenerate suggestion。"""
        card = LOW_QUALITY_CARDS["self_contradicting"]
        result = _score_and_suggest(card)
        assert result.regenerate_suggestion is not None

    def test_extremely_short_is_merge_candidate(self):
        """极短卡片应被视为 merge candidate。"""
        card = LOW_QUALITY_CARDS["extremely_short"]
        result = _score_and_suggest(card)
        assert result.merge_candidate is True

    def test_high_quality_not_split_candidate(self):
        """高质量卡片不应建议 split。"""
        card = HIGH_QUALITY_CARDS["well_structured_fact"]
        result = _score_and_suggest(card)
        assert result.split_candidate is False

    def test_suggestions_do_not_mutate_original(self):
        """generate_suggestions 返回新实例，不修改原 quality。"""
        from mindforge.quality.rubric import score_quality

        card = LOW_QUALITY_CARDS["extremely_short"]
        quality = score_quality(
            title=card.title,
            body=card.body,
            source_id=card.source_id,
            source_path=card.source_path,
        )
        original_score = quality.overall_score
        original_regenerate = quality.regenerate_suggestion

        from mindforge.quality.suggestions import generate_suggestions
        new_quality = generate_suggestions(quality)

        # 原实例不变
        assert quality.overall_score == original_score
        assert quality.regenerate_suggestion == original_regenerate
        # 新实例是独立对象
        assert new_quality is not quality
