"""v1.2 Knowledge Community — 确定性社区检测测试。"""

from mindforge.relations.community import KnowledgeCommunity, detect_communities


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
