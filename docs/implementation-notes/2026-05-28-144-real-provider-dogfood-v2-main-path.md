# Real Provider Dogfood v2 — Main Path Verification

Date: 2026-05-28
Task type: `dogfood`
Provider: qwen3.6-plus (real, user-configured via Web UI)
Workspace: `/tmp/mindforge-real-provider-dogfood-20260528-v2-workspace`
Server: `http://127.0.0.1:8765`, fresh clone v2 at commit `8c62c33`

## Pipeline Results

| Stage | Result | Details |
|-------|--------|---------|
| Provider Readiness | PASS | `model_setup: ready`, `provider_mode: real`, `can_run_real_smoke: true` |
| Sample Workspace | PASS | 6 demo cards created via `POST /api/sample-workspace` |
| Source Import | PASS | `engineering-workflow.md` imported, `processing_status: succeeded` |
| AI Draft (real LLM) | PASS | qwen3.6-plus generated 1 draft, `value_score=8`, `strategy_version=0.10.0` |
| Explicit Approve | PASS | `ai_draft → human_approved`, BM25 index updated (`index_updated: true`) |
| Library | PASS | 7 cards visible (1 real import + 6 demo) |
| Recall (BM25) | PASS | Top hit `score=10.88` for "MindForge 工程工作流", `why_this_matched: title(w=5.0)` |
| Wiki | PASS | 7 sections, ~2K+ chars deterministic generation |
| Export (ZIP) | PASS | 200 OK, 3KB ZIP for single card export |

## Safety Boundary

| Invariant | Status |
|-----------|--------|
| `fake_is_default` | true |
| `secret_value_not_returned` | true |
| `human_approval_required` | true |
| `synthetic_only_smoke_input` | true |
| `real_output_is_review_only` | true |
| No raw API key in any response | PASS |

## Key Observations

1. **Real LLM call succeeded** — qwen3.6-plus correctly processed `engineering-workflow.md` through the full 5-stage pipeline (Triage → Distill → Link → Questions → Actions), producing a high-quality knowledge card in Chinese.
2. **P0 DOGFOOD-001 fix verified** — `provider_readiness_detail()` no longer crashes, returns correct masked API key status.
3. **Explicit approval boundary intact** — approve requires `confirm: true` + `reviewed_source: true`, cannot be bypassed.
4. **BM25 index correctly updated** on approve — Recall immediately finds the newly approved card.
5. **Wiki rebuild works** with 7 cards in deterministic mode.

## No Blockers Found

- P0: resolved (`8c62c33`)
- P1: verified as false positive (all 5 endpoints have registered routes)
- P2: documented as product note (triage threshold intentional)

## API Endpoint Notes

- `/api/recall` is GET with `?q=` query param (not POST)
- `/api/knowledge/export/download` is POST with `{"card_ids": [...], "format": "zip"}` body
- `/api/sources/import-folder` does not exist — use `/api/knowledge/import/folder` instead

## Next Steps

- User Validation with 5 real non-technical users (HARD_STOP_PRODUCT_DECISION — requires real users)
- Guided Onboarding MVP is already implemented — ready for first-run UX testing
