# Dogfood Readiness P3/P4 Closure

## 1. Context

- **Date**: 2026-05-23
- **Source**: Dogfood readiness browser smoke notes (`2026-05-23-005`)
- **Goal**: Close remaining P3/P4 UX issues before fake dogfood; avoid rolling backlog
- **Constraint**: No new features, no real LLM, no provider/approval/recall/BM25 semantic changes

## 2. P3/P4 Master List & Triage

### P3-1: Setup form accessibility — form fields missing id/name/label associations

**Root cause**: SetupPage model edit form uses `<label>` wrappers without `htmlFor`, and most `<input>/<select>` lack `id`/`name` attributes. Screen readers can't associate labels with controls.

**Fix strategy**: Add stable `id` and `name` to all form controls in model edit form, default model select, workflow routing selects, wiki model select, wiki auto-rebuild checkbox. Add `htmlFor` to corresponding labels.

**Will fix this round**: Yes. Low risk, no behavior change, pure a11y markup.

**Files**: `web/src/pages/SetupPage.tsx`

### P3-2: Source status values mapping (Manual/Missing/Failed)

**Root cause**: Dogfood smoke flagged `display_status` / `generated_knowledge_status` potentially showing raw English values.

**Actual state**: SourcesPage already uses `sourceStatusLabel()`, `sourceRunStatusLabel()`, `sourceDueStatusLabel()` with locale. The `SourceStatus.display_status` field exists in types but is NOT rendered in any frontend component — it's only used for bucket counting. `WatchedSourceResponse.status_label` is set by backend and used as primary display with `sourceStatusLabel()` as fallback.

**Will fix this round**: No. Already resolved by existing display mapping. No raw status values leak to user-facing UI.

### P3-3: /search route shows Home content

**Root cause**: App.tsx routes only `/recall` to RecallPage. Sidebar links to `/recall` with label "搜索"/"Search". If user navigates to `/search`, no route matches, falls to default HomePage.

**Fix strategy**: Add `|| path.startsWith("/search")` to the RecallPage condition in App.tsx line 74.

**Will fix this round**: Yes. One-line change, no behavioral risk.

**Files**: `web/src/App.tsx`

### P3-4: Workflow strategy description shows raw API text in wrong locale

**Root cause**: `active_strategy_description` from backend is displayed raw on SetupPage line 539 without locale mapping. Description is in Chinese but shows even in en mode.

**Fix strategy**: Add `strategyDescriptionLabel()` to utils.ts following the same pattern as `strategyNameLabel()`/`strategyStatusLabel()`. Use in SetupPage line 539.

**Will fix this round**: Yes. Follows existing display mapping pattern.

**Files**: `web/src/lib/utils.ts`, `web/src/pages/SetupPage.tsx`

### P3-5: NextAction action_key / description_key gaps

**Root cause**: Dogfood smoke identified missing action_key/description_key on some NextAction items.

**Actual state**: All backend NextAction items in `web_facade.py`, `web_config_service.py`, `web_source_service.py`, `processing_run_service.py` already populate `action_key` and `description_key`. Frontend `nextActionLabel()` and `nextActionDescription()` have full zh/en mappings. EmptyState and NextActionCard components both use the display mapping functions.

**Will fix this round**: No. Already resolved by prior Milestone E work.

### P3-6: EmptyState action.description localization

**Root cause**: Dogfood smoke flagged `action.description` showing raw text without locale mapping.

**Actual state**: EmptyState.tsx already uses `nextActionDescription(action?.description_key, locale) ?? action?.description`. All backend NextAction items have `description_key`. Fallback to raw `action.description` is by design for safety.

**Will fix this round**: No. Already resolved.

### P3-7: Setup/Sources/Processing page-level NextAction consistency

**Root cause**: Dogfood smoke flagged inconsistent NextAction display across pages.

**Actual state**: All pages use either `NextActionCard` (with `nextActionLabel` + `nextActionDescription`) or inline NextAction rendering via `nextActionLabel`. Backend services populate consistent action_key/description_key. Locale is passed consistently.

**Will fix this round**: No. Already consistent after Milestone E.

### P3-8: display_status mapping (from dogfood smoke P3-3)

**Root cause**: Source status values like "Manual", "Missing", "Failed" are technical labels.

**Actual state**: These values come from `SourceStatus.display_status` which is only used in backend bucket counting (`bucket_counts`). Frontend never renders `display_status` — the `SourcesPage` watcher view uses `WatchedSourceResponse.status_label || sourceStatusLabel(source.status, locale)`.

**Will fix this round**: No. Values not user-visible. If they become visible in future, add `sourceDisplayStatusLabel()` mapping.

### P4-1: StatusCard inline nextAction fallback chain too aggressive

**Root cause**: StatusCard line 30-31: `nextActionLabel(...) ?? nextAction.label ?? nextAction.command ?? nextAction.description`. The chain falls through to `command` and `description` which are not suitable as label text.

**Fix strategy**: Tighten to `nextActionLabel(...) ?? nextAction.label`. The description is already shown via the `detail` prop. Command should not be shown as label text.

**Will fix this round**: Yes. Tightens display contract.

**Files**: `web/src/components/StatusCard.tsx`

### P4-2: Rebuild / technical status polish

**Root cause**: Wiki rebuild tooltip and developer-facing copy could be more polished.

**Actual state**: All Wiki/rebuild copy is already in i18n with zh/en. Technical status labels use friendlyStatus mapping. No hardcoded developer copy visible to users.

**Will fix this round**: No. Already handled by existing i18n.

### P4-3: React DevTools console message

**Root cause**: React DevTools info message in browser console.

**Actual state**: This is a browser extension message, not from application code. Cannot be fixed from our side.

**Will fix this round**: No. Not an application issue.

## 3. This Round: Fix Plan

| ID | Item | Action | Risk |
|----|------|--------|------|
| P3-1 | Setup form accessibility | Add id/name/htmlFor to form controls | Low — pure markup |
| P3-3 | /search route | Add /search alias in App.tsx | Low — one line |
| P3-4 | Strategy description | Add display mapping in utils.ts + SetupPage | Low — follows existing pattern |
| P4-1 | StatusCard fallback | Tighten fallback chain | Low — removes incorrect fallbacks |

## 4. Not Fixed This Round (with specific reasons)

| ID | Reason |
|----|--------|
| P3-2 | Already resolved: SourcesPage uses sourceStatusLabel/sourceRunStatusLabel/sourceDueStatusLabel with locale |
| P3-5 | Already resolved: all backend NextAction items have action_key/description_key; frontend mappings complete |
| P3-6 | Already resolved: EmptyState uses nextActionDescription with locale |
| P3-7 | Already resolved: NextAction display consistent across all pages |
| P3-8 | Not user-visible: display_status only used in backend bucket counting, not rendered in UI |
| P4-2 | Already resolved: rebuild copy in i18n |
| P4-3 | Not fixable: browser DevTools message, not application code |

## 5. Files to Modify

- `web/src/pages/SetupPage.tsx` — P3-1 (form a11y) + P3-4 (strategy description)
- `web/src/App.tsx` — P3-3 (/search route)
- `web/src/lib/utils.ts` — P3-4 (strategyDescriptionLabel)
- `web/src/components/StatusCard.tsx` — P4-1 (fallback chain)

## 6. Gate Plan

- `npm --prefix web run build` → exit code 0
- `python -m pytest tests/test_web_product_copy.py -q` → exit code 0
- `git diff --check` → exit code 0

## 7. Smoke Plan

Browser MCP smoke:
1. Setup page loads, form fields have id/name
2. zh/en toggle works
3. /search → shows RecallPage (not Home)
4. SourcesPage status labels zh/en correct
5. Workflow strategy description zh/en correct
6. No regression on Home/Library/Wiki/Drafts/Trash
7. No console errors, no 4xx/5xx
