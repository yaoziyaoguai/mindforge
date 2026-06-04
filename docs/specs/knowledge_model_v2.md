# Specification: Knowledge Model v2

## Overview
This document defines the schema additions to the Knowledge Card YAML frontmatter. The goal is to evolve cards from "flat text containers" to typed, semantically linked nodes in a personal knowledge network, without introducing heavy graph databases or vector stores.

## Schema Additions

### 1. `knowledge_type` (Enum)
Defines the epistemological nature of the card.
*   `concept`: A definition, factual entity, or established term. (Fallback for legacy cards)
*   `claim`: An assertion, opinion, or thesis that can be debated, supported, or contradicted.
*   `insight`: A personal realization, synthesis, or "aha" moment.
*   `method`: A process, SOP, or "how-to".
*   `evidence`: Raw data, quotes, or empirical observations used to support claims.
*   `todo`: An actionable item or next step derived from knowledge.
*   `summary`: An LLM-generated or human-written overview of a topic. (Crucial: LLM summaries must start as `ai_draft`).

### 2. `relations` (List of Objects)
Defines explicit, directed semantic links to other cards.

**Schema:**
```yaml
relations:
  - type: supports       # Required
    target_id: card_123  # Required: The `id` of the target card
```

**Allowed `type` values:**
*   `supports`: This card provides evidence or argument for the target.
*   `contradicts`: This card argues against or provides counter-evidence to the target.
*   `expands`: This card provides more detail or a sub-topic of the target.
*   `example_of`: This card is a specific instance of the target (usually a concept).
*   `derived_from`: This card's conclusion was logically drawn from the target.
*   `prerequisite_of`: This card must be understood before the target.
*   `related_to`: A generic, weak associative link (use sparingly).

### 3. `human_note` (String, Optional)
A dedicated field for the user to append personal thoughts, context, or caveats during the approval process, kept separate from the `AI Summary`.

## Fallback & Compatibility Rules

When parsing existing `CardSummary` objects in `src/mindforge/cards.py`:
1.  **Missing `knowledge_type`**: If absent or invalid, default to `"concept"`.
2.  **Missing `relations`**: If absent or malformed, default to an empty tuple `()`.

## Validation Constraints
*   The `cards.py` parser must *never* throw a fatal error if these fields are malformed; it must log a warning internally (or handle it silently) and use the fallbacks, ensuring the application remains robust.
*   These fields are metadata. The actual reasoning or explanation of *why* a relation exists should remain in the markdown body.
