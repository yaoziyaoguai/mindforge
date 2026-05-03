# MindForge v0.13 Release Readiness Evidence Pack

> Status: **evidence only**. **No tag, no release.** A tag / publish
> decision is a separate human authorization step. This document is
> the audit trail that *would* be referenced by a future authorizer.

## 1. Quality Gates (last green run)

| Gate                                | Result                       |
|-------------------------------------|------------------------------|
| `.venv/bin/ruff check .`            | All checks passed!           |
| `.venv/bin/pytest --no-header`      | **1257 passed, 3 skipped**   |
| `git diff --check`                  | clean                        |
| Sensitive-token sweep on new files  | only intentional negatives   |
| AST guard on v0.13 modules          | all 4 modules pass `_GUARDED`|
| `human_approved` literal allowlist  | enforced (boundary test)     |

## 2. Safety Gates

| Invariant                                                       | Enforced by                                            |
|-----------------------------------------------------------------|--------------------------------------------------------|
| Default `active_profile` is `fake`                              | `configs/mindforge.yaml` + `test_v013_stage2_consistency` |
| Env presence alone does NOT activate real                       | `classify_real_opt_in` → `env_only` ≠ `ready`           |
| Real provider call requires `--allow-real` AND profile ≠ fake AND alias key present | `real_smoke.run_synthetic_real_smoke` 3-gate |
| Real-smoke prompt is hard-coded synthetic                       | `_SYNTHETIC_PROMPT` constant                           |
| Real-smoke output `human_approved=False`, `written=False`       | dataclass-shaped audit trail                           |
| Provider error messages NOT echoed (no leak of server hints)    | separate `ProviderError` catch                          |
| API key value NEVER read or returned                            | `inspect_provider_config` presence-only                 |
| `.env` never overrides existing env (12-factor)                 | `env_loader.load_dotenv_silently`                      |
| `.env` never printed                                            | silent loader; `provider readiness` returns presence-bool |
| Dogfood preflight refuses home / Obsidian / nonexistent / private | `dogfood_safety._REFUSING_CLASSES`                    |
| Preflight does NOT read input file contents                     | `test_classify_does_not_read_file_contents`             |
| Preflight does NOT invoke LLM factory                           | `test_cli_dogfood_preflight_does_not_invoke_llm`        |
| `human_approved` only via `approver.approve_card`               | `test_human_approved_promotion_requires_explicit_approve_card_call` |
| Custom-strategy preview is non-executable                       | v0.12 declarative strategy guarantee                   |

## 3. Provider Boundary Gates

| Module                  | Allowed imports                              | Forbidden imports                                                        |
|-------------------------|----------------------------------------------|--------------------------------------------------------------------------|
| `provider_readiness.py` | std-lib, `config`                            | cli, approval_*, writer, cards, obsidian*, cubox*, scanner, dotenv, network |
| `real_smoke.py`         | std-lib, `config`, `llm.factory`             | cli, approval_*, writer, cards, obsidian*, cubox*, scanner, dotenv, network |
| `provider_cli.py`       | typer, `app_context`, `env_loader` (allowlisted), readiness, smoke | cli, approval_*, writer, cards, obsidian*, cubox*, scanner, network    |
| `dogfood_safety.py`     | std-lib, `provider_readiness`                | cli, approval_*, writer, cards, obsidian*, cubox*, scanner, dotenv, network |

All enforced by `tests/test_v013_cli_provider_surface.py` (AST walk).

## 4. Dogfooding Gates

- `mindforge dogfood plan` — static checklist (no execution)
- `mindforge dogfood preflight <path>` — static decision (no file read,
  no LLM, no write)
- Real dogfood must be run **manually** by the user, command-by-command,
  using the `dogfood plan` checklist + a disposable copy of their
  vault. Tooling does not auto-loop.

## 5. Approval Gates

- `human_approved = True` is set **only** inside `approver.approve_card`
- `approver.approve_card` requires explicit human invocation (CLI
  `approve` command with confirmation flow)
- Real-smoke / preflight / readiness paths cannot reach
  `approve_card`; AST guard prevents the import path
- Auto-approve path: not implemented; not in roadmap

## 6. Known Limitations (v0.13)

- Real Cubox API ingestion: deferred to a future gate
- Real Obsidian formal-note write: deferred to a future gate
- `human_approved` UX is still CLI-only, no web/TUI surface
- Custom strategy runtime is declarative-preview only (no execution)
- `--declare-non-sensitive` is user-asserted; no content scan to verify
  truthfulness (by design — content scan would be a boundary violation)

## 7. Manual Smoke Performed (in this session)

| Smoke                                                         | Result                                       |
|---------------------------------------------------------------|----------------------------------------------|
| `mindforge provider readiness --config configs/mindforge.yaml`| `fake-default` reported (Stage 1)            |
| `mindforge provider smoke` (no flag)                          | refused with `blocker` (Stage 1)             |
| `mindforge provider smoke --allow-real --profile anthropic_coding_plan` | DashScope qwen, 44/72 tokens, 1434ms (Stage 3) |
| `mindforge dogfood preflight examples/demo-vault`             | `synthetic` → allowed, exit 0 (Stage 4)      |
| `mindforge dogfood preflight <obsidian path> --declare-non-sensitive` | refused, exit 2 (Stage 4)            |

## 8. Rollback

- Every Stage 1–4 change is in a single, git-revertable cohesive commit
  series (no rebase, no force, no tag).
- Reverting all v0.13 changes is `git revert <range>` against the
  current HEAD.
- No schema migration, no config breaking change, no dependency update.

## 9. Future Gates (NOT in v0.13)

| Capability                            | Required gate before implementation                          |
|---------------------------------------|--------------------------------------------------------------|
| Real Cubox ingestion                  | sample-folder + item-cap + dry-run-first + no-persist        |
| Real Obsidian write                   | per-write explicit confirmation + diff preview + dry-run     |
| Auto-approval workflow                | not planned; would require permanent design review            |
| Custom executable strategy runtime    | sandbox design + capability-based permissions                 |
| RAG / embedding / semantic merge      | separate design milestone with privacy-impact assessment      |
| Public release / git tag              | explicit human authorization + CHANGELOG freeze + tag review |

## 10. Verdict

v0.13 is **locally stage-complete and RFC-ready**. **No tag and no
release have been created.** A tag/release decision is **explicitly
deferred** to human authorization (G6 future gate); this pack provides
the evidence trail that decision would consult.
