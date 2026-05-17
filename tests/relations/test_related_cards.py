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
