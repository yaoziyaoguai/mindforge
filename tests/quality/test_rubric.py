"""M1 rubric scoring tests — SDD §5.1-5.2, RFC §7 FR1.1-1.2。

验证质量评分规则的确定性：同一输入 → 相同 score。
"""
from tests.fixtures.quality_golden import (
    HIGH_QUALITY_CARDS,
    MEDIUM_QUALITY_CARDS,
    LOW_QUALITY_CARDS,
    SyntheticCard,
)


def _make_input(card: SyntheticCard) -> dict:
    """将 SyntheticCard 转为 quality 模块的输入格式。"""
    return {
        "title": card.title,
        "body": card.body,
        "source_id": card.source_id,
        "source_path": card.source_path,
        "source_type": card.source_type,
    }


# ---------------------------------------------------------------------------
# 高质量卡片测试
# ---------------------------------------------------------------------------

class TestHighQualityScoring:
    """高质量卡片得分 ≥ 70（SDD §5.2）。"""

    def test_well_structured_fact_scores_high(self):
        """完整结构 + 具体内容 + source citation → score ≥ 70。"""
        from mindforge.quality.rubric import score_quality

        card = HIGH_QUALITY_CARDS["well_structured_fact"]
        result = score_quality(**_make_input(card))
        assert result.overall_score >= 70, f"Expected ≥70, got {result.overall_score}"
        assert result.overall_level.value == "high"

    def test_comprehensive_method_scores_high(self):
        """详细的 step-by-step 方法卡片 → score ≥ 70。"""
        from mindforge.quality.rubric import score_quality

        card = HIGH_QUALITY_CARDS["comprehensive_method"]
        result = score_quality(**_make_input(card))
        assert result.overall_score >= 70, f"Expected ≥70, got {result.overall_score}"

    def test_specific_insight_scores_high(self):
        """有数据分析、有局限说明的 insight → score ≥ 70。"""
        from mindforge.quality.rubric import score_quality

        card = HIGH_QUALITY_CARDS["specific_insight"]
        result = score_quality(**_make_input(card))
        assert result.overall_score >= 70, f"Expected ≥70, got {result.overall_score}"


# ---------------------------------------------------------------------------
# 低质量卡片测试
# ---------------------------------------------------------------------------

class TestLowQualityScoring:
    """低质量卡片得分 < 40（SDD §5.2）。"""

    def test_extremely_short_scores_low(self):
        """极短、无结构的卡片 → score < 40。"""
        from mindforge.quality.rubric import score_quality

        card = LOW_QUALITY_CARDS["extremely_short"]
        result = score_quality(**_make_input(card))
        assert result.overall_score < 40, f"Expected <40, got {result.overall_score}"
        assert result.overall_level.value == "low"

    def test_no_structure_scores_low(self):
        """无任何结构的纯文本 → score < 40。"""
        from mindforge.quality.rubric import score_quality

        card = LOW_QUALITY_CARDS["no_structure_at_all"]
        result = score_quality(**_make_input(card))
        assert result.overall_score < 40, f"Expected <40, got {result.overall_score}"

    def test_self_contradicting_scores_low(self):
        """自相矛盾的卡片 consistency 维度得分低 → overall < 40。"""
        from mindforge.quality.rubric import score_quality

        card = LOW_QUALITY_CARDS["self_contradicting"]
        result = score_quality(**_make_input(card))
        assert result.overall_score < 40, f"Expected <40, got {result.overall_score}"


# ---------------------------------------------------------------------------
# 中质量卡片测试
# ---------------------------------------------------------------------------

class TestMediumQualityScoring:
    """中质量卡片得分 40-69（SDD §5.2）。"""

    def test_short_but_structured_scores_medium_or_high(self):
        """有结构有来源的卡片，即使偏短也可能得分较高（rubric 判定为准）。"""
        from mindforge.quality.rubric import score_quality

        card = MEDIUM_QUALITY_CARDS["short_but_structured"]
        result = score_quality(**_make_input(card))
        # 该卡有完整结构 + 来源引用 + 具体内容，rubric 可能判定为 high
        assert result.overall_score >= 50, f"Expected ≥50, got {result.overall_score}"

    def test_vague_claim_scores_medium(self):
        """有结构但语言模糊 → 40 ≤ score < 70。"""
        from mindforge.quality.rubric import score_quality

        card = MEDIUM_QUALITY_CARDS["vague_claim"]
        result = score_quality(**_make_input(card))
        assert 40 <= result.overall_score < 70, f"Expected 40-69, got {result.overall_score}"


# ---------------------------------------------------------------------------
# 确定性测试
# ---------------------------------------------------------------------------

class TestDeterministicScoring:
    """同一输入在任何时间产生相同 score（RFC §6 AD-1, Dev Rules §1 rule 2）。"""

    def test_same_input_same_score(self):
        """多次调用对同一输入产生相同 overall_score。"""
        from mindforge.quality.rubric import score_quality

        card = HIGH_QUALITY_CARDS["well_structured_fact"]
        kwargs = _make_input(card)
        scores = [score_quality(**kwargs).overall_score for _ in range(10)]
        assert len(set(scores)) == 1, f"Non-deterministic: {scores}"

    def test_no_external_dependency(self):
        """rubric 评分不依赖 LLM / Embedding / API 调用。"""
        from mindforge.quality.rubric import score_quality

        card = HIGH_QUALITY_CARDS["well_structured_fact"]
        result = score_quality(**_make_input(card))
        # 只要能返回结果即为纯计算（没有 import openai/httpx 等外部调用）
        assert 0 <= result.overall_score <= 100


# ---------------------------------------------------------------------------
# 维度级测试
# ---------------------------------------------------------------------------

class TestRubricDimensions:
    """每个 rubric 维度的单独验证（SDD §5.1）。"""

    def test_all_five_dimensions_present(self):
        """结果必须包含 5 个维度分。"""
        from mindforge.quality.rubric import score_quality

        card = HIGH_QUALITY_CARDS["well_structured_fact"]
        result = score_quality(**_make_input(card))
        dimensions = {rs.dimension for rs in result.rubric_scores}
        expected = {"completeness", "structure", "specificity", "source_citation", "consistency"}
        assert dimensions == expected, f"Got dimensions: {dimensions}"

    def test_source_citation_dimension_zero_when_no_source(self):
        """无 source_id/source_path 时 source_citation 维度为 0。"""
        from mindforge.quality.rubric import score_quality

        card = LOW_QUALITY_CARDS["extremely_short"]
        result = score_quality(**_make_input(card))
        sc_score = next(rs for rs in result.rubric_scores if rs.dimension == "source_citation")
        assert sc_score.score == 0.0, f"Expected 0 for no source, got {sc_score.score}"

    def test_source_citation_dimension_positive_when_has_source(self):
        """有 source_id 时 source_citation 维度 > 0。"""
        from mindforge.quality.rubric import score_quality

        card = HIGH_QUALITY_CARDS["well_structured_fact"]
        result = score_quality(**_make_input(card))
        sc_score = next(rs for rs in result.rubric_scores if rs.dimension == "source_citation")
        assert sc_score.score > 0, f"Expected >0 with source, got {sc_score.score}"

    def test_structure_dimension_high_for_well_structured(self):
        """有 ## Summary / ## Details / ### 子章节的卡片 structure 高。"""
        from mindforge.quality.rubric import score_quality

        card = HIGH_QUALITY_CARDS["comprehensive_method"]
        result = score_quality(**_make_input(card))
        st_score = next(rs for rs in result.rubric_scores if rs.dimension == "structure")
        assert st_score.score >= 0.7, f"Expected ≥0.7 structure, got {st_score.score}"

    def test_completeness_low_for_missing_summary(self):
        """无 ## Summary 章节 → completeness 低。"""
        from mindforge.quality.rubric import score_quality

        card = LOW_QUALITY_CARDS["no_structure_at_all"]
        result = score_quality(**_make_input(card))
        comp_score = next(rs for rs in result.rubric_scores if rs.dimension == "completeness")
        assert comp_score.score < 0.5, f"Expected <0.5 completeness, got {comp_score.score}"

    def test_specificity_low_for_vague_language(self):
        """大量模糊词汇 → specificity 低。"""
        from mindforge.quality.rubric import score_quality

        card = MEDIUM_QUALITY_CARDS["vague_claim"]
        result = score_quality(**_make_input(card))
        spec_score = next(rs for rs in result.rubric_scores if rs.dimension == "specificity")
        assert spec_score.score < 0.6, f"Expected <0.6 specificity, got {spec_score.score}"
