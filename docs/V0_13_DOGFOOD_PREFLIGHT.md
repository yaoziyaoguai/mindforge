# v0.13 Stage 4 — Controlled Dogfood Preflight

> Status: **delivered (local)**, fake-default still default, no real run is
> initiated by this command. Companion to
> [`V0_13_REAL_LLM_SMOKE_SAFETY.md`](./V0_13_REAL_LLM_SMOKE_SAFETY.md).

## Why

Stage 3 wired up real LLM smoke end-to-end. The next risk is **input**:
nothing in the existing CLI told a user "this path is your home / your
real Obsidian vault / a real Cubox dump — refuse." `mindforge dogfood
plan` only prints a static command checklist; it cannot answer the
runtime question "is *this* input safe right now?".

Stage 4 adds a tiny, **purely static** preflight that classifies the
input path and combines it with provider readiness, then yields an
allowed/refused decision — *without ever reading the input contents,
calling an LLM, or writing anything*.

## What it is

`mindforge dogfood preflight <path>` — new sub-command, ~30 LOC of glue
in `cli.py`, all logic in `src/mindforge/dogfood_safety.py`.

```bash
mindforge dogfood preflight examples/demo-vault
mindforge dogfood preflight ./scratch/mynote.md --declare-non-sensitive
mindforge dogfood preflight examples/demo-vault --allow-real
```

### Decision rules (priority order)

| # | Condition                                                      | Classification                  | Decision  |
|---|----------------------------------------------------------------|---------------------------------|-----------|
| 1 | Path does not exist                                            | `path_does_not_exist`           | refused   |
| 2 | Under `examples/demo-vault` or `examples/custom-strategies`    | `synthetic`                     | allowed   |
| 3 | Self / parent named `.obsidian`, or parent contains `.obsidian/` | `obsidian_vault_forbidden`      | refused   |
| 4 | Under `Path.home()` and not under `Path.cwd()`                 | `home_scan_forbidden`           | refused   |
| 5 | `--declare-non-sensitive` and rules 1–4 not matched            | `non_sensitive_local`           | allowed   |
| 6 | Otherwise                                                      | `private_real_data_forbidden`   | refused   |

`--allow-real` only adds a blocker if `provider readiness` cannot reach
`opt_in_state == "ready"`; it never initiates a network call.

### Permanent output contract

Every report — allowed or refused — carries:

- `output_contract.artifact_type` ∈ {`review_packet`, `preflight_refusal`}
- `output_contract.writes_vault = False`
- `output_contract.writes_cards = False`
- `output_contract.approves     = False`
- `output_contract.human_approved = False`

These are documentation **of what this command will not do**, not
runtime switches.

## What it is not

- Not an automated dogfood runner (the `dogfood plan` checklist is the
  manual runner).
- Not a content classifier — it never reads file contents.
- Not a real-LLM call — `--allow-real` only asks readiness "would real
  be reachable?".
- Not a substitute for human review of the actual draft cards.

## Hard architectural boundaries (enforced by tests)

`dogfood_safety.py` does **not** import:

- `cli`, `approval_service`, `approver`, `approve_presenter`
- `writer`, `cards`, `process_service`, `processors`
- `review_service` / `review_presenter`, `recall_*`
- `obsidian*`, `cubox_*`, `scanner`
- `dotenv`, `requests`, `httpx`, `subprocess`, `env_loader`

Guarded in `tests/test_v013_cli_provider_surface.py` (`_GUARDED` list)
and `tests/test_v013_stage4_dogfood_preflight.py`
(`test_classify_does_not_read_file_contents`,
`test_cli_dogfood_preflight_does_not_invoke_llm`).

## Quality gates

- `1257 passed, 3 skipped`
- `ruff check .` clean
- `git diff --check` clean
- Sensitive-token sweep on new file: no `cat .env`, no api_key prints,
  no `Path.home()` *iteration*, no network imports.

## Future gates (still deferred)

- Real Cubox ingestion → still requires its own opt-in gate proposal.
- Real Obsidian write → still requires explicit per-write confirmation.
- `human_approved` promotion → still only via `approver.approve_card`
  with explicit human invocation.
