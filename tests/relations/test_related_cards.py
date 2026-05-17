"""M3 Related Cards unit tests — SDD §7, TDD §5。"""

import pytest

from mindforge.relations.related_cards import (
    RelatedCardEdge,
    RelationReason,
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
