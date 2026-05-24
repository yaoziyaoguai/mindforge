"""v0.4 U1 golden tests — Wiki Related Sections computation."""

import pytest
from mindforge.wiki_service import compute_wiki_related_sections


class TestComputeWikiRelatedSections:
    def test_empty_map_returns_empty(self):
        result = compute_wiki_related_sections({})
        assert result == {}

    def test_single_section_returns_empty(self):
        """Single section has no other sections to relate to."""
        result = compute_wiki_related_sections({"Section A": ["card-1", "card-2"]})
        assert result == {}

    def test_two_sections_with_shared_cards(self):
        section_map = {
            "Section A": ["card-1", "card-2", "card-3"],
            "Section B": ["card-2", "card-3", "card-4"],
        }
        result = compute_wiki_related_sections(section_map)

        # Section A → Section B should be related
        assert len(result["Section A"]) == 1
        assert result["Section A"][0]["title"] == "Section B"
        # Jaccard: |{card-2, card-3}| / |{card-1, card-2, card-3, card-4}| = 2/4 = 0.5
        assert result["Section A"][0]["overlap"] == 0.5
        assert result["Section A"][0]["shared_cards"] == 2

        # Section B → Section A
        assert len(result["Section B"]) == 1
        assert result["Section B"][0]["title"] == "Section A"

    def test_three_sections_returns_top_n(self):
        section_map = {
            "Section A": ["card-1", "card-2", "card-3"],
            "Section B": ["card-2", "card-3", "card-4"],
            "Section C": ["card-3"],
        }
        result = compute_wiki_related_sections(section_map, top_n=2)

        # Section A should have B (0.5) and C (0.25) — top 2
        assert len(result["Section A"]) == 2
        assert result["Section A"][0]["title"] == "Section B"
        assert result["Section A"][1]["title"] == "Section C"

    def test_sections_with_no_shared_cards(self):
        section_map = {
            "Section A": ["card-1"],
            "Section B": ["card-2"],
        }
        result = compute_wiki_related_sections(section_map)
        assert result["Section A"] == []
        assert result["Section B"] == []

    def test_sections_with_empty_card_lists(self):
        section_map = {
            "Section A": [],
            "Section B": ["card-1"],
        }
        result = compute_wiki_related_sections(section_map)
        assert result["Section A"] == []
        # B has no related because A has no cards to share
        assert result["Section B"] == []

    def test_returns_top_n_default_three(self):
        section_map = {
            "S1": ["c1", "c2"],
            "S2": ["c1", "c2"],
            "S3": ["c1", "c2"],
            "S4": ["c1", "c2"],
            "S5": ["c1", "c2"],
        }
        result = compute_wiki_related_sections(section_map)
        # Each section should have at most 3 related sections
        for sec_title, related in result.items():
            assert len(related) <= 3

    def test_jaccard_calculation_accuracy(self):
        """Golden test: verify Jaccard = intersection / union."""
        section_map = {
            "A": ["c1", "c2", "c3", "c4"],
            "B": ["c3", "c4", "c5", "c6"],
        }
        result = compute_wiki_related_sections(section_map)
        # intersection: c3, c4 = 2
        # union: c1, c2, c3, c4, c5, c6 = 6
        # jaccard = 2/6 = 0.333
        assert result["A"][0]["overlap"] == pytest.approx(0.333, abs=0.001)
        assert result["A"][0]["shared_cards"] == 2
