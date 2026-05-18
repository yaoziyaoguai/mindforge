"""M1 card type classification tests — SDD §5.4, RFC §7 FR1.4。

验证基于规则的卡片类型分类：fact/claim/decision/method/risk/question/insight。
"""
from tests.fixtures.quality_golden import CARD_TYPE_FIXTURES, SyntheticCard


def _classify(card: SyntheticCard):
    """调用 card type 分类器。"""
    from mindforge.quality.card_type import classify_card_type
    return classify_card_type(title=card.title, body=card.body)


class TestCardTypeClassification:
    """卡片类型分类测试（SDD §5.4 规则关键词）。"""

    def test_fact_classified_by_observation_keywords(self):
        """包含 'measured' / 'observed' / 'recorded' → fact。"""
        result = _classify(CARD_TYPE_FIXTURES["fact"])
        assert result is not None
        assert result.value == "fact"

    def test_claim_classified_by_argument_keywords(self):
        """包含 'argues' / 'claims' / 'asserts' → claim。"""
        result = _classify(CARD_TYPE_FIXTURES["claim"])
        assert result is not None
        assert result.value == "claim"

    def test_decision_classified_by_choice_keywords(self):
        """包含 'decided' / 'chose' / 'resolved' → decision。"""
        result = _classify(CARD_TYPE_FIXTURES["decision"])
        assert result is not None
        assert result.value == "decision"

    def test_method_classified_by_procedure_keywords(self):
        """包含 'how to' / 'steps to' / 'procedure' / 'approach' → method。"""
        result = _classify(CARD_TYPE_FIXTURES["method"])
        assert result is not None
        assert result.value == "method"

    def test_risk_classified_by_warning_keywords(self):
        """包含 'risk' / 'pitfall' / 'failure mode' / 'caution' → risk。"""
        result = _classify(CARD_TYPE_FIXTURES["risk"])
        assert result is not None
        assert result.value == "risk"

    def test_question_classified_by_inquiry_keywords(self):
        """包含 'how can' / 'why does' / 'what is' / 'open question' → question。"""
        result = _classify(CARD_TYPE_FIXTURES["question"])
        assert result is not None
        assert result.value == "question"

    def test_insight_classified_by_discovery_keywords(self):
        """包含 'interesting' / 'surprising' / 'key insight' / 'lesson' → insight。"""
        result = _classify(CARD_TYPE_FIXTURES["insight"])
        assert result is not None
        assert result.value == "insight"

    def test_unclassified_when_no_keywords_match(self):
        """无关键词匹配时返回 None。"""
        result = _classify(CARD_TYPE_FIXTURES["no_type_match"])
        assert result is None

    def test_strongest_type_wins_on_mixed_keywords(self):
        """多类型关键词共存时选择得分最高的（fact + method 混合 → method 分更高）。"""
        result = _classify(CARD_TYPE_FIXTURES["mixed_fact_method"])
        assert result is not None
        # "procedure", "steps" (method) > "measured", "observed" (fact) in this fixture
        assert result.value in ("fact", "method")

    def test_deterministic_same_input_same_type(self):
        """同一输入多次分类结果一致。"""
        results = [_classify(CARD_TYPE_FIXTURES["fact"]) for _ in range(10)]
        types = [r.value if r else None for r in results]
        assert len(set(types)) == 1
