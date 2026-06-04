# Knowledge Experience Reconstruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completely reconstruct the Knowledge/Wiki experience by strictly enforcing approval boundaries, introducing typed knowledge and semantic relations, and transitioning from a monolithic Markdown file to a runtime API presenter.

**Architecture:** Deprecate `llm_rebuild_wiki` to stop unauthorized AI text generation. Enhance `CardSummary` with `knowledge_type` and `relations`. Implement a `TopicPresenter` to dynamically aggregate approved cards. Provide new REST APIs for the frontend. (Frontend UI implementation will be a separate, subsequent plan).

**Tech Stack:** Python, FastAPI, Pytest, YAML (for frontmatter).

---

### Task 1: Freeze Current Risk (Deprecate `llm_rebuild_wiki`)

**Files:**
- Modify: `src/mindforge_web/routers/wiki.py`
- Modify: `tests/test_wiki_related_sections.py` (or similar wiki router tests if they exist to adjust expectations)

- [ ] **Step 1: Write the failing test for the router**

```python
# Create/modify test in tests/test_wiki_router.py (or similar suitable file)
def test_wiki_rebuild_llm_is_deprecated(client, mock_facade):
    response = client.post("/api/wiki/rebuild", json={"mode": "llm"})
    assert response.status_code == 410 # Or 400 with specific message
    data = response.json()
    assert data["ok"] is False
    assert "deprecated" in data["error"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_wiki_router.py -v` (Adjust filename based on actual test location)
Expected: FAIL (currently returns 200 OK or tries to build)

- [ ] **Step 3: Write minimal implementation**

Modify `src/mindforge_web/routers/wiki.py` inside `wiki_rebuild`:

```python
@router.post("/rebuild")
def wiki_rebuild(
    payload: WikiRebuildRequest | None = None,
    facade: WebFacade = Depends(get_facade),
):
    """(Deprecated) From v0.5, direct LLM Wiki rebuild is disabled to enforce approval boundaries."""
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        status_code=410,
        content={
            "ok": False,
            "mode": payload.mode if payload else facade.cfg.wiki.mode,
            "error": "Direct LLM Wiki rebuild is deprecated in v0.5 to enforce strict approval boundaries. LLM summaries must now be generated as AI drafts and explicitly approved."
        }
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_wiki_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mindforge_web/routers/wiki.py tests/
git commit -m "feat(wiki): deprecate llm_rebuild_wiki API endpoint"
```

---

### Task 2: Implement Knowledge Model v2 Core

**Files:**
- Modify: `src/mindforge/cards.py`
- Create/Modify: `tests/test_knowledge_model_v2.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_knowledge_model_v2.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_knowledge_model_v2.py -v`
Expected: FAIL (`CardSummary` lacks new attributes)

- [ ] **Step 3: Write minimal implementation**

Modify `src/mindforge/cards.py`:
1. Add to `CardSummary` dataclass:
```python
    # M5.x Knowledge Model v2
    knowledge_type: str = "concept"
    relations: tuple[dict[str, str], ...] = ()
    human_note: str | None = None
```
2. Add helper function `_parse_relations`:
```python
def _parse_relations(v: Any) -> tuple[dict[str, str], ...]:
    if not isinstance(v, list):
        return ()
    parsed = []
    for item in v:
        if isinstance(item, dict):
            rel_type = str(item.get("type", ""))
            target_id = str(item.get("target_id", ""))
            if rel_type and target_id:
                parsed.append({"type": rel_type, "target_id": target_id})
    return tuple(parsed)
```
3. Update `_load_summary` return instantiation:
```python
        # ... existing args ...
        knowledge_type=_str_or_none(data.get("knowledge_type")) or "concept",
        human_note=_str_or_none(data.get("human_note")),
        relations=_parse_relations(data.get("relations")),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_knowledge_model_v2.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mindforge/cards.py tests/test_knowledge_model_v2.py
git commit -m "feat(cards): implement knowledge model v2 schema and fallbacks"
```

---

### Task 3: Implement Topic Presenter (Approval Boundary Enforcement)

**Files:**
- Create: `src/mindforge/topic_presenter.py`
- Create: `tests/test_topic_presenter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_topic_presenter.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_topic_presenter.py -v`
Expected: FAIL (`mindforge.topic_presenter` not found)

- [ ] **Step 3: Write minimal implementation**

Create `src/mindforge/topic_presenter.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_topic_presenter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mindforge/topic_presenter.py tests/test_topic_presenter.py
git commit -m "feat(presenter): implement strict TopicPresenter with approval boundaries"
```

---

### Task 4: Expose Topic API

**Files:**
- Create: `src/mindforge_web/routers/topics.py`
- Modify: `src/mindforge_web/app.py` (to include the new router, check structure first)
- Create: `tests/test_api_topics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_topics.py
def test_get_topic_view(client, mock_facade):
    # Setup mock_facade.cfg to point to dummy data if needed, or mock iter_cards
    # For now, just test the endpoint existence and basic structure
    response = client.get("/api/topics/TestTopic")
    assert response.status_code == 200
    data = response.json()
    assert "topic" in data
    assert data["topic"] == "TestTopic"
    assert "cards" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_topics.py -v`
Expected: FAIL (404 Not Found)

- [ ] **Step 3: Write minimal implementation**

Create `src/mindforge_web/routers/topics.py`:
```python
from fastapi import APIRouter, Depends
from mindforge_web.deps import get_facade
from mindforge_web.services.web_facade import WebFacade
from mindforge.cards import iter_cards
from mindforge.topic_presenter import build_topic_view

router = APIRouter(prefix="/api/topics", tags=["topics"])

@router.get("/{topic_name}")
def get_topic(topic_name: str, facade: WebFacade = Depends(get_facade)):
    scan = iter_cards(facade.cfg.vault.root, facade.cfg.vault.cards_dir)
    view = build_topic_view(topic_name, scan.cards)
    return view
```

*(Note: Verify where routers are included, likely in `src/mindforge_web/app.py` or `src/mindforge_web/main.py`. Include the router there.)*
```python
# e.g., in app.py:
# from .routers import topics
# app.include_router(topics.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_topics.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mindforge_web/routers/topics.py tests/test_api_topics.py
# git add src/mindforge_web/app.py (if modified)
git commit -m "feat(api): expose /api/topics endpoint driven by TopicPresenter"
```
````