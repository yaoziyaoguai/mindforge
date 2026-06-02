# MindForge Web UI Backend Gap Log

Last updated: 2026-06-02

This log prevents the reference-image redesign from implying backend capabilities that do not exist yet.

## Batch 1: Shell, Home, Setup

| page/type | UI expectation from reference | current backend/API support | current UI behavior | needed backend work | priority | safe to show in UI now? | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Home / Welcome Desk | Overview cards for Sources, AI Drafts, Ready for Review, Approved Knowledge | partial | real data when `/api/workflow/summary` is present; fallback to `/api/home/status` workspace/vault/safety counts | If product wants richer source freshness or per-stage deltas, add explicit home dashboard summary fields | P1 | yes | Counts shown are from existing status APIs or clearly minimal fallbacks; no fake cards are rendered. |
| Home / Welcome Desk | Knowledge Flow: Import -> AI Draft -> Human Review -> Approved Knowledge -> Export | yes for product semantics, partial for per-step live activity | static explanatory flow using real product states and links | Optional per-step live status endpoint if future UI wants progress details | P2 | yes | Flow explains current lifecycle boundaries; it does not claim live pipeline automation beyond existing states. |
| Home / Welcome Desk | First-run Configure Real Model card | yes for provider readiness/status, no for one-click setup | status card and CTA route to Setup only | None for status; future improvement could return recommended setup preset from backend | P2 | yes | Sidebar/Home card is status display and navigation, not a hidden provider activation action. |
| Sidebar | Demo Mode / Configure Real Model card | partial | uses `SafetySummary.provider_state`; CTA navigates to `/setup` | Optional richer provider readiness reason summary for sidebar | P2 | yes | It only distinguishes demo vs ready provider and does not modify provider mode. |
| Setup / Model Configuration | Provider -> Connection -> Model -> Validate/Test guide | partial | guide uses `ConfigStatusResponse.provider` and `/api/config/editable`; existing form still saves via current API | Backend could expose a first-run setup wizard shape if future UI needs server-authored steps | P2 | yes | Guide is a UI organization layer over existing editable config/readiness. |
| Setup / Model Configuration | Validate/Test a configured provider | partial | `Validate Config` calls existing `validateSetupConfig`; no real LLM smoke/test is triggered | Add explicit non-generative readiness test endpoint if product wants endpoint/auth verification without content generation | P1 | yes | The UI labels Validate/Test as configuration validation and states no real LLM call occurs. |
| Setup / Model Configuration | Provider presets: Qwen / OpenAI-compatible / Anthropic-compatible / Custom | partial | OpenAI-compatible and Anthropic-compatible are shown as supported mappings; Qwen and Custom are marked manual endpoint configuration | Add first-class provider presets only if backend supports provider-specific defaults and validation | P2 | yes | Presets are explanatory cards, not fake one-click integrations. |
| Setup / Model Configuration | API key display | yes | input is write-only; configured keys are shown only as presence/masked state from editable config | None for Batch 1 | P0 | yes | Preserves secret boundary; no plaintext API key is shown. |
| Setup / Model Configuration | Configure complete -> go to Sources/Drafts | yes for navigation, partial for contextual recommendation | guide text points to Sources after save/validate; no automatic redirect | Optional next-action endpoint could suggest Sources vs Drafts from current state | P3 | yes | Guidance is copy and navigation only; no fake completion state. |

## Backend -> Frontend Matrix: Batch 1

| backend/API capability | route/service/api file | current frontend surface | expose now? | if no, why | future UI slice | priority |
| --- | --- | --- | --- | --- | --- | --- |
| Home status with safety/workspace/vault/provider/recall summaries | `web/src/api/home.ts`, `/api/home/status` | Home overview, SafetyBar, Sidebar provider card | yes | n/a | Add richer empty states after Batch 2 pages settle | P0 |
| Workflow summary with processed source, ai_draft, human_approved counts | `web/src/api/workflow.ts`, `/api/workflow/summary` | Home overview cards | yes | n/a | Could drive per-stage flow activity badges | P1 |
| Editable setup config and masked secret metadata | `web/src/api/config.ts`, `/api/config/editable` | Setup guide and existing model form | yes | n/a | Improve provider preset form defaults | P0 |
| Provider mode opt-in/out | `web/src/api/config.ts`, provider mode endpoints | Existing Setup activation dialog only | yes, but only in Setup | Sidebar/Home must not activate real mode implicitly | Keep opt-in confirmation in Setup | P0 |
| Setup validation | `web/src/api/config.ts`, `/api/config/validate` | Setup guide Validate Config and existing Validate button | yes | n/a | Add clearer validation result panel | P1 |
| Lab/internal graph/sensemaking/dogfood routes | existing app routes/pages | collapsed Lab only | no main-path exposure | Product boundary says Graph/Sensemaking/Entity/Community are lab/internal, not primary workflow | Separate lab redesign if requested | P3 |

## Assets

No external assets were added in Batch 1.
