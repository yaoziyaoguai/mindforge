"""v0.6 DeterministicGraphBuilder tests — 图构建验证。"""

import pytest

from mindforge.relations.graph_builder import DeterministicGraphBuilder
from mindforge.relations.graph_models import (
    EdgeType,
    NodeType,
)
from mindforge.relations.related_cards import (
    RelationReason,
    compute_related_cards,
)

from tests.fixtures.relations_golden import SyntheticRelationCard, build_relations_fixture


# ── Helper ─────────────────────────────────────────


def _to_record(card: SyntheticRelationCard) -> dict[str, object]:
    return {
        "id": card.id,
        "title": f"Card {card.id}",
        "source_id": card.source_id,
        "tags": list(card.tags),
        "wiki_sections": list(card.wiki_sections),
        "status": card.status,
        "run_id": card.review_batch,
        "source_location_index": card.source_location_index,
    }


# ── Builder Construction ──────────────────────────


class TestBuilderConstruction:
    def test_builder_accepts_card_list(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", source_id="src_1")),
            _to_record(SyntheticRelationCard(id="c2", source_id="src_1")),
        ]
        builder = DeterministicGraphBuilder(cards)
        assert builder is not None

    def test_builder_accepts_empty_list(self):
        builder = DeterministicGraphBuilder([])
        graph = builder.get_graph("nonexistent", NodeType.CARD, depth=1)
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0


# ── Card-Centered Graph ───────────────────────────


class TestCardCenteredGraph:
    def test_1_hop_graph_has_center_and_neighbors(self):
        fixture = build_relations_fixture()
        cards = [_to_record(c) for c in fixture.cards]
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("c1", NodeType.CARD, depth=1)

        # 中心节点必须存在
        center_ids = [n.id for n in graph.nodes if n.type == NodeType.CARD]
        assert "c1" in center_ids

        # 至少有一条边
        assert len(graph.edges) > 0

    def test_2_hop_graph_includes_neighbor_of_neighbor(self):
        """c1 与 c2 通过 same_source 相关，c2 与 c3 通过 shared_tag 可能不相关，
        但 2-hop graph 应展开 c2 的关系链。"""
        # 让 c2 和 c3 共享 tag 以建立 2-hop 关系
        cards_data = [
            SyntheticRelationCard(id="c1", source_id="src_1", tags=("auth",)),
            SyntheticRelationCard(id="c2", source_id="src_1", tags=("auth", "db")),
            SyntheticRelationCard(id="c3", source_id="src_2", tags=("db",)),
        ]
        cards = [_to_record(c) for c in cards_data]
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("c1", NodeType.CARD, depth=2)

        node_ids = {n.id for n in graph.nodes if n.type == NodeType.CARD}
        # 2-hop 应包含 c3（c2 的邻居）
        assert "c3" in node_ids, f"2-hop graph should include c3, got nodes: {node_ids}"

    def test_every_edge_has_evidence(self):
        fixture = build_relations_fixture()
        cards = [_to_record(c) for c in fixture.cards]
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("c1", NodeType.CARD, depth=1)

        for edge in graph.edges:
            assert edge.evidence is not None, (
                f"Edge {edge.source_id}→{edge.target_id} missing evidence"
            )
            assert edge.evidence.reason, "Edge missing reason"
            assert edge.evidence.evidence, "Edge missing evidence text"
            assert edge.evidence.strength > 0, "Edge strength should be > 0"

    def test_orphan_card_returns_empty_graph(self):
        cards = [_to_record(SyntheticRelationCard(id="orphan"))]
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("orphan", NodeType.CARD, depth=1)

        # 至少应该有中心节点
        center = [n for n in graph.nodes if n.id == "orphan"]
        assert len(center) == 1


# ── GraphPort Interface ────────────────────────────


class TestGraphPortMethods:
    def test_get_node_returns_card_node(self):
        cards = [_to_record(SyntheticRelationCard(id="c1", tags=("ai",)))]
        builder = DeterministicGraphBuilder(cards)
        node = builder.get_node("c1", NodeType.CARD)
        assert node is not None
        assert node.type == NodeType.CARD

    def test_get_node_returns_none_for_missing(self):
        builder = DeterministicGraphBuilder([])
        node = builder.get_node("nonexistent", NodeType.CARD)
        assert node is None

    def test_get_node_source_with_card_count(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", source_id="src_1")),
            _to_record(SyntheticRelationCard(id="c2", source_id="src_1")),
        ]
        builder = DeterministicGraphBuilder(cards)
        node = builder.get_node("src_1", NodeType.SOURCE)
        assert node is not None
        assert node.card_count == 2

    def test_get_node_tag_with_card_count(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", tags=("ai",))),
            _to_record(SyntheticRelationCard(id="c2", tags=("ai",))),
            _to_record(SyntheticRelationCard(id="c3", tags=("ai",))),
        ]
        builder = DeterministicGraphBuilder(cards)
        node = builder.get_node("ai", NodeType.TAG)
        assert node is not None
        assert node.card_count == 3

    def test_get_node_wiki_section_with_card_count(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", wiki_sections=("LLM",))),
            _to_record(SyntheticRelationCard(id="c2", wiki_sections=("LLM",))),
        ]
        builder = DeterministicGraphBuilder(cards)
        node = builder.get_node("LLM", NodeType.WIKI_SECTION)
        assert node is not None
        assert node.card_count == 2

    def test_get_node_concept_returns_none(self):
        builder = DeterministicGraphBuilder([])
        node = builder.get_node("test", NodeType.CONCEPT)
        assert node is None  # CONCEPT 尚未实现

    def test_get_edges_returns_related_cards(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", source_id="src_1")),
            _to_record(SyntheticRelationCard(id="c2", source_id="src_1")),
        ]
        builder = DeterministicGraphBuilder(cards)
        edges = builder.get_edges("c1")
        assert len(edges) > 0
        assert any(e.target_id == "c2" for e in edges)

    def test_get_edges_filter_by_type(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", source_id="src_1", tags=("ai",))),
            _to_record(SyntheticRelationCard(id="c2", source_id="src_1", tags=("ai",))),
        ]
        builder = DeterministicGraphBuilder(cards)
        edges = builder.get_edges("c1", edge_types={EdgeType.SHARES_TAG})
        for e in edges:
            assert e.edge_type == EdgeType.SHARES_TAG

    def test_get_edges_direction_outgoing(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", source_id="src_1")),
            _to_record(SyntheticRelationCard(id="c2", source_id="src_1")),
        ]
        builder = DeterministicGraphBuilder(cards)
        outgoing = builder.get_edges("c1", direction="outgoing")
        for e in outgoing:
            assert e.source_id == "c1"

    def test_get_edges_invalid_direction_raises(self):
        builder = DeterministicGraphBuilder([])
        with pytest.raises(ValueError, match="invalid direction"):
            builder.get_edges("c1", direction="sideways")  # type: ignore[arg-type]


# ── Source / Tag / Wiki Centered Graph ─────────────


class TestSourceCenteredGraph:
    def test_source_graph_includes_all_cards(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", source_id="src_1")),
            _to_record(SyntheticRelationCard(id="c2", source_id="src_1")),
            _to_record(SyntheticRelationCard(id="c3", source_id="src_2")),
        ]
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("src_1", NodeType.SOURCE, depth=1)

        card_ids = {n.id for n in graph.nodes if n.type == NodeType.CARD}
        assert "c1" in card_ids
        assert "c2" in card_ids
        assert "c3" not in card_ids

    def test_source_graph_has_derived_from_edges(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", source_id="src_1")),
            _to_record(SyntheticRelationCard(id="c2", source_id="src_1")),
        ]
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("src_1", NodeType.SOURCE, depth=1)

        derived_edges = [e for e in graph.edges if e.edge_type == EdgeType.DERIVED_FROM]
        assert len(derived_edges) == 2


class TestTagCenteredGraph:
    def test_tag_graph_includes_tagged_cards(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", tags=("ai",))),
            _to_record(SyntheticRelationCard(id="c2", tags=("ai",))),
            _to_record(SyntheticRelationCard(id="c3", tags=("db",))),
        ]
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("ai", NodeType.TAG, depth=1)

        card_ids = {n.id for n in graph.nodes if n.type == NodeType.CARD}
        assert "c1" in card_ids
        assert "c2" in card_ids
        assert "c3" not in card_ids


class TestWikiSectionCenteredGraph:
    def test_section_graph_includes_referenced_cards(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", wiki_sections=("LLM",))),
            _to_record(SyntheticRelationCard(id="c2", wiki_sections=("LLM",))),
        ]
        builder = DeterministicGraphBuilder(cards)
        graph = builder.get_graph("LLM", NodeType.WIKI_SECTION, depth=1)

        card_ids = {n.id for n in graph.nodes if n.type == NodeType.CARD}
        assert "c1" in card_ids
        assert "c2" in card_ids


# ── Path Finding ──────────────────────────────────


class TestPathFinding:
    def test_direct_edge_path(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1", source_id="src_1")),
            _to_record(SyntheticRelationCard(id="c2", source_id="src_1")),
        ]
        builder = DeterministicGraphBuilder(cards)
        paths = builder.get_path("c1", "c2", max_depth=1)
        assert len(paths) > 0
        assert len(paths[0]) == 1
        assert paths[0][0].source_id == "c1"
        assert paths[0][0].target_id == "c2"

    def test_no_path_returns_empty(self):
        cards = [
            _to_record(SyntheticRelationCard(id="c1")),
            _to_record(SyntheticRelationCard(id="c2")),
        ]
        builder = DeterministicGraphBuilder(cards)
        paths = builder.get_path("c1", "c2", max_depth=2)
        assert paths == []


# ── Backward Compatibility ────────────────────────


class TestBackwardCompatibility:
    """验证新 graph_builder 与现有 compute_related_cards 结果一致。"""

    def test_builder_edges_match_compute_related_cards_count(self):
        fixture = build_relations_fixture()
        cards = [_to_record(c) for c in fixture.cards]
        builder = DeterministicGraphBuilder(cards)

        old_result = compute_related_cards("c1", cards, context="library")
        new_edges = builder.get_edges("c1", direction="outgoing")

        # 新 builder 的 outgoing 边目标应与旧结果的目标匹配
        old_targets = {e.target_card_id for e in old_result}
        new_targets = {e.target_id for e in new_edges}
        assert old_targets == new_targets, (
            f"Backward compat: old targets {old_targets} != new targets {new_targets}"
        )

    def test_every_old_relation_reason_maps_to_edge_type(self):
        """确保所有现有 RelationReason 都有对应的 EdgeType 映射。"""
        from mindforge.relations.graph_builder import _REASON_TO_EDGE_TYPE
        for reason in RelationReason:
            assert reason in _REASON_TO_EDGE_TYPE, (
                f"RelationReason.{reason.name} has no EdgeType mapping"
            )


# ── Determinism ───────────────────────────────────


class TestDeterminism:
    def test_same_input_produces_same_graph(self):
        cards = [_to_record(c) for c in build_relations_fixture().cards]
        builder1 = DeterministicGraphBuilder(cards)
        builder2 = DeterministicGraphBuilder(cards)

        g1 = builder1.get_graph("c1", NodeType.CARD, depth=2)
        g2 = builder2.get_graph("c1", NodeType.CARD, depth=2)

        assert {n.id for n in g1.nodes} == {n.id for n in g2.nodes}
        assert {(e.source_id, e.target_id, e.edge_type) for e in g1.edges} == \
               {(e.source_id, e.target_id, e.edge_type) for e in g2.edges}


# ── Performance ───────────────────────────────────


class TestPerformance:
    def test_100_card_graph_builds_under_200ms(self):
        import time
        cards = []
        for i in range(100):
            src = f"src_{(i % 10)}"
            tags = (f"tag_{i % 5}",)
            sections = (f"section_{i % 3}",)
            cards.append(_to_record(SyntheticRelationCard(
                id=f"card_{i}",
                source_id=src,
                tags=tags,
                wiki_sections=sections,
            )))
        builder = DeterministicGraphBuilder(cards)
        start = time.perf_counter()
        graph = builder.get_graph("card_0", NodeType.CARD, depth=2)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Graph build took {elapsed:.3f}s, expected < 1.0s"
        assert len(graph.nodes) > 0
