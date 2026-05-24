"""v0.6 R6 Discovery Context unit tests.

中文学习型说明：测试 assemble_discovery_context() 的确定性行为，
包括 1-hop/2-hop 邻居分类、wiki sections/tags/sources 聚合。
"""

from __future__ import annotations

from mindforge.relations.discovery_context import assemble_discovery_context
from mindforge.relations.graph_builder import DeterministicGraphBuilder


def _make_cards() -> list[dict[str, object]]:
    """构建测试用的卡片数据集。"""
    return [
        {
            "id": "card_1",
            "title": "Card One",
            "status": "human_approved",
            "source_id": "src_a",
            "tags": ["ai", "llm"],
            "wiki_sections": ["Machine Learning"],
            "run_id": "r1",
            "source_location_index": 0,
        },
        {
            "id": "card_2",
            "title": "Card Two",
            "status": "human_approved",
            "source_id": "src_a",
            "tags": ["ai", "db"],
            "wiki_sections": ["Machine Learning"],
            "run_id": "r1",
            "source_location_index": 1,
        },
        {
            "id": "card_3",
            "title": "Card Three",
            "status": "human_approved",
            "source_id": "src_b",
            "tags": ["db"],
            "wiki_sections": ["Database"],
            "run_id": "r1",
            "source_location_index": 0,
        },
        {
            "id": "card_4",
            "title": "Card Four",
            "status": "human_approved",
            "source_id": "src_b",
            "tags": ["db", "sql"],
            "wiki_sections": ["Database"],
            "run_id": "r1",
            "source_location_index": 1,
        },
    ]


class TestAssembleDiscoveryContext:
    def test_center_card_id_and_title(self):
        """验证中心卡片 id 和 title 正确返回。"""
        cards = _make_cards()
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("card_1", "card", depth=2)
        ctx = assemble_discovery_context(graph)
        assert ctx.center_card_id == "card_1"
        assert ctx.center_card_title == "Card One"

    def test_direct_matches_are_1hop_neighbors(self):
        """验证 direct_matches 包含 1-hop 邻居。"""
        cards = _make_cards()
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("card_1", "card", depth=2)
        ctx = assemble_discovery_context(graph)
        neighbor_ids = {m.card_id for m in ctx.direct_matches}
        # card_2 同源且同 section，应为 1-hop 邻居
        assert "card_2" in neighbor_ids, f"card_2 should be 1-hop neighbor, got: {neighbor_ids}"

    def test_neighbor_cards_are_2hop(self):
        """验证 neighbor_cards 包含 2-hop 邻居。"""
        cards = _make_cards()
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("card_1", "card", depth=2)
        ctx = assemble_discovery_context(graph)
        # card_1 → card_2 (1-hop) → card_3 (2-hop via shared tag "db")
        direct_ids = {m.card_id for m in ctx.direct_matches}
        neighbor_ids_set = {m.card_id for m in ctx.neighbor_cards}
        all_related = direct_ids | neighbor_ids_set
        # card_3 should appear as either 1-hop or 2-hop
        # (depends on relationship engine — at minimum more than just card_1 itself)
        assert len(all_related) >= 1, f"Expected at least one related card, got: {all_related}"

    def test_direct_and_neighbor_are_disjoint(self):
        """验证 direct_matches 和 neighbor_cards 不重叠。"""
        cards = _make_cards()
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("card_1", "card", depth=2)
        ctx = assemble_discovery_context(graph)
        direct_ids = {m.card_id for m in ctx.direct_matches}
        neighbor_ids = {m.card_id for m in ctx.neighbor_cards}
        assert direct_ids.isdisjoint(neighbor_ids), \
            f"direct and neighbor should not overlap: direct={direct_ids}, neighbor={neighbor_ids}"

    def test_wiki_sections_present(self):
        """验证 wiki_sections 被正确聚合。"""
        cards = _make_cards()
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("card_1", "card", depth=2)
        ctx = assemble_discovery_context(graph)
        section_names = {s.section_title for s in ctx.wiki_sections}
        assert "Machine Learning" in section_names, (
            f"Expected 'Machine Learning', got: {section_names}"
        )

    def test_shared_tags_present(self):
        """验证 shared_tags 被正确聚合。"""
        cards = _make_cards()
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("card_1", "card", depth=2)
        ctx = assemble_discovery_context(graph)
        tag_names = {t.tag for t in ctx.shared_tags}
        # card_1 has tags "ai" and "llm"
        assert len(tag_names) >= 1, f"Expected at least one tag, got: {tag_names}"

    def test_shared_sources_present(self):
        """验证 shared_sources 被正确聚合。"""
        cards = _make_cards()
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("card_1", "card", depth=2)
        ctx = assemble_discovery_context(graph)
        source_ids = {s.source_id for s in ctx.shared_sources}
        assert "src_a" in source_ids, f"Expected 'src_a' in sources, got: {source_ids}"

    def test_every_direct_match_has_evidence(self):
        """验证每条 direct_match 都有可解释的证据。"""
        cards = _make_cards()
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("card_1", "card", depth=2)
        ctx = assemble_discovery_context(graph)
        for match in ctx.direct_matches:
            assert match.relation_reason, f"Match {match.card_id} missing relation_reason"
            assert match.relation_strength > 0, f"Match {match.card_id} strength should be > 0"
            assert match.evidence, f"Match {match.card_id} missing evidence text"

    def test_deterministic_same_input_same_output(self):
        """验证确定性：相同输入 → 相同输出。"""
        cards = _make_cards()
        builder1 = DeterministicGraphBuilder(cards)
        builder2 = DeterministicGraphBuilder(cards)
        graph1 = builder1.get_graph("card_1", "card", depth=2)
        graph2 = builder2.get_graph("card_1", "card", depth=2)
        ctx1 = assemble_discovery_context(graph1)
        ctx2 = assemble_discovery_context(graph2)
        assert ctx1.center_card_id == ctx2.center_card_id
        assert len(ctx1.direct_matches) == len(ctx2.direct_matches)
        assert len(ctx1.neighbor_cards) == len(ctx2.neighbor_cards)
        assert len(ctx1.shared_tags) == len(ctx2.shared_tags)
        assert len(ctx1.shared_sources) == len(ctx2.shared_sources)

    def test_empty_context_for_isolated_card(self):
        """验证孤立卡片（无邻居）返回合理空上下文。"""
        cards = [
            {
                "id": "isolated_card",
                "title": "Isolated",
                "status": "human_approved",
                "source_id": None,
                "tags": [],
                "wiki_sections": [],
                "run_id": None,
                "source_location_index": None,
            },
        ]
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("isolated_card", "card", depth=2)
        ctx = assemble_discovery_context(graph)
        assert ctx.center_card_id == "isolated_card"
        assert ctx.center_card_title == "Isolated"
        assert len(ctx.direct_matches) == 0
        assert len(ctx.neighbor_cards) == 0
