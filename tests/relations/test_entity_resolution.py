"""v3.9 Entity Resolution contract tests — 验证 ConceptCandidate 检测与边界。

中文学习型说明：所有测试使用合成数据，不调用真实 LLM / embedding。
验证确定性规则（exact match / substring / shared context）的正确性，
以及 Entity ≠ ConceptCandidate 的建模边界。
"""

from __future__ import annotations

from mindforge.relations.entity_resolution import (
    ConceptCandidate,
    _normalize,
    _tokenize,
    detect_concept_candidates,
)


class TestNormalizeAndTokenize:
    """规范化与分词工具测试。"""

    def test_normalize_lowercase_and_strip(self):
        assert _normalize("Transformer 架构") == "transformer架构"
        assert _normalize("  Hello  World!  ") == "helloworld"

    def test_normalize_removes_special_chars(self):
        assert _normalize("C++ Programming") == "cprogramming"
        assert _normalize("machine-learning") == "machinelearning"

    def test_tokenize_extracts_english_tokens(self):
        tokens = _tokenize("Reinforcement Learning in Deep Networks")
        assert "reinforcement" in tokens
        assert "learning" in tokens
        assert "deep" in tokens
        assert "networks" in tokens
        # stopwords are filtered
        assert "in" not in tokens

    def test_tokenize_extracts_chinese_tokens(self):
        """中文字符按连续 2-8 字提取为一个 token。
        无词典条件下，"梯度下降优化算法"（7 字）作为一个整体 token，不做子词切分。
        """
        tokens = _tokenize("梯度下降优化算法")
        assert "梯度下降优化算法" in tokens

    def test_tokenize_filters_short_english(self):
        tokens = _tokenize("a b c de ab")
        # single chars filtered, "de" and "ab" kept (>=2)
        assert "de" in tokens
        assert "ab" in tokens
        assert "a" not in tokens

    def test_tokenize_filters_stopwords(self):
        tokens = _tokenize("the quick brown fox")
        assert "the" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens


class TestConceptCandidateDataclass:
    """ConceptCandidate 数据类单元测试。"""

    def test_candidate_is_frozen(self):
        c = ConceptCandidate(
            label="Test Entity",
            normalized_label="testentity",
            source_card_ids=("card_1", "card_2"),
            confidence=0.8,
            evidence="found in 2 cards",
            source_type="tag",
        )
        # frozen dataclass: 不应可修改
        try:
            c.confidence = 0.9  # type: ignore[misc]
            frozen = False
        except Exception:
            frozen = True
        assert frozen, "ConceptCandidate 必须是 frozen dataclass"

    def test_card_count_property(self):
        c = ConceptCandidate(
            label="Test",
            normalized_label="test",
            source_card_ids=("c1", "c2", "c3"),
        )
        assert c.card_count == 3

    def test_candidate_with_aliases(self):
        c = ConceptCandidate(
            label="Reinforcement Learning",
            normalized_label="reinforcementlearning",
            aliases=("RL", "reinforcement-learning"),
        )
        assert "RL" in c.aliases

    def test_default_values(self):
        c = ConceptCandidate(label="X", normalized_label="x")
        assert c.aliases == ()
        assert c.source_card_ids == ()
        assert c.confidence == 0.0
        assert c.evidence == ""
        assert c.source_type == "title"


class TestDetectConceptCandidates:
    """detect_concept_candidates 确定性规则测试。"""

    def _card(self, id_: str, title: str, tags=None, sections=None, body=""):
        return {
            "id": id_,
            "title": title,
            "tags": tags or [],
            "wiki_sections": sections or [],
            "body_summary": body,
        }

    def test_empty_cards_returns_empty(self):
        result = detect_concept_candidates([])
        assert result == []

    def test_single_card_no_candidates(self):
        """只有一张卡片的 token 不产生候选（至少 2 张卡提及）。"""
        cards = [self._card("c1", "Transformer Architecture", ["deep-learning"], ["Architecture"], "attention mechanism")]
        result = detect_concept_candidates(cards)
        assert len(result) == 0

    def test_exact_match_title_tokens(self):
        """两张卡片标题包含相同 token → candidate detected。"""
        cards = [
            self._card("c1", "Reinforcement Learning Basics"),
            self._card("c2", "Advanced Reinforcement Learning"),
        ]
        result = detect_concept_candidates(cards)
        labels = {c.label for c in result}
        assert "reinforcement" in labels
        assert "learning" in labels

    def test_exact_match_tag(self):
        """共享 tag → candidate detected。"""
        cards = [
            self._card("c1", "Card A", ["machine-learning"]),
            self._card("c2", "Card B", ["machine-learning"]),
            self._card("c3", "Card C", ["machine-learning"]),
        ]
        result = detect_concept_candidates(cards)
        tags = [c for c in result if c.source_type == "tag"]
        assert len(tags) >= 1
        ml = next((c for c in tags if "machinelearning" in c.normalized_label), None)
        assert ml is not None
        assert ml.card_count == 3

    def test_wiki_section_co_occurrence(self):
        """同一 wiki section 下的多张卡片 → 共享 topic candidate。"""
        cards = [
            self._card("c1", "Intro to RL", sections=["Reinforcement Learning"]),
            self._card("c2", "Policy Gradients", sections=["Reinforcement Learning"]),
            self._card("c3", "Q-Learning Deep Dive", sections=["Reinforcement Learning"]),
        ]
        result = detect_concept_candidates(cards)
        sections = [c for c in result if c.source_type == "wiki_section"]
        assert len(sections) >= 1

    def test_body_token_candidates(self):
        """body_summary 中重复出现的 token → candidate detected。"""
        cards = [
            self._card("c1", "Card 1", body="Understanding attention mechanism in transformers"),
            self._card("c2", "Card 2", body="Attention mechanism is key to transformer models"),
        ]
        result = detect_concept_candidates(cards)
        labels = {c.label for c in result}
        assert "attention" in labels
        assert "mechanism" in labels

    def test_multi_source_confidence(self):
        """来自多种 source (title+tag+body) 的 candidate 置信度更高。"""
        cards = [
            self._card("c1", "Deep Learning Overview", ["deep-learning"], body="deep learning fundamentals"),
            self._card("c2", "Deep Learning in Practice", ["deep-learning"], body="practical deep learning"),
            self._card("c3", "ML Basics", ["deep-learning"], body="intro to deep learning"),
        ]
        result = detect_concept_candidates(cards)
        assert len(result) > 0
        # 所有 candidate 置信度在 0.0-1.0
        for c in result:
            assert 0.0 <= c.confidence <= 1.0, f"confidence {c.confidence} out of range"

    def test_min_confidence_filter(self):
        """低于 min_confidence 的候选被过滤。"""
        cards = [
            self._card("c1", "A card", body="token"),
            self._card("c2", "B card", body="token"),
        ]
        # min_confidence=0.5 is high, should filter most
        result = detect_concept_candidates(cards, min_confidence=0.5)
        # With default confidence calc, this may or may not produce results
        # depending on token specificity
        assert all(c.confidence >= 0.5 for c in result)

    def test_max_candidates_limit(self):
        """max_candidates 限制返回数量。"""
        cards = [
            self._card(f"c{i:03d}", f"Card about concept_{i}", [f"tag-{i % 5}"], body=f"concept_{i} concept_{i+1} concept_{i+2}")
            for i in range(20)
        ]
        result = detect_concept_candidates(cards, max_candidates=10)
        assert len(result) <= 10

    def test_result_sorted_by_confidence(self):
        """结果按置信度降序排列。"""
        cards = [
            self._card("c1", "Reinforcement Learning", ["rl"], body="reinforcement learning policy gradient"),
            self._card("c2", "Deep RL", ["rl"], body="deep reinforcement learning"),
            self._card("c3", "RL Applications", ["rl"], body="reinforcement learning in practice"),
        ]
        result = detect_concept_candidates(cards)
        for i in range(len(result) - 1):
            assert result[i].confidence >= result[i + 1].confidence

    def test_evidence_is_human_readable(self):
        """evidence 必须是人类可读的描述，不是 machine token。"""
        cards = [
            self._card("c1", "Transformer Architecture", ["transformer"], body="attention is all you need"),
            self._card("c2", "BERT Model", ["transformer"], body="bidirectional encoder representations"),
        ]
        result = detect_concept_candidates(cards)
        for c in result:
            assert "card_id" not in c.evidence.lower() or "↔" not in c.evidence
            assert len(c.evidence) > 0


class TestEntityVsConceptCandidateBoundary:
    """Entity ≠ ConceptCandidate 边界测试。

    中文学习型说明：这些测试确保 ConceptCandidate 检测不会自动将候选升级为
    已确认 Entity。升级必须经过 explicit human approval pipeline。
    """

    def test_concept_candidate_has_no_approved_flag(self):
        """ConceptCandidate 没有 is_approved / status 字段 —
        它们是 candidate graph 的一部分，不能有审批状态。"""
        c = ConceptCandidate(
            label="Test",
            normalized_label="test",
            source_card_ids=("c1",),
            confidence=0.9,
        )
        # ConceptCandidate 不应有 status 或 approved 字段
        assert not hasattr(c, "status")
        assert not hasattr(c, "approved")
        assert not hasattr(c, "is_approved")

    def test_detect_does_not_modify_cards(self):
        """detect_concept_candidates 是纯函数，不修改输入 cards。"""
        cards = [
            {"id": "c1", "title": "Original Title", "tags": ["ai"], "wiki_sections": [], "body_summary": "content"},
            {"id": "c2", "title": "Another Title", "tags": ["ai"], "wiki_sections": [], "body_summary": "content"},
        ]
        original_titles = [c["title"] for c in cards]
        detect_concept_candidates(cards)
        assert [c["title"] for c in cards] == original_titles

    def test_high_confidence_does_not_mean_approved(self):
        """高置信度 != 已确认。confidence 只是启发式分数，
        不能替代 explicit human approval。"""
        cards = [
            self._card(f"c{i:03d}", "Shared Entity Concept", ["shared-tag"], sections=["Shared Section"], body="shared entity concept body text")
            for i in range(10)
        ]
        result = detect_concept_candidates(cards)
        high_conf = [c for c in result if c.confidence >= 0.7]
        for c in high_conf:
            assert not hasattr(c, "approved")
            assert not hasattr(c, "status")

    def test_concept_candidate_type_is_candidate_not_entity(self):
        """从 NodeType 角度：CONCEPT_CANDIDATE ≠ ENTITY。
        所有检测结果属于 candidate graph。"""
        from mindforge.relations.graph_models import NodeType
        assert NodeType.CONCEPT_CANDIDATE != NodeType.ENTITY
        assert "candidate" in NodeType.CONCEPT_CANDIDATE.value
        assert "candidate" not in NodeType.ENTITY.value

    @staticmethod
    def _card(id_, title, tags=None, sections=None, body=""):
        return {
            "id": id_,
            "title": title,
            "tags": tags or [],
            "wiki_sections": sections or [],
            "body_summary": body,
        }
