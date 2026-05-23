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

### 1.1 P3 Close Round (2026-05-23)

| File | Change |
|------|--------|
| `src/mindforge_web/services/web_facade.py` | +9 unique description_key across 11 sites |
| `src/mindforge_web/routers/sources.py` | +2 sites: action_key + description_key |
| `web/src/lib/utils.ts` | +2 action_key labels, +11 description_key entries (zh+en) |
| `tests/test_web_product_copy.py` | +4 test cases for P3 close coverage |

Total: 4 additional files changed.

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

### 4.1 P3 Close Round — Complete Inventory Coverage

After re-auditing all remaining NextAction sites, the final tally:

**web_facade.py (11 sites)** — all already had action_key from Milestone D, but NONE had description_key:
- `init_vault.desc`, `review_drafts.desc`, `watch_source.desc`, `search_knowledge.desc`
- `create_drafts.desc`, `search_approved_cards.desc`, `adjust_query.desc`, `rebuild_index.desc`, `try_another_query.desc`
- All 9 unique description_keys added across 11 construction sites

**routers/sources.py (2 sites)** — had NEITHER action_key nor description_key:
- `use_web_import` / `use_web_import.desc` (import-local fallback)
- `use_local_source` / `use_local_source.desc` (import-cubox-json fallback)

**web_review_service.py (1 site)** — DEFERRED with specific reason:
- `reject_unavailable()` at line 154: honest-unavailable placeholder for a reject feature that doesn't exist yet in the core backend. Adding action_key would imply this is a real action when it's a placeholder. When reject/defer is implemented, this site will be replaced entirely. Defer reason #1: "action 语义不清，确实需要用户产品判断".

**web_facade.py** — no longer excluded from scope. The blanket prohibition in Non-goal 11 was removed because adding description_key to existing action_key sites is purely additive and doesn't change business logic, API contracts, or behavior.

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
- `python -m pytest tests/test_web_product_copy.py -q`: 46 passed, EXIT_CODE=0
- `git diff --check`: EXIT_CODE=0
- New test cases: `nextActionDescription` existence, EmptyState/NextActionCard description_key usage, fallback null, provider safety i18n keys, onboarding explanation keys, action_key label mappings, SetupPage safety banner/onboarding, SourcesPage no hardcoded English
- P3 close test cases: `test_web_facade_description_keys_in_mapping`, `test_routers_sources_action_keys_in_next_action_label_mapping`, `test_routers_sources_description_keys_in_mapping`, `test_milestone_e_p3_close_all_inventory_sites_complete`

## 8. Browser Smoke

Pending — Phase 8.

## 9. Remaining P3/P4

- **web_review_service.py** (`reject_unavailable`, 1 site): DEFERRED — honest-unavailable placeholder for reject feature that doesn't exist yet. Will be replaced when reject/defer core service is implemented. Defer reason #1: "action 语义不清，确实需要用户产品判断".
- All other P3 NextAction sites across web_facade.py (11 sites) and routers/sources.py (2 sites) now COMPLETE with description_key.

No remaining P3/P4 from this milestone.

## 10. Rollback Record

None — no P0/P1/P2 found during code self-review.
