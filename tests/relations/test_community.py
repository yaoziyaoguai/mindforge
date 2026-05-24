"""v1.2 Knowledge Community — 确定性社区检测测试。"""

from mindforge.relations.community import (
    CommunityOverlap,
    KnowledgeCommunity,
    SubCommunityRef,
    detect_communities,
)


def _card(id: str, source_id: str | None = None, tags: list[str] | None = None, wiki_sections: list[str] | None = None) -> dict[str, object]:
    return {"id": id, "source_id": source_id, "tags": tags or [], "wiki_sections": wiki_sections or []}


class TestDetectCommunities:
    def test_source_community_detected(self):
        cards = [
            _card("c1", source_id="src/doc.md"),
            _card("c2", source_id="src/doc.md"),
        ]
        communities = detect_communities(cards)
        assert len(communities) == 1
        assert communities[0].community_type == "source"
        assert communities[0].shared_entity == "src/doc.md"
        assert communities[0].member_count == 2

    def test_tag_community_detected(self):
        cards = [
            _card("c1", tags=["ai"]),
            _card("c2", tags=["ai"]),
            _card("c3", tags=["ai"]),
        ]
        communities = detect_communities(cards)
        assert len(communities) == 1
        assert communities[0].community_type == "tag"
        assert communities[0].shared_entity == "#ai"
        assert communities[0].member_count == 3

    def test_wiki_section_community_detected(self):
        cards = [
            _card("c1", wiki_sections=["Intro"]),
            _card("c2", wiki_sections=["Intro"]),
        ]
        communities = detect_communities(cards)
        assert len(communities) == 1
        assert communities[0].community_type == "wiki_section"
        assert communities[0].shared_entity == "Intro"

    def test_min_members_threshold(self):
        cards = [
            _card("c1", source_id="src/a.md"),
        ]
        communities = detect_communities(cards, min_members=2)
        assert len(communities) == 0  # 只有 1 张卡片，不形成社区

    def test_multiple_community_types(self):
        cards = [
            _card("c1", source_id="src/a.md", tags=["ai"], wiki_sections=["Intro"]),
            _card("c2", source_id="src/a.md", tags=["ai"], wiki_sections=["Intro"]),
        ]
        communities = detect_communities(cards)
        # source community + tag community + wiki section community
        types = {c.community_type for c in communities}
        assert types == {"source", "tag", "wiki_section"}

    def test_sorted_by_member_count_desc(self):
        cards = [
            _card("c1", tags=["ai"]),
            _card("c2", tags=["ai"]),
            _card("c3", tags=["ai"]),
            _card("c4", tags=["ml"]),
            _card("c5", tags=["ml"]),
        ]
        communities = detect_communities(cards)
        counts = [c.member_count for c in communities]
        assert counts == sorted(counts, reverse=True)

    def test_description_is_deterministic(self):
        cards = [
            _card("c1", source_id="src/doc.md"),
            _card("c2", source_id="src/doc.md"),
        ]
        c1 = detect_communities(cards)
        c2 = detect_communities(cards)
        assert c1[0].description == c2[0].description

    def test_member_ids_present(self):
        cards = [
            _card("c1", source_id="src/doc.md"),
            _card("c2", source_id="src/doc.md"),
        ]
        communities = detect_communities(cards)
        assert set(communities[0].member_card_ids) == {"c1", "c2"}


class TestKnowledgeCommunity:
    def test_immutable(self):
        import pytest
        c = KnowledgeCommunity(
            community_type="source",
            shared_entity="src/a.md",
            member_count=2,
            member_card_ids=("c1", "c2"),
            description="test",
        )
        with pytest.raises(Exception):
            c.member_count = 3  # type: ignore[misc]

    def test_v2_1_defaults(self):
        """v2.1 新字段默认值：向后兼容。"""
        c = KnowledgeCommunity(
            community_type="source",
            shared_entity="src/a.md",
            member_count=2,
            member_card_ids=("c1", "c2"),
            description="test",
        )
        assert c.sub_communities == ()
        assert c.overlap_with == ()
        assert c.quality_score == 0.0


class TestCardQuality:
    """v2.1 卡片质量评分测试。"""

    def test_empty_card_minimal_score(self):
        from mindforge.relations.community import _card_quality
        score = _card_quality({"id": "c1"})
        assert score == 0.0

    def test_source_provenance_adds_score(self):
        from mindforge.relations.community import _card_quality
        score = _card_quality({"id": "c1", "source_id": "src/doc.md"})
        assert score == 0.2

    def test_tags_add_score(self):
        from mindforge.relations.community import _card_quality
        score = _card_quality({"id": "c1", "tags": ["ai", "ml", "python"]})
        assert score == 0.3  # max 0.3 from tags

    def test_wiki_sections_add_score(self):
        from mindforge.relations.community import _card_quality
        score = _card_quality({"id": "c1", "wiki_sections": ["Intro", "Advanced"]})
        assert score == 0.2  # 2 sections × 0.1

    def test_long_body_adds_score(self):
        from mindforge.relations.community import _card_quality
        short = _card_quality({"id": "c1", "body": "hi"})
        long = _card_quality({"id": "c2", "body": "x" * 101})
        assert short == 0.0
        assert long >= 0.2  # body length bonus

    def test_approved_status_adds_score(self):
        from mindforge.relations.community import _card_quality
        score = _card_quality({"id": "c1", "status": "human_approved"})
        assert score == 0.2

    def test_max_score_capped_at_1(self):
        from mindforge.relations.community import _card_quality
        score = _card_quality({
            "id": "c1",
            "source_id": "src/doc.md",
            "tags": ["a", "b", "c", "d", "e"],
            "wiki_sections": ["x", "y", "z", "w"],
            "body": "x" * 200,
            "status": "human_approved",
        })
        assert 0.9 <= score <= 1.0


class TestV2_1Hierarchy:
    """v2.1 多层级社区分组测试。"""

    def test_tag_is_sub_community_of_source(self):
        """当 tag 社区成员是 source 社区成员的子集时，tag 是 source 的子社区。"""
        cards = [
            _card("c1", source_id="src/doc.md", tags=["ai"]),
            _card("c2", source_id="src/doc.md", tags=["ai"]),
            _card("c3", source_id="src/doc.md", tags=["ml"]),
        ]
        communities = detect_communities(cards, min_members=2)
        # source: src/doc.md (c1, c2, c3)
        # tag: #ai (c1, c2)
        # tag: #ml (c1 only — 不满足 min_members=2)

        source_comm = [c for c in communities if c.community_type == "source"][0]
        assert len(source_comm.sub_communities) >= 1
        sub_types = {s.community_type for s in source_comm.sub_communities}
        assert "tag" in sub_types

    def test_wiki_section_is_sub_of_tag(self):
        """当 wiki_section 社区成员是 tag 社区成员的子集时，wiki_section 是 tag 的子社区。"""
        cards = [
            _card("c1", tags=["ai"], wiki_sections=["Intro"]),
            _card("c2", tags=["ai"], wiki_sections=["Intro"]),
            _card("c3", tags=["ai"], wiki_sections=["Advanced"]),
        ]
        communities = detect_communities(cards, min_members=2)

        tag_comm = [c for c in communities if c.community_type == "tag" and c.shared_entity == "#ai"][0]
        assert len(tag_comm.sub_communities) >= 1
        sub_types = {s.community_type for s in tag_comm.sub_communities}
        assert "wiki_section" in sub_types

    def test_no_self_referential_sub_community(self):
        """同类型社区之间不构成父子关系。"""
        cards = [
            _card("c1", tags=["ai"]),
            _card("c2", tags=["ai"]),
        ]
        communities = detect_communities(cards, min_members=2)
        tag_comm = [c for c in communities if c.community_type == "tag"][0]
        # 没有同类型的子社区
        for sub in tag_comm.sub_communities:
            assert sub.community_type != "tag"


class TestV2_1Overlap:
    """v2.1 社区重叠检测测试。"""

    def test_overlap_between_source_and_tag(self):
        """如果 source 社区和 tag 社区共享成员，应检测到重叠。"""
        cards = [
            _card("c1", source_id="src/a.md", tags=["ai"]),
            _card("c2", source_id="src/a.md", tags=["ai"]),
            _card("c3", source_id="src/a.md", tags=["ml"]),
            _card("c4", source_id="src/b.md", tags=["ai"]),
        ]
        communities = detect_communities(cards, min_members=2)
        # source: src/a.md (c1,c2,c3), src/b.md (c4 only — 不满足 min)
        # tag: #ai (c1,c2,c4)

        tag_ai = [c for c in communities if c.shared_entity == "#ai"][0]
        assert len(tag_ai.overlap_with) >= 1
        overlap_types = {o.community_type for o in tag_ai.overlap_with}
        assert "source" in overlap_types

    def test_no_overlap_when_no_shared_members(self):
        """不同类型社区无共享成员时，不应有重叠。"""
        cards = [
            _card("c1", source_id="src/a.md", tags=["ai"]),
            _card("c2", source_id="src/a.md"),
            _card("c3", source_id="src/b.md", tags=["ml"]),
            _card("c4", source_id="src/b.md"),
        ]
        communities = detect_communities(cards, min_members=2)
        # source: src/a.md {c1,c2}, src/b.md {c3,c4}
        # tag: #ai {c1}, #ml {c3} — 都不满足 min

        source_comm = [c for c in communities if c.shared_entity == "src/a.md"][0]
        for overlap in source_comm.overlap_with:
            assert overlap.community_type != "tag"  # 无 tag 重叠

    def test_overlap_records_shared_member_ids(self):
        cards = [
            _card("c1", source_id="src/doc.md", tags=["ai"]),
            _card("c2", source_id="src/doc.md", tags=["ai"]),
        ]
        communities = detect_communities(cards, min_members=2)
        tag_ai = [c for c in communities if c.shared_entity == "#ai"][0]
        for overlap in tag_ai.overlap_with:
            assert overlap.shared_member_count >= 1
            assert len(overlap.shared_member_ids) == overlap.shared_member_count


class TestV2_1QualityScore:
    """v2.1 社区质量评分测试。"""

    def test_community_quality_is_average_of_members(self):
        cards = [
            {"id": "c1", "source_id": "src/doc.md", "tags": ["ai"], "status": "human_approved"},
            {"id": "c2", "source_id": "src/doc.md"},
        ]
        communities = detect_communities(cards, min_members=2)
        source_comm = [c for c in communities if c.community_type == "source"][0]
        # c1: source_id(0.2) + tags(0.1) + approved(0.2) = 0.5
        # c2: source_id(0.2) = 0.2
        # avg = (0.5 + 0.2) / 2 = 0.35
        assert 0.3 <= source_comm.quality_score <= 0.4

    def test_quality_score_range(self):
        cards = [
            _card("c1", source_id="src/a.md"),
            _card("c2", source_id="src/a.md"),
        ]
        communities = detect_communities(cards, min_members=2)
        for c in communities:
            assert 0.0 <= c.quality_score <= 1.0


class TestSubCommunityRef:
    def test_immutable(self):
        ref = SubCommunityRef(
            community_type="tag",
            shared_entity="#ai",
            member_count=3,
        )
        assert ref.community_type == "tag"
        assert ref.shared_entity == "#ai"
        assert ref.member_count == 3


class TestCommunityOverlap:
    def test_immutable(self):
        import pytest
        overlap = CommunityOverlap(
            community_type="source",
            shared_entity="src/doc.md",
            shared_member_count=2,
            shared_member_ids=("c1", "c2"),
        )
        assert overlap.shared_member_count == 2
        with pytest.raises(Exception):
            overlap.shared_member_count = 3  # type: ignore[misc]
