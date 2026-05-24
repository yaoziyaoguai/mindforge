# v1.4 W2: Knowledge Community Browser — Implementation Note

**Date:** 2025-05-25
**Status:** Complete

## What was done

Added a collapsible Knowledge Community Browser panel to the Library page, backed by a `GET /api/knowledge/communities` endpoint.

## Decisions

- **Backend uses `builder._cards` directly** — the initial implementation went through `library_cards()` → `library_card_detail()` which required two API round-trips and failed because `LibraryCardResponse` has no `.tags` attribute. The rewritten implementation calls `_build_graph_builder(cfg)` and passes `builder._cards` directly to `detect_communities()`, matching how the graph builder already works.
- **Method placement fix** — the `knowledge_communities` method was initially (from a prior session bug) nested inside `_provenance_trail_response` as a local function. It was moved to its correct position as a `WebFacade` class method, between `provenance_trail()` and the Graph API section.
- **Frontend collapsible `<details>`** — the community panel is hidden by default (`open={false}`) to avoid overwhelming the Library page. Users expand it when they want to browse communities.
- **Grouped display** — communities are grouped by type (source → tag → wiki_section), with the top 5 per type shown and a "+N more" indicator for overflow.

## Non-goals

- No click-through from community to filtered card view (future enhancement)
- No community hierarchy or nested communities (GraphRAG concept — deferred)

## Files changed

| File | Change |
|------|--------|
| `src/mindforge_web/services/web_facade.py` | Fix `knowledge_communities` method placement + implementation |
| `tests/relations/test_graph_api.py` | Add `TestKnowledgeCommunitiesEndpoint` (4 tests) |
| `web/src/api/types.ts` | Add `KnowledgeCommunityResponse`, `KnowledgeCommunitiesResponse` |
| `web/src/api/library.ts` | Add `getKnowledgeCommunities()` |
| `web/src/components/KnowledgeCommunityPanel.tsx` | New component |
| `web/src/pages/LibraryPage.tsx` | Integrate collapsible community panel |
| `web/src/lib/i18n.ts` | Add zh/en community labels |

## Gates

- pytest: exit 0, all tests pass
- ruff: All checks passed
- npm build: exit 0
- git diff --check: clean
