"""M6 Local Graph unit tests — SDD §10, TDD §7。"""

import pytest

from mindforge.relations.local_graph import (
    GraphNode,
    GraphEdge,
    NodeType,
    LocalGraph,
    build_card_centered_graph,
)

from tests.fixtures.graph_golden import (
    SyntheticGraphCard,
    build_graph_golden,
)


def _card_dict(card: SyntheticGraphCard) -> dict[str, object]:
    return {
        "id": card.id,
        "source_id": card.source_id,
        "tags": list(card.tags),
        "wiki_sections": list(card.wiki_sections),
    }


class TestLocalGraph:
    def test_card_centered_graph_has_1_hop_neighbors(self):
        cards = [
            SyntheticGraphCard(id="center", source_id="src_1", tags=("x",)),
            SyntheticGraphCard(id="n1", source_id="src_1"),
        ]
        graph = build_card_centered_graph("center", [_card_dict(c) for c in cards])
        neighbor_ids = {n.id for n in graph.nodes if n.type == NodeType.CARD}
        assert "n1" in neighbor_ids

    def test_graph_nodes_have_correct_types(self):
        cards = [
            SyntheticGraphCard(id="c1", source_id="src_1", tags=("t1",), wiki_sections=("s1",)),
        ]
        graph = build_card_centered_graph("c1", [_card_dict(c) for c in cards])
        node_types = {n.type for n in graph.nodes}
        assert NodeType.CARD in node_types
        assert NodeType.SOURCE in node_types
        assert NodeType.TAG in node_types
        assert NodeType.WIKI_SECTION in node_types

    def test_graph_edges_have_correct_reasons(self):
        cards = [
            SyntheticGraphCard(id="center", source_id="src_1", tags=("auth",)),
            SyntheticGraphCard(id="n1", source_id="src_1"),
        ]
        graph = build_card_centered_graph("center", [_card_dict(c) for c in cards])
        assert len(graph.edges) > 0
        for edge in graph.edges:
            assert edge.reason in (
                "same_source", "same_tag", "same_wiki_section",
            )

    def test_center_card_is_always_in_graph(self):
        cards = [SyntheticGraphCard(id="center")]
        graph = build_card_centered_graph("center", [_card_dict(c) for c in cards])
        center_nodes = [n for n in graph.nodes if n.id == "center"]
        assert len(center_nodes) == 1

    def test_unrelated_cards_not_in_graph(self):
        cards = [
            SyntheticGraphCard(id="center", source_id="src_1"),
            SyntheticGraphCard(id="unrelated", source_id="src_99"),
        ]
        graph = build_card_centered_graph("center", [_card_dict(c) for c in cards])
        unrelated = [n for n in graph.nodes if n.id == "unrelated"]
        assert len(unrelated) == 0

    def test_node_href_enables_navigation(self):
        cards = [
            SyntheticGraphCard(id="center", source_id="src_1"),
            SyntheticGraphCard(id="n1", source_id="src_1"),
        ]
        graph = build_card_centered_graph("center", [_card_dict(c) for c in cards])
        for node in graph.nodes:
            if node.type == NodeType.CARD:
                assert node.href is not None
                assert "card" in node.href.lower()

    def test_graph_computation_under_1s(self):
        import time
        cards = [
            SyntheticGraphCard(
                id=f"c{i}",
                source_id=f"src_{i % 10}",
                tags=(f"tag_{i % 10}",),
                wiki_sections=(f"section_{i % 5}",),
            )
            for i in range(100)
        ]
        records = [_card_dict(c) for c in cards]
        start = time.perf_counter()
        graph = build_card_centered_graph("c0", records)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Graph computation took {elapsed:.3f}s"
        assert len(graph.nodes) > 0

    # ── Golden fixture ──

    def test_golden_graph_expected_nodes(self):
        golden = build_graph_golden()
        graph = build_card_centered_graph(
            golden.center_id,
            [_card_dict(c) for c in golden.cards],
        )
        node_ids = {n.id for n in graph.nodes}
        for expected_id in golden.expected_nodes:
            assert expected_id in node_ids, f"Expected node '{expected_id}' in graph"

    def test_golden_graph_has_edges(self):
        golden = build_graph_golden()
        graph = build_card_centered_graph(
            golden.center_id,
            [_card_dict(c) for c in golden.cards],
        )
        assert len(graph.edges) >= golden.expected_edge_count_min


class TestLocalGraphModels:
    def test_graph_is_immutable(self):
        graph = LocalGraph(
            center_id="c1",
            center_type=NodeType.CARD,
            nodes=(),
            edges=(),
        )
        with pytest.raises(Exception):
            graph.nodes = ()  # type: ignore[misc]

    def test_graph_node_is_immutable(self):
        node = GraphNode(id="c1", type=NodeType.CARD, label="Card 1")
        with pytest.raises(Exception):
            node.label = "Changed"  # type: ignore[misc]

    def test_graph_edge_is_immutable(self):
        edge = GraphEdge(
            source_id="c1",
            target_id="src_1",
            reason="same_source",
        )
        with pytest.raises(Exception):
            edge.reason = "other"  # type: ignore[misc]
