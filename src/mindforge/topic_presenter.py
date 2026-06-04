from typing import Any, Iterable
from .cards import CardSummary

def build_topic_view(topic: str, all_cards: Iterable[CardSummary]) -> dict[str, Any]:
    """
    Builds a secure, runtime view of a topic.
    CRITICAL: Enforces the approval boundary. Only human_approved cards are included.
    """
    approved_cards = []
    type_counts: dict[str, int] = {}
    
    for card in all_cards:
        # STRICT APPROVAL BOUNDARY
        if card.status != "human_approved":
            continue
            
        if card.track != topic:
            continue
            
        approved_cards.append({
            "id": card.id,
            "title": card.title,
            "knowledge_type": card.knowledge_type,
            "relations": list(card.relations),
            "tags": list(card.tags),
            "summary": "", # In a real implementation, we might need to fetch the body snippet carefully
            "value_score": card.value_score
        })
        
        k_type = card.knowledge_type or "concept"
        type_counts[k_type] = type_counts.get(k_type, 0) + 1
        
    return {
        "topic": topic,
        "total_approved_cards": len(approved_cards),
        "type_counts": type_counts,
        "cards": approved_cards
    }
