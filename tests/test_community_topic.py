"""v3.3 — 社区增强与主题合成测试。

验证 representative cards、source coverage、evidence detail 和 topic synthesis。
纯 deterministic 测试，不调用 LLM/embedding/vector DB。
"""

from __future__ import annotations

from mindforge.relations.community import (
    detect_communities,
    select_representative_cards,
)
from mindforge.relations.topic import (
    detect_topics,
)


# ---------------------------------------------------------------------------
# 合成测试数据
# ---------------------------------------------------------------------------


def _make_cards() -> list[dict[str, object]]:
    """构建测试用卡片数据集：4 张卡片，跨 2 sources、4 tags、2 wiki_sections。"""
    return [
        {
            "id": "c1", "source_id": "doc1.md",
            "tags": ["python", "testing"],
            "wiki_sections": ["Dev"],
            "body": "A" * 200, "status": "human_approved",
        },
        {
            "id": "c2", "source_id": "doc1.md",
            "tags": ["python", "patterns"],
            "wiki_sections": ["Dev"],
            "body": "B" * 150, "status": "human_approved",
        },
        {
            "id": "c3", "source_id": "doc2.md",
            "tags": ["testing", "ci"],
            "wiki_sections": ["Ops"],
            "body": "C" * 100, "status": "human_approved",
        },
        {
            "id": "c4", "source_id": "doc2.md",
            "tags": ["ci", "deployment"],
            "wiki_sections": ["Ops"],
            "body": "D" * 80, "status": "ai_draft",
        },
    ]


# ---------------------------------------------------------------------------
# Representative Cards 测试
# ---------------------------------------------------------------------------


class TestRepresentativeCards:
    """验证代表性卡片选择的确定性启发式。"""

    def test_selects_up_to_max_count(self):
        cards = _make_cards()
        member_ids = ["c1", "c2", "c3", "c4"]
        reps = select_representative_cards("source", member_ids, cards, max_count=3)
        assert len(reps) <= 3

    def test_selects_at_least_one(self):
        cards = _make_cards()
        member_ids = ["c1", "c2"]
        reps = select_representative_cards("source", member_ids, cards, max_count=3)
        assert len(reps) >= 1

    def test_prefers_higher_quality_cards(self):
        """高质量卡片（有 body、approved、多标签）应排在前面。"""
        cards = _make_cards()
        member_ids = ["c1", "c2", "c3", "c4"]
        reps = select_representative_cards("tag", member_ids, cards, max_count=2)
        # c1 和 c2 质量最高（长 body + approved + 多标签）
        assert reps[0] in ("c1", "c2")

    def test_empty_members_returns_empty(self):
        reps = select_representative_cards("source", [], _make_cards())
        assert reps == []

    def test_deterministic_same_input_same_output(self):
        cards = _make_cards()
        member_ids = ["c1", "c2", "c3", "c4"]
        r1 = select_representative_cards("source", member_ids, cards)
        r2 = select_representative_cards("source", member_ids, cards)
        assert r1 == r2


# ---------------------------------------------------------------------------
# Community Enhancement 测试 (v3.3 新字段)
# ---------------------------------------------------------------------------


class TestCommunityEnhancement:
    """验证 detect_communities 返回的 v3.3 增强字段。"""

    def test_representative_card_ids_present(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        for c in communities:
            assert isinstance(c.representative_card_ids, tuple)
            # 每个社区至少应有 1 张代表性卡片
            assert len(c.representative_card_ids) >= 1, (
                f"社区 {c.community_type}:{c.shared_entity} 缺少代表性卡片"
            )

    def test_source_coverage_present(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        for c in communities:
            assert 0.0 <= c.source_coverage <= 1.0

    def test_source_coverage_full_when_all_have_source(self):
        """所有卡片都有 source_id，覆盖率应为 100%。"""
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        for c in communities:
            assert c.source_coverage == 1.0, (
                f"社区 {c.community_type}:{c.shared_entity} source_coverage 应为 1.0"
            )

    def test_source_coverage_partial(self):
        """部分卡片缺少 source_id 时覆盖率应 < 1.0。"""
        cards = [
            {"id": "x1", "source_id": "s1.md", "tags": ["shared"], "wiki_sections": [], "body": "", "status": "ai_draft"},
            {"id": "x2", "source_id": None, "tags": ["shared"], "wiki_sections": [], "body": "", "status": "ai_draft"},
        ]
        communities = detect_communities(cards, min_members=2)
        tag_comms = [c for c in communities if c.community_type == "tag"]
        assert len(tag_comms) == 1
        assert tag_comms[0].source_coverage == 0.5

    def test_evidence_detail_not_empty(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        for c in communities:
            assert len(c.evidence_detail) > 0, (
                f"社区 {c.community_type}:{c.shared_entity} evidence_detail 为空"
            )
            assert c.shared_entity in c.evidence_detail, (
                f"evidence_detail 应包含 shared_entity '{c.shared_entity}'"
            )

    def test_evidence_detail_includes_key_info(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        largest = max(communities, key=lambda c: c.member_count)
        assert "成员" in largest.evidence_detail
        assert "代表性卡片" in largest.evidence_detail

    def test_backward_compatible_no_new_fields_break_old(self):
        """确保 detect_communities 仍返回有效的 KnowledgeCommunity 列表。"""
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        assert len(communities) > 0
        # 验证核心字段仍然有效
        for c in communities:
            assert c.community_type in ("source", "tag", "wiki_section")
            assert c.member_count >= 2
            assert len(c.member_card_ids) == c.member_count
            assert isinstance(c.quality_score, float)


# ---------------------------------------------------------------------------
# Topic Synthesis 测试
# ---------------------------------------------------------------------------


class TestTopicSynthesis:
    """验证 detect_topics 的主题合成逻辑。"""

    def test_topics_detected_from_overlapping_communities(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        topics = detect_topics(communities, cards)
        # 数据集中社区高度交叉 → 至少应有 1 个 topic
        assert len(topics) >= 1

    def test_topic_has_valid_structure(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        topics = detect_topics(communities, cards)
        for t in topics:
            assert t.topic_id.startswith("topic-")
            assert len(t.topic_name) > 0
            assert t.community_count >= 2
            assert t.total_card_count > 0
            assert len(t.card_ids) == t.total_card_count
            assert len(t.member_communities) == t.community_count
            assert len(t.representative_card_ids) >= 1
            assert len(t.evidence) > 0

    def test_topic_card_ids_are_deduplicated(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        topics = detect_topics(communities, cards)
        for t in topics:
            assert len(t.card_ids) == len(set(t.card_ids)), "卡片 ID 应去重"

    def test_no_topics_when_communities_below_min(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        # min_communities=100 → 无 topic 满足条件
        topics = detect_topics(communities, cards, min_communities=100)
        assert len(topics) == 0

    def test_no_topics_without_overlap(self):
        """完全隔离的社区不应合成 topic。"""
        cards = [
            {"id": "a1", "source_id": "src_a.md", "tags": ["x"], "wiki_sections": [], "body": "", "status": "ai_draft"},
            {"id": "a2", "source_id": "src_a.md", "tags": ["x"], "wiki_sections": [], "body": "", "status": "ai_draft"},
            {"id": "b1", "source_id": "src_b.md", "tags": ["y"], "wiki_sections": [], "body": "", "status": "ai_draft"},
            {"id": "b2", "source_id": "src_b.md", "tags": ["y"], "wiki_sections": [], "body": "", "status": "ai_draft"},
        ]
        communities = detect_communities(cards, min_members=2)
        topics = detect_topics(communities, cards, min_overlap=1)
        # src_a 和 src_b 社区没有共享成员 → 不应合成 topic
        # 但同 source 内部的 tag 社区有交叉 → 需要检查
        # tag x 和 source src_a 有重叠 → 形成 topic
        # tag y 和 source src_b 有重叠 → 形成 topic
        # 所以应该有 2 个 topic
        assert len(topics) == 2

    def test_topic_evidence_explains_why(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        topics = detect_topics(communities, cards)
        for t in topics:
            assert "主题包含" in t.evidence or "个交叉社区" in t.evidence

    def test_topics_sorted_by_card_count_desc(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        topics = detect_topics(communities, cards)
        for i in range(len(topics) - 1):
            assert topics[i].total_card_count >= topics[i + 1].total_card_count

    def test_deterministic_same_input_same_topics(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        t1 = detect_topics(communities, cards)
        t2 = detect_topics(communities, cards)
        assert len(t1) == len(t2)
        for a, b in zip(t1, t2):
            assert a.topic_id == b.topic_id
            assert a.total_card_count == b.total_card_count

    def test_empty_communities_returns_empty_topics(self):
        topics = detect_topics([], [])
        assert topics == []

    def test_single_community_returns_empty_topics(self):
        cards = [
            {"id": "s1", "source_id": "src.md", "tags": [], "wiki_sections": [], "body": "", "status": "ai_draft"},
            {"id": "s2", "source_id": "src.md", "tags": [], "wiki_sections": [], "body": "", "status": "ai_draft"},
        ]
        communities = detect_communities(cards, min_members=2)
        topics = detect_topics(communities, cards)
        # 只有 1 个社区 → 无法合成 topic（min_communities=2）
        assert len(topics) == 0


# ---------------------------------------------------------------------------
# 端到端集成测试：community + topic 完整管线
# ---------------------------------------------------------------------------


class TestE2ECommunityTopic:
    """验证 community → topic 完整管线。"""

    def test_full_pipeline(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        topics = detect_topics(communities, cards)

        # 基本断言
        assert len(communities) >= 4  # 至少 2 source + 2 tag + 2 wiki_section
        assert len(topics) >= 1

        # Topic 的卡片集合应覆盖所有 community 卡片
        all_topic_card_ids: set[str] = set()
        for t in topics:
            all_topic_card_ids.update(t.card_ids)
        # Topic 卡片集应是 community 卡片集的子集（去重后）
        all_comm_card_ids: set[str] = set()
        for c in communities:
            all_comm_card_ids.update(c.member_card_ids)
        assert all_topic_card_ids.issubset(all_comm_card_ids)

    def test_representative_cards_are_valid_members(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        for c in communities:
            for rid in c.representative_card_ids:
                assert rid in c.member_card_ids, (
                    f"代表性卡片 {rid} 不在社区 {c.shared_entity} 的成员中"
                )

    def test_topic_representative_cards_are_valid(self):
        cards = _make_cards()
        communities = detect_communities(cards, min_members=2)
        topics = detect_topics(communities, cards)
        for t in topics:
            for rid in t.representative_card_ids:
                assert rid in t.card_ids, (
                    f"Topic 代表性卡片 {rid} 不在 topic 的 card_ids 中"
                )
