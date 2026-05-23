# Web i18n Mixed-language Follow-up Implementation Notes

**Date**: 2026-05-23
**Spec**: `docs/specs/2026-05-23-002-web-i18n-mixed-language-follow-up-spec.md`

## Summary

按 spec 完成全站 i18n 混用修复，覆盖 Setup / Sources / Wiki / Trash / SourceAddPanel 及所有 wiki 子组件。所有用户可见 UI copy 现在通过 `t()` 获取，后端 internal id 通过 display mapping 函数映射为本地化文案。

## Files Modified

| File | Change |
|------|--------|
| `web/src/lib/i18n.ts` | +95 zh keys, +95 en keys; fix ~4 zh values still in English (setup.save/validate/revert/unsaved); add TFunc type export |
| `web/src/lib/utils.ts` | Add workflowStepLabel, strategyStatusLabel, strategyNameLabel, sourceStatusLabel, sourceRunStatusLabel, sourceDueStatusLabel |
| `web/src/pages/SetupPage.tsx` | Replace ~20 hardcoded English strings with t(); use display mapping functions |
| `web/src/pages/SourcesPage.tsx` | Replace ~40 hardcoded English strings; use source display mappings; switch to getFrequencyOptions |
| `web/src/pages/TrashPage.tsx` | Full i18n: import useLocale, replace all ~15 hardcoded strings, use friendlyStatus |
| `web/src/pages/WikiPage.tsx` | Replace hardcoded error/status messages with t() |
| `web/src/components/SourceAddPanel.tsx` | Full i18n: useLocale, getFrequencyOptions(t) replaces static frequencyOptions |
| `web/src/components/wiki/WikiHeader.tsx` | useLocale for title/description |
| `web/src/components/wiki/WikiStatusBar.tsx` | useLocale for all labels, status, buttons |
| `web/src/components/wiki/WikiEmptyState.tsx` | useLocale for 3 empty states |
| `web/src/components/wiki/WikiErrorState.tsx` | useLocale for error title/retry |
| `web/src/components/wiki/WikiLoadingState.tsx` | useLocale for loading title/desc |
| `web/src/components/wiki/WikiAdvancedActions.tsx` | useLocale for troubleshooting |
| `web/src/components/wiki/WikiReadingPane.tsx` | useLocale for section headers |
| `web/src/components/wiki/WikiTOC.tsx` | useLocale for TOC labels, aria-label |
| `web/src/components/wiki/WikiSection.tsx` | useLocale for "Knowledge sources" |
| `web/src/components/wiki/WikiReferenceCard.tsx` | useLocale for "Approved" badge/tooltip |
| `web/src/components/wiki/WikiReferencePanel.tsx` | useLocale for default title |
| `web/src/components/wiki/WikiSectionRelationshipPreview.tsx` | useLocale for graph preview |
| `tests/test_web_product_copy.py` | Add 7 test functions for wiki/trash/source_add keys, useLocale coverage, display mappings; fix zh value assertions |

## What Was Fixed

### Category C1 (Backend data displayed directly)
- Source status codes: now mapped via sourceStatusLabel/sourceRunStatusLabel/sourceDueStatusLabel
- Workflow step IDs: now mapped via workflowStepLabel
- Strategy name/status: now mapped via strategyNameLabel/strategyStatusLabel
- Card previous_status in Trash: now mapped via friendlyStatus

### Category C2 (Frontend hardcoded English)
- SetupPage: "Default model", "Processing workflow", "View prompt", "Model", etc. → t()
- SourcesPage: "Process now", "Edit frequency", "Last run summary", etc. → t()
- TrashPage: all labels, buttons, empty state → t()
- Wiki: all 13 components → t()
- SourceAddPanel: all labels, buttons, hints → t()

### Category C3 (Missing i18n keys)
- +95 zh keys: sources.*, trash.*, wiki.*, source_add.*, shared.yes/no
- +95 corresponding en keys

### Category C4 (Incomplete display mappings)
- workflowStepLabel: triage/distill/link_suggestion/review_questions/action_extraction
- strategyStatusLabel, strategyNameLabel
- sourceStatusLabel, sourceRunStatusLabel, sourceDueStatusLabel
- friendlyStatus already existed from Milestone A

## What Was NOT Fixed (by design)

1. **NextAction backend labels**: Home page "Review drafts 有 ai_draft..." comes from backend `/api/home` `next_actions` data. This is C1 (backend hardcoded data). Per spec, backend API not modified.

2. **Source type labels in WikiReferenceCard**: "Markdown", "Text", "HTML", "PDF", "Word" are adapter format identifiers — proper nouns kept as-is with Chinese comment explaining the boundary.

3. **"API key" stays as "API key"**: Universal technical term, Chinese speakers commonly use it in English. zh value intentionally kept identical to en.

4. **Rebuild status messages**: WikiPage rebuild results like "Wiki rebuilt (llm): 5 cards, 3 sections" are technical status messages, not primary UI copy.

5. **SafetyBar labels**: "Local only", "Explicit approval required", "Safe local read" — these come from backend and are part of the safety/security contract. Not translated to avoid misrepresenting security posture.

## Test Strategy

Enhanced `tests/test_web_product_copy.py` with:
- `test_i18n_wiki_keys_complete` — verifies all 43 wiki-related zh/en keys exist and are non-empty
- `test_i18n_trash_keys_complete` — verifies 13 trash keys
- `test_i18n_source_add_keys_complete` — verifies 26 source_add keys
- `test_all_pages_use_locale` — verifies all 26 page/component files import useLocale
- `test_display_mapping_functions_exist` — verifies all 6 mapping functions
- `test_setup_page_uses_display_mappings` — verifies SetupPage imports mappings
- `test_sources_page_uses_display_mappings` — verifies SourcesPage imports mappings

Also fixed existing test assertions that compared zh values against English strings.

## Gate Results

| Gate | Result |
|------|--------|
| `npm --prefix web run build` | EXIT_CODE=0 |
| `python -m pytest tests/test_web_product_copy.py -q` | 23 passed, EXIT_CODE=0 |
| `git diff --check` | EXIT_CODE=0 |

## Browser Smoke Results

- Chinese mode: Sidebar fully Chinese, Home page Chinese ✓
- English mode: Sidebar fully English, Home page English ✓
- Language toggle works ✓
- No JS console errors ✓
- No raw i18n keys visible ✓
- 404 errors: expected (backend not running for smoke test)

## Deviations from Spec

1. **frequencyOptions removed instead of deprecated**: The backward-compatible export caused a runtime error (`t is not a function`). Removed entirely since SourcesPage now uses `getFrequencyOptions(t)`.

2. **setup.save/validate/revert/unsaved zh values**: These were still in English in the zh block. Fixed as part of this follow-up.

3. **EmptyState.tsx not i18n-ized**: This component receives translated strings via props (`title`, `action.label`). Adding useLocale would be redundant since its parent already translates.

## Remaining P3/P4

- P3: NextAction backend labels still mixed language (requires backend change, out of scope)
- P3: Source type format names (Markdown/HTML/PDF) kept as proper nouns
- P4: Rebuild status messages are technical/developer-facing, kept in English
