# MindForge v0.13 Closure Ledger

> Status: **stage-complete locally and pushed** (Stage 1–5 delivered
> and on `origin/main`). **No tag, no release.**
> Companion to [ROADMAP.md](./ROADMAP.md), [CHANGELOG.md](./CHANGELOG.md),
> [V0_13_RELEASE_READINESS_EVIDENCE.md](./V0_13_RELEASE_READINESS_EVIDENCE.md),
> [V0_13_REAL_SAFE_JOURNEY.md](./V0_13_REAL_SAFE_JOURNEY.md).

## Purpose

This ledger answers, for every v0.13-relevant capability, exactly **one
question**: *what state is it in right now, and who can trigger it?*
Five buckets only:

| Bucket          | Meaning                                                                       |
|-----------------|-------------------------------------------------------------------------------|
| `available`     | Always on, fake-safe, no opt-in needed                                        |
| `fake-only`     | Implemented, but only fake provider path is exercised                         |
| `real-opt-in`   | Real provider path implemented; user must explicitly opt in (flag + profile)  |
| `review-only`   | Output is a review packet / preview; never `human_approved`, never written     |
| `future-gated`  | Not implemented in v0.13; requires its own future opt-in gate to land         |
| `forbidden`     | Permanently rejected for v0.x; not a roadmap item                             |

## Ledger

| Capability                                          | State          | Triggered by                          | Output artifact          | Can produce `human_approved`? |
|-----------------------------------------------------|----------------|---------------------------------------|--------------------------|-------------------------------|
| Fake provider pipeline (default)                    | `available`    | any command, default                  | `ai_draft`               | No (only via approver)        |
| `mindforge provider readiness`                      | `available`    | user                                  | text/json report         | No                            |
| `mindforge provider smoke` (no `--allow-real`)      | `available`    | user                                  | refusal report           | No                            |
| `mindforge provider smoke --allow-real`             | `real-opt-in`  | user (flag + profile + env present)   | `ai_draft_preview`       | **No** (review-only contract) |
| `mindforge provider smoke --profile <name>`         | `real-opt-in`  | user                                  | `ai_draft_preview`       | No                            |
| `mindforge dogfood plan`                            | `available`    | user                                  | static checklist         | No                            |
| `mindforge dogfood preflight <path>`                | `available`    | user                                  | preflight report         | No (output_contract)          |
| Synthetic input (`examples/demo-vault`, etc.)       | `available`    | user                                  | n/a                      | No                            |
| `--declare-non-sensitive` local input               | `real-opt-in`  | user (explicit flag)                  | preflight report         | No                            |
| Home-directory scan                                 | `forbidden`    | n/a — preflight refuses               | refusal                  | No                            |
| Real Obsidian vault scan                            | `forbidden`    | n/a — preflight refuses               | refusal                  | No                            |
| Real Obsidian formal-note write                     | `future-gated` | requires explicit per-write gate      | n/a                      | No                            |
| Real Cubox API ingestion                            | `future-gated` | requires sample-folder + cap + gate   | n/a                      | No                            |
| `human_approved` promotion                          | `available`    | `approver.approve_card` + human only  | `human_approved` card    | Yes (only this path)          |
| Auto-approve / approval bypass                      | `forbidden`    | n/a                                   | n/a                      | No                            |
| Custom strategy declarative preview (v0.12)         | `available`    | user, registered yaml                 | preview-only artifact    | No                            |
| Custom executable strategy runtime                  | `future-gated` | requires sandboxed runtime gate       | n/a                      | No                            |
| Arbitrary Python plugin / shell strategy            | `forbidden`    | n/a                                   | n/a                      | No                            |
| RAG / embedding / semantic merge                    | `future-gated` | requires its own design / gate        | n/a                      | No                            |
| Public release / git tag                            | `future-gated` | requires human authorization          | n/a                      | No                            |

## v0.13 closure criteria — met?

| Criterion                                                                  | Met? | Evidence                                              |
|----------------------------------------------------------------------------|------|-------------------------------------------------------|
| Fake remains default                                                       | ✅   | `configs/mindforge.yaml: active_profile: fake`        |
| Real provider opt-in implemented                                           | ✅   | `provider_cli.py` + `--allow-real` + 3-gate           |
| Real LLM smoke runs end-to-end                                             | ✅   | Stage 3 evidence (DashScope qwen, 44/72 tokens)       |
| Synthetic input only for real smoke                                        | ✅   | `_SYNTHETIC_PROMPT` hard-coded in `real_smoke.py`     |
| Output of real smoke ≠ `human_approved`                                    | ✅   | `human_approved=False` permanently in audit-trail     |
| Controlled dogfood entrypoint (preflight)                                  | ✅   | Stage 4 `dogfood_safety.py` + `dogfood preflight`     |
| Home-scan / Obsidian-vault / private-data refused                          | ✅   | `_REFUSING_CLASSES` + 14 Stage 4 tests                |
| AST-guarded module boundaries                                              | ✅   | `_GUARDED` list covers all 4 v0.13 modules            |
| `human_approved` literal allowlist enforced                                | ✅   | `test_review_approval_boundary.py`                    |
| Quality gates green                                                        | ✅   | 1257 passed, 3 skipped; ruff clean; diff-check clean  |
| No tag / no release                                                        | ✅   | `git tag --list "v0.13*"` empty                       |

**Verdict**: v0.13 is **stage-complete**. Tag/release decision is a
separate human authorization step (see Release Readiness Evidence).

## Out of scope for v0.13 (escalated to v0.14+)

- Real Cubox ingestion gate (sample-folder + item-cap + dry-run-first)
- Real Obsidian write gate (per-write confirmation prompt)
- `human_approved` workflow UX (still requires manual approver call)
- Custom executable strategy runtime (sandbox design first)
- RAG / embedding / semantic merge (separate design milestone)
- Public release / tag / packaging publish (human authorization)
