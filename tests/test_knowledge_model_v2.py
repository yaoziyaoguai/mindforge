import pytest
from pathlib import Path
from mindforge.cards import _load_summary

def test_load_summary_parses_knowledge_model_v2(tmp_path):
    card_path = tmp_path / "test_card.md"
    card_path.write_text(
        "---\n"
        "id: card_123\n"
        "status: human_approved\n"
        "knowledge_type: claim\n"
        "relations:\n"
        "  - type: supports\n"
        "    target_id: card_456\n"
        "human_note: This is a test note.\n"
        "---\n"
        "Body text\n",
        encoding="utf-8"
    )
    
    summary = _load_summary(card_path, tmp_path)
    
    assert summary.knowledge_type == "claim"
    assert summary.human_note == "This is a test note."
    assert len(summary.relations) == 1
    assert summary.relations[0]["type"] == "supports"
    assert summary.relations[0]["target_id"] == "card_456"

def test_load_summary_knowledge_model_fallbacks(tmp_path):
    card_path = tmp_path / "test_card_legacy.md"
    card_path.write_text(
        "---\n"
        "id: card_legacy\n"
        "status: human_approved\n"
        "---\n"
        "Body text\n",
        encoding="utf-8"
    )
    
    summary = _load_summary(card_path, tmp_path)
    
    assert summary.knowledge_type == "concept" # Default fallback
    assert summary.human_note is None
    assert summary.relations == ()
