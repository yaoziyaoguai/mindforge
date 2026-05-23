# Implementation Notes: Setup Deep Restructure (Milestone E)

## 1. Actual Modified Files

| File | Change | Unit |
|------|--------|------|
| `src/mindforge_web/schemas.py` | +1 field: `description_key` on `NextAction` | U6 |
| `src/mindforge_web/services/web_config_service.py` | +2 sites: action_key + description_key | U5 |
| `src/mindforge_web/services/web_source_service.py` | +7 sites: action_key + description_key | U5 |
| `src/mindforge_web/services/processing_run_service.py` | +6 sites: action_key + description_key | U5 |
| `web/src/api/types.ts` | +1 field: `description_key` on `NextAction` | U6 |
| `web/src/lib/utils.ts` | Extended `nextActionLabel()` 9→28 keys; new `nextActionDescription()` 22 keys | U5, U6 |
| `web/src/lib/i18n.ts` | +20 keys: provider safety copy, onboarding explanations | U1, U2, U3 |
| `web/src/components/EmptyState.tsx` | Uses `nextActionDescription()` for localized description | U6 |
| `web/src/components/NextActionCard.tsx` | Uses `nextActionDescription()` for localized description | U6 |
| `web/src/pages/SetupPage.tsx` | +Provider safety banner, readiness summary, onboarding `<details>` | U1, U2, U3, U4 |
| `web/src/pages/SourcesPage.tsx` | Fixed 2 hardcoded English error messages → `t()` | U7 |
| `docs/dev/copy-policy.md` | Updated with `description_key` contract and `nextActionDescription` | U8 |
| `tests/test_web_product_copy.py` | +9 test cases for Milestone E regression guard | U8 |

13 files changed, +408 / -15 lines.

## 2. Spec vs. Implementation Differences

- **U2 Wizard/progressive disclosure**: Instead of a multi-step wizard with step navigation, implemented as collapsible `<details>` elements explaining "why" each setup step is needed. Rationale: The existing 3-tab SetupPage already provides step separation; adding onboarding explanations within each tab achieves progressive disclosure without breaking the existing tab UX.
- **U4 Processing workflow copy**: The `strategyNameLabel` and `strategyStatusLabel` functions were already in place from Milestone C covering workflow display. No additional changes were needed — the mapping was already correct.

## 3. P3/P4 Incorporation

All 3 remaining P3/P4 items merged into Milestone E:

1. **P3: NextAction action_key on 17 remaining sites across 6 files** → Reduced scope to Setup/Sources/Processing only (15 sites across 3 files). Excluded web_review_service and web_facade per scope boundary.
2. **P3: EmptyState action.description localization** → `description_key` mechanism implemented.
3. **P3: Setup/Sources/Processing NextAction consistency review** → Completed; SourcesPage hardcoded English errors fixed.

## 4. action_key Completion Scope

15 NextAction sites in 3 service files:

- `web_config_service.py`: `setup.configure_cubox`, `setup.manage_watched_sources`
- `web_source_service.py`: `sources.create_source_folder`, `sources.add_watched_source`, `sources.back_to_watch_list`, `sources.view_source_status`, `sources.review_drafts`, `sources.add_watch_from_import`, `sources.import_once`
- `processing_run_service.py`: `processing.view_run_status`, `processing.review_drafts`, `processing.view_source_status`, `processing.view_error`, `processing.retry_processing`, `processing.view_sources`

Excluded from scope (per stop condition 6): web_review_service, web_facade, and other non-Setup/Sources/Processing services.

## 5. description_key Mechanism

- `NextAction.description_key: str | None` — stable machine-readable key, parallel to `action_key`
- Frontend `nextActionDescription(key, locale)` returns localized description or null
- EmptyState and NextActionCard call `nextActionDescription(action?.description_key, locale) ?? action?.description`
- 22 description keys mapped in both zh and en

## 6. Provider Safety Copy

SetupPage now shows after the provider status cards:
- Green badge "本地模拟" / "Local Simulated" for fake providers
- Blue badge "远程模型" / "Remote Model" for real providers
- Safety banner: "API Key 仅保存在本地 secret store 中..."
- Provider readiness row: shows Ready/Incomplete with active provider name and API key status

## 7. Test Results

- `npm --prefix web run build`: EXIT_CODE=0
- `python -m pytest tests/test_web_product_copy.py -q`: 42 passed, EXIT_CODE=0
- `git diff --check`: EXIT_CODE=0
- New test cases: `nextActionDescription` existence, EmptyState/NextActionCard description_key usage, fallback null, provider safety i18n keys, onboarding explanation keys, action_key label mappings, SetupPage safety banner/onboarding, SourcesPage no hardcoded English

## 8. Browser Smoke

Pending — Phase 8.

## 9. Remaining P3/P4

- NextAction action_key for web_review_service and web_facade (excluded from scope per stop condition)
- These should be addressed in a future milestone when those pages are refactored

## 10. Rollback Record

None — no P0/P1/P2 found during code self-review.
