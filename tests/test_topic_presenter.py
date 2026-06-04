from datetime import datetime
from pathlib import Path
from mindforge.cards import CardSummary
from mindforge.topic_presenter import build_topic_view

def test_topic_presenter_enforces_approval_boundary():
    approved_card = CardSummary(
        id="c1", title="Approved", status="human_approved", path=Path("c1.md"), rel_path="c1.md",
        projects=(), tags=(), source_type=None, track="React", knowledge_type="concept"
    )
    draft_card = CardSummary(
        id="c2", title="Draft", status="ai_draft", path=Path("c2.md"), rel_path="c2.md",
        projects=(), tags=(), source_type=None, track="React", knowledge_type="summary"
    )
    
    view = build_topic_view("React", [approved_card, draft_card])
    
    assert view["topic"] == "React"
    assert len(view["cards"]) == 1
    assert view["cards"][0]["id"] == "c1"
    # Draft card MUST NOT be included
    
def test_topic_presenter_groups_by_knowledge_type():
    c1 = CardSummary(id="c1", title="C1", status="human_approved", path=Path("c1.md"), rel_path="c1", projects=(), tags=(), source_type=None, track="React", knowledge_type="concept")
    c2 = CardSummary(id="c2", title="C2", status="human_approved", path=Path("c2.md"), rel_path="c2", projects=(), tags=(), source_type=None, track="React", knowledge_type="claim")
    
    view = build_topic_view("React", [c1, c2])
    
    assert view["type_counts"]["concept"] == 1
    assert view["type_counts"]["claim"] == 1
