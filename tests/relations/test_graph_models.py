"""v0.6 Graph Models unit tests — 图数据结构验证。"""

import pytest

from mindforge.relations.graph_models import (
    EdgeType,
    Graph,
    GraphEdge,
    GraphNode,
    NodeType,
    RelationEvidence,
)


class TestRelationEvidence:
    """RelationEvidence 必须可解释，不可有黑盒相似度。"""

    def test_evidence_has_reason_and_evidence_text(self):
        ev = RelationEvidence(
            reason="same_source_document",
            evidence="source: reading-notes/ai-ml.md",
            strength=0.8,
        )
        assert ev.reason == "same_source_document"
        assert ev.evidence == "source: reading-notes/ai-ml.md"
        assert ev.strength == 0.8
        assert ev.detail == {}

    def test_evidence_with_detail(self):
        ev = RelationEvidence(
            reason="shared_tag",
            evidence="tag: llm",
            strength=0.5,
            detail={"tag": "llm", "shared_count": 3},
        )
        assert ev.detail["tag"] == "llm"
        assert ev.detail["shared_count"] == 3

    def test_evidence_is_frozen(self):
        ev = RelationEvidence(reason="test", evidence="test", strength=1.0)
        with pytest.raises(Exception):
            ev.strength = 0.5  # type: ignore[misc]


class TestGraphNode:
    def test_card_node(self):
        node = GraphNode(
            id="card_1",
            type=NodeType.CARD,
            label="Test Card",
            href="/library?card=card_1",
        )
        assert node.id == "card_1"
        assert node.type == NodeType.CARD
        assert node.label == "Test Card"
        assert node.href == "/library?card=card_1"

    def test_source_node_with_card_count(self):
        node = GraphNode(
            id="src_1",
            type=NodeType.SOURCE,
            label="reading-notes/ai.md",
            card_count=5,
        )
        assert node.card_count == 5

    def test_tag_node(self):
        node = GraphNode(
            id="llm",
            type=NodeType.TAG,
            label="#llm",
            card_count=3,
        )
        assert node.type == NodeType.TAG
        assert node.label == "#llm"

    def test_node_is_frozen(self):
        node = GraphNode(id="n1", type=NodeType.CARD, label="test")
        with pytest.raises(Exception):
            node.label = "changed"  # type: ignore[misc]


class TestGraphEdge:
    def test_edge_carries_evidence(self):
        evidence = RelationEvidence(
            reason="same_source_document",
            evidence="same source: src_1",
            strength=0.8,
        )
        edge = GraphEdge(
            source_id="card_1",
            target_id="card_2",
            edge_type=EdgeType.RELATED_BY_SOURCE,
            evidence=evidence,
        )
        assert edge.source_id == "card_1"
        assert edge.target_id == "card_2"
        assert edge.edge_type == EdgeType.RELATED_BY_SOURCE
        assert edge.evidence.reason == "same_source_document"

    def test_edge_is_frozen(self):
        ev = RelationEvidence(reason="t", evidence="t", strength=0.5)
        edge = GraphEdge(
            source_id="a", target_id="b",
            edge_type=EdgeType.SHARES_TAG,
            evidence=ev,
        )
        with pytest.raises(Exception):
            edge.edge_type = EdgeType.LINKS_TO  # type: ignore[misc]


class TestGraph:
    def test_graph_construction(self):
        nodes = (
            GraphNode(id="c1", type=NodeType.CARD, label="Center"),
            GraphNode(id="c2", type=NodeType.CARD, label="Neighbor"),
        )
        ev = RelationEvidence(reason="test", evidence="test edge", strength=0.5)
        edges = (
            GraphEdge(
                source_id="c1", target_id="c2",
                edge_type=EdgeType.RELATED_BY_SOURCE,
                evidence=ev,
            ),
        )
        graph = Graph(
            center_id="c1",
            center_type=NodeType.CARD,
            depth=1,
            nodes=nodes,
            edges=edges,
        )
        assert graph.center_id == "c1"
        assert graph.depth == 1
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    def test_graph_with_depth_2(self):
        graph = Graph(
            center_id="c1",
            center_type=NodeType.CARD,
            depth=2,
            nodes=(),
            edges=(),
        )
        assert graph.depth == 2

    def test_graph_is_frozen(self):
        graph = Graph(
            center_id="c1",
            center_type=NodeType.CARD,
            depth=1,
            nodes=(),
            edges=(),
        )
        with pytest.raises(Exception):
            graph.depth = 3  # type: ignore[misc]
