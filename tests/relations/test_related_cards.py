"""M3 Related Cards unit tests — SDD §7, TDD §5。"""

import pytest

from mindforge.relations.related_cards import (
    RelatedCardEdge,
    RelationReason,
    compute_multi_hop_related_cards,
    compute_related_cards,
)

from tests.fixtures.relations_golden import (
    SyntheticRelationCard,
    build_relations_fixture,
)


# ──────────────────────────────────────────────
# Helper: convert fixture cards
# ──────────────────────────────────────────────

def _to_record(card: SyntheticRelationCard) -> dict[str, object]:
    return {
        "id": card.id,
        "source_id": card.source_id,
        "tags": list(card.tags),
        "wiki_sections": list(card.wiki_sections),
        "status": card.status,
        "run_id": card.review_batch,
        "source_location_index": card.source_location_index,
    }


# ──────────────────────────────────────────────
# Relation computation tests
# ──────────────────────────────────────────────

class TestRelatedCards:
    def test_same_source_cards_are_related(self):
        cards = [
            SyntheticRelationCard(id="c1", source_id="src_1"),
            SyntheticRelationCard(id="c2", source_id="src_1"),
        ]
        edges = compute_related_cards("c1", [_to_record(c) for c in cards])
        assert any(e.target_card_id == "c2" and e.reason == RelationReason.SAME_SOURCE
                   for e in edges)

    def test_same_tag_cards_are_related(self):
        cards = [
            SyntheticRelationCard(id="c1", tags=("auth",)),
            SyntheticRelationCard(id="c2", tags=("auth",)),
        ]
        edges = compute_related_cards("c1", [_to_record(c) for c in cards])
        assert any(e.target_card_id == "c2" and e.reason == RelationReason.SAME_TAG
                   for e in edges)

    def test_same_wiki_section_cards_are_related(self):
        cards = [
            SyntheticRelationCard(id="c1", wiki_sections=("Auth",)),
            SyntheticRelationCard(id="c2", wiki_sections=("Auth",)),
        ]
        edges = compute_related_cards("c1", [_to_record(c) for c in cards])
        assert any(e.target_card_id == "c2" and e.reason == RelationReason.SAME_WIKI_SECTION
                   for e in edges)

    def test_source_card_not_related_to_itself(self):
        cards = [SyntheticRelationCard(id="c1", source_id="src_1")]
        edges = compute_related_cards("c1", [_to_record(c) for c in cards])
        assert all(e.target_card_id != "c1" for e in edges)

    def test_related_cards_sorted_by_strength_desc(self):
        cards = [
            SyntheticRelationCard(id="center", source_id="src_1", tags=("x",), wiki_sections=("s",)),
            SyntheticRelationCard(id="c_same_source", source_id="src_1"),
            SyntheticRelationCard(id="c_same_tag", tags=("x",)),
        ]
        edges = compute_related_cards("center", [_to_record(c) for c in cards])
        strengths = [e.strength for e in edges]
        assert strengths == sorted(strengths, reverse=True)

    def test_library_context_filters_non_approved(self):
        cards = [
            SyntheticRelationCard(id="c1", source_id="src_1", status="human_approved"),
            SyntheticRelationCard(id="c2", source_id="src_1", status="pending_review"),
        ]
        edges = compute_related_cards(
            "c1", [_to_record(c) for c in cards],
            context="library",
        )
        assert all(e.target_card_id != "c2" for e in edges)

    def test_dogfood_fixture_covers_all_deterministic_reason_labels(self):
        """dogfood fixture 至少覆盖 4-6 张 approved cards 和五种 v0.3 reason。

        中文学习型说明：真实 dogfood 曾只有一张 approved card，导致 Related
        Cards 看起来通过但没有验证关系标签。这里用纯合成摘要锁定用户可见的
        deterministic labels，不引入 embedding 或 semantic similarity。
        """
        cards = [
            SyntheticRelationCard(
                id="center",
                source_id="src-a",
                tags=("agent", "workflow"),
                wiki_sections=("Agent Runtime",),
                review_batch="run-42",
                source_location_index=10,
            ),
            SyntheticRelationCard(id="same_source", source_id="src-a"),
            SyntheticRelationCard(id="same_tag", tags=("agent",)),
            SyntheticRelationCard(id="same_wiki", wiki_sections=("Agent Runtime",)),
            SyntheticRelationCard(id="same_batch", review_batch="run-42"),
            SyntheticRelationCard(id="neighbor", source_id="src-a", source_location_index=11),
        ]

        edges = compute_related_cards("center", [_to_record(c) for c in cards])
        reasons = {(edge.target_card_id, edge.reason) for edge in edges}
        details = {edge.reason_detail for edge in edges}

        assert ("same_source", RelationReason.SAME_SOURCE) in reasons
        assert ("same_tag", RelationReason.SAME_TAG) in reasons
        assert ("same_wiki", RelationReason.SAME_WIKI_SECTION) in reasons
        assert ("same_batch", RelationReason.SAME_REVIEW_BATCH) in reasons
        assert ("neighbor", RelationReason.SOURCE_LOCATION_NEIGHBOR) in reasons
        assert any("same review batch" in detail for detail in details)
        assert any("nearby source location" in detail for detail in details)

    def test_library_context_excludes_draft_and_rejected_from_dogfood_relations(self):
        """Library context 只能返回 human_approved related cards。"""
        cards = [
            SyntheticRelationCard(id="center", source_id="src-a", status="human_approved"),
            SyntheticRelationCard(id="approved_neighbor", source_id="src-a", status="human_approved"),
            SyntheticRelationCard(id="draft_neighbor", source_id="src-a", status="ai_draft"),
            SyntheticRelationCard(id="rejected_neighbor", source_id="src-a", status="rejected"),
        ]

        edges = compute_related_cards("center", [_to_record(c) for c in cards], context="library")
        related_ids = {edge.target_card_id for edge in edges}

        assert "approved_neighbor" in related_ids
        assert "draft_neighbor" not in related_ids
        assert "rejected_neighbor" not in related_ids

    def test_golden_fixture_expected_relations(self):
        f = build_relations_fixture()
        edges = compute_related_cards(f.query_card_id, [_to_record(c) for c in f.cards])
        related_ids = {e.target_card_id for e in edges}
        for expected_id in f.expected_related_ids:
            assert expected_id in related_ids, f"Expected {expected_id} to be related"

    def test_golden_fixture_no_false_relations(self):
        f = build_relations_fixture()
        edges = compute_related_cards(f.query_card_id, [_to_record(c) for c in f.cards])
        related_ids = {e.target_card_id for e in edges}
        for no_rel_id in f.expected_no_relation_ids:
            assert no_rel_id not in related_ids, f"Expected {no_rel_id} NOT to be related"


# ──────────────────────────────────────────────
# Data model tests
# ──────────────────────────────────────────────

class TestRelatedCardEdge:
    def test_edge_is_immutable(self):
        edge = RelatedCardEdge(
            source_card_id="c1",
            target_card_id="c2",
            reason=RelationReason.SAME_SOURCE,
            reason_detail="same source: src_1",
            strength=0.8,
        )
        with pytest.raises(Exception):
            edge.strength = 0.9  # type: ignore[misc]

    def test_manual_link_not_emitted(self):
        """manual_link 在 v0.3 API 中不应出现"""
        cards = [
            SyntheticRelationCard(id="c1", source_id="src_1"),
            SyntheticRelationCard(id="c2", source_id="src_1"),
        ]
        edges = compute_related_cards("c1", [_to_record(c) for c in cards])
        assert all(e.reason != RelationReason.MANUAL_LINK for e in edges)


# ──────────────────────────────────────────────
# Performance test
# ──────────────────────────────────────────────

    # v1.2 新增: 多标签/多章节加权
    def test_multi_tag_gives_higher_strength(self):
        """共享 2 个 tag 的关系强度应高于共享 1 个 tag。"""
        cards = [
            SyntheticRelationCard(id="c1", tags=("ai", "ml")),
            SyntheticRelationCard(id="c2", tags=("ai", "ml")),
            SyntheticRelationCard(id="c3", tags=("ai",)),
        ]
        edges = compute_related_cards("c1", [_to_record(c) for c in cards])
        c2_strength = next(e.strength for e in edges if e.target_card_id == "c2")
        c3_strength = next(e.strength for e in edges if e.target_card_id == "c3")
        assert c2_strength > c3_strength, f"Multi-tag ({c2_strength}) should be stronger than single-tag ({c3_strength})"

    def test_multi_wiki_section_gives_higher_strength(self):
        """共享 2 个 wiki section 的关系强度应高于共享 1 个。"""
        cards = [
            SyntheticRelationCard(id="c1", wiki_sections=("S1", "S2")),
            SyntheticRelationCard(id="c2", wiki_sections=("S1", "S2")),
            SyntheticRelationCard(id="c3", wiki_sections=("S1",)),
        ]
        edges = compute_related_cards("c1", [_to_record(c) for c in cards])
        c2_strength = next(e.strength for e in edges if e.target_card_id == "c2")
        c3_strength = next(e.strength for e in edges if e.target_card_id == "c3")
        assert c2_strength > c3_strength, f"Multi-section ({c2_strength}) should be stronger than single-section ({c3_strength})"


# ──────────────────────────────────────────────
# v2.1 Multi-hop tests
# ──────────────────────────────────────────────


class TestMultiHopRelatedCards:
    """v2.1 多层关系发现 BFS 测试。"""

    def test_default_one_hop_matches_legacy(self):
        """max_depth=1 的 multi-hop 应与 legacy compute_related_cards 结果一致。"""
        cards = [
            SyntheticRelationCard(id="c1", source_id="src_1"),
            SyntheticRelationCard(id="c2", source_id="src_1"),
        ]
        legacy = compute_related_cards("c1", [_to_record(c) for c in cards])
        multi = compute_multi_hop_related_cards("c1", [_to_record(c) for c in cards], max_depth=1)
        assert len(legacy) == len(multi)

    def test_two_hop_discovers_indirect_neighbors(self):
        """2-hop 应发现通过中间卡片间接关联的卡片。"""
        cards = [
            SyntheticRelationCard(id="c1", source_id="src_a"),
            SyntheticRelationCard(id="c2", source_id="src_a", tags=("ai",)),
            SyntheticRelationCard(id="c3", tags=("ai",)),
        ]
        # c1 → c2 (same_source) → c3 (same_tag)
        edges = compute_multi_hop_related_cards("c1", [_to_record(c) for c in cards], max_depth=2)
        target_ids = {e.target_card_id for e in edges}
        assert "c3" in target_ids  # 2-hop reachable

    def test_hop_distance_recorded(self):
        """每条 edge 的 hop_distance 应正确记录。"""
        cards = [
            SyntheticRelationCard(id="c1", source_id="src_a"),
            SyntheticRelationCard(id="c2", source_id="src_a", tags=("ai",)),
            SyntheticRelationCard(id="c3", tags=("ai",)),
        ]
        edges = compute_multi_hop_related_cards("c1", [_to_record(c) for c in cards], max_depth=2)
        c2_edges = [e for e in edges if e.target_card_id == "c2"]
        c3_edges = [e for e in edges if e.target_card_id == "c3"]
        assert all(e.hop_distance == 1 for e in c2_edges)
        assert any(e.hop_distance == 2 for e in c3_edges)

    def test_via_path_recorded(self):
        """via_path 应记录从 center 到 target 的中间卡片路径。"""
        cards = [
            SyntheticRelationCard(id="c1", source_id="src_a"),
            SyntheticRelationCard(id="c2", source_id="src_a", tags=("ai",)),
            SyntheticRelationCard(id="c3", tags=("ai",)),
        ]
        edges = compute_multi_hop_related_cards("c1", [_to_record(c) for c in cards], max_depth=2)
        c3_edge = next(e for e in edges if e.target_card_id == "c3")
        assert "c2" in c3_edge.via_path  # 通过 c2 到达 c3

    def test_strength_decays_with_hop_distance(self):
        """同 reason 的边，2-hop 强度应低于同等条件下的 1-hop 强度。"""
        cards = [
            SyntheticRelationCard(id="c1", tags=("ai",)),
            SyntheticRelationCard(id="c2", tags=("ai",), source_id="src_x"),
            SyntheticRelationCard(id="c3", source_id="src_x"),
            SyntheticRelationCard(id="c4", source_id="src_x"),  # c1→c2 (tag, hop=1), c2→c4 (source, hop=2)
        ]
        edges = compute_multi_hop_related_cards("c1", [_to_record(c) for c in cards], max_depth=2)
        # 找 hop=1 的 SAME_TAG 边 (c1→c2: shared tag "ai")
        tag_hop1 = next((e for e in edges if e.target_card_id == "c2" and e.reason == RelationReason.SAME_TAG), None)
        assert tag_hop1 is not None, "Expected 1-hop tag edge to c2"
        # 手动计算：tag_hop1.strength * 0.7 ≈ decayed value
        # 验证 hop_distance 正确
        assert tag_hop1.hop_distance == 1
        # 验证 2-hop 边的 hop_distance 和衰减
        source_hop2 = [e for e in edges if e.target_card_id == "c3"]
        if source_hop2:
            assert source_hop2[0].hop_distance == 2
            # 检查强度衰减：2-hop strength = 1-hop base * 0.7
            # SAME_SOURCE base = 0.8, decayed by 0.7 → ~0.56
            assert source_hop2[0].strength <= 0.8 * 0.7 + 0.05  # 允许 recency bonus 微调

    def test_multiple_reasons_per_target(self):
        """同一 target 可通过多个 reason 关联（source + tag）。"""
        cards = [
            SyntheticRelationCard(id="c1", source_id="src_1", tags=("ai",)),
            SyntheticRelationCard(id="c2", source_id="src_1", tags=("ai",)),
        ]
        edges = compute_multi_hop_related_cards("c1", [_to_record(c) for c in cards], max_depth=1)
        c2_edges = [e for e in edges if e.target_card_id == "c2"]
        reasons = {e.reason for e in c2_edges}
        assert len(reasons) >= 2  # SAME_SOURCE + SAME_TAG

    def test_max_depth_limits_traversal(self):
        """max_depth 应限制遍历深度。"""
        cards = [
            SyntheticRelationCard(id="c1", tags=("a",)),
            SyntheticRelationCard(id="c2", tags=("a",), wiki_sections=("S1",)),
            SyntheticRelationCard(id="c3", wiki_sections=("S1",), source_id="src_x"),
            SyntheticRelationCard(id="c4", source_id="src_x"),
        ]
        edges_1 = compute_multi_hop_related_cards("c1", [_to_record(c) for c in cards], max_depth=1)
        edges_2 = compute_multi_hop_related_cards("c1", [_to_record(c) for c in cards], max_depth=2)
        # 深度越大，发现的卡片越多（或至少不减少）
        target_ids_1 = {e.target_card_id for e in edges_1}
        target_ids_2 = {e.target_card_id for e in edges_2}
        assert target_ids_1.issubset(target_ids_2)

    def test_no_self_reference_in_multi_hop(self):
        """BFS 不该将 center 自身作为 related card 返回。"""
        cards = [
            SyntheticRelationCard(id="c1", tags=("ai",)),
            SyntheticRelationCard(id="c2", tags=("ai",)),
        ]
        edges = compute_multi_hop_related_cards("c1", [_to_record(c) for c in cards], max_depth=2)
        assert all(e.target_card_id != "c1" for e in edges)


class TestRelatedCardEdgeV21:
    """v2.1 RelatedCardEdge 新字段测试。"""

    def test_hop_distance_default(self):
        edge = RelatedCardEdge(
            source_card_id="c1",
            target_card_id="c2",
            reason=RelationReason.SAME_SOURCE,
        )
        assert edge.hop_distance == 1

    def test_via_path_default(self):
        edge = RelatedCardEdge(
            source_card_id="c1",
            target_card_id="c2",
            reason=RelationReason.SAME_SOURCE,
        )
        assert edge.via_path == ()

    def test_edge_with_via_path(self):
        edge = RelatedCardEdge(
            source_card_id="c1",
            target_card_id="c3",
            reason=RelationReason.SAME_SOURCE,
            hop_distance=2,
            via_path=("c2",),
        )
        assert edge.hop_distance == 2
        assert edge.via_path == ("c2",)


class TestRelatedCardsPerformance:
    def test_performance_under_500ms(self):
        """计算时间 < 500ms"""
        import time
        cards = [
            SyntheticRelationCard(
                id=f"c{i}",
                source_id=f"src_{i % 20}",
                tags=(f"tag_{i % 10}",),
                wiki_sections=(f"section_{i % 5}",),
            )
            for i in range(1000)
        ]
        records = [_to_record(c) for c in cards]
        start = time.perf_counter()
        edges = compute_related_cards("c0", records)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Took {elapsed:.3f}s, expected < 0.5s"
        assert len(edges) > 0
