# v0.7.11 Main Code Monolith Decomposition Plan

## Current Conclusion

`src/mindforge/cli.py` is still a serious CLI monolith at 5,784 lines. The core architecture is still healthy because processors, adapters, approval, recall, and Obsidian services do not depend on CLI, but the main code has become harder to read because command entry, orchestration, safety policy, Rich rendering, empty-state copy, and some use-case decisions still live in one file.

Main code should be decomposed before test-file cleanup because `cli.py` is the production coupling point. Large tests are noisy, but they are currently a useful safety net; a 5,784-line CLI file slows every future feature and makes boundary mistakes more likely.

This plan is recorded as v0.7.11 because the repository already has `v0.7.10` tagged for the Obsidian preflight service-helper extraction.

## `cli.py` Responsibility Map

| responsibility | current location | evidence / risk |
| --- | --- | --- |
| Typer app registration | top-level app setup, `llm_app`, `backup_app`, `config_app`, `dogfood_app`, `approve_app`, `review_app`, `project_app`, `index_app`, `vault_app`, `obsidian_app`, `telemetry_app` | This can stay in CLI. |
| Parameter parsing and defaults | all command functions, especially `process`, `recall`, `obsidian_stage`, `init`, `doctor`, `next_cmd` | CLI-owned, but defaults often sit beside business decisions. |
| Config loading / path resolution | `_load_cfg`, `_apply_global_vault_override`, `_override_active_profile`, `_obsidian_options`, `_daily_snapshot`, `_config_ux_payload` | Should move gradually to an app context helper. |
| Rich / console rendering | most commands call `console.print`, `Table`, `print` directly | Presentation is mixed with business branching. |
| commands / start / today / next onboarding | `commands_cmd`, `_daily_snapshot`, `_next_suggestions`, `_print_daily_snapshot`, `_print_next_actions`, `start_cmd`, `today_cmd`, `next_cmd` | `_next_suggestions` is 195 lines and mixes state reads, YAML peeks, path checks, and suggested commands. |
| process / provider / fake profile orchestration | `process` | 279 lines; config/profile override, provider construction, pipeline execution, checkpoint writes, card writes, telemetry, output. |
| approve / review / recall orchestration | `approve`, `approve_list`, `review_due`, `review_schedule`, `review_weekly`, `recall`, `_do_bm25_recall` | `_do_bm25_recall` is 322 lines; `recall` is 204 lines. Search result shaping and output should be separated. |
| backup / export | `backup_export`, `_build_review_schedule_export`, `_write_json` | 90-line command builds manifest/payload and writes files. Good candidate for backup service. |
| Obsidian doctor / scan / links | `obsidian_doctor`, `obsidian_scan`, `obsidian_links`, `_print_obsidian_issues` | Domain scan logic is in `obsidian.py`; presentation remains in CLI. This is acceptable short-term. |
| Obsidian stage dry-run | `obsidian_stage`, `_print_stage_preview`, `_stage_preview_fields` | `obsidian_stage` is 183 lines and still contains validation branches plus rendering. |
| Obsidian staged export | `_write_obsidian_staged_export`, `obsidian_stage`, `obsidian_stage.py` | v0.7.9 moved path/manifest helpers out; CLI still owns staged file write and output. Good boundary for now. |
| Obsidian diff preview | `_print_staged_diff_preview`, `build_staged_diff_preview_plan` | v0.7.10 moved diff data plan to service; CLI renders it. |
| Obsidian preflight | `obsidian_preflight_cmd`, `obsidian.py`, `build_preflight_display_plan` | Validation lives in service; CLI still renders table and exit. |
| Obsidian next / dogfooding | `obsidian_next`, `_obsidian_dogfood_command_snippets`, `build_obsidian_next_plan` | v0.7.10 moved status calculation and snippets into service, but CLI still has compatibility wrapper. |
| Safety guard / no-write / no-env / no-real-LLM copy | scattered in `doctor`, `setup_cmd`, `config_init`, `dogfood_plan`, Obsidian commands, recall summary | Needs `safety_policy.py` for named policy facts and user-facing canonical lines. |
| Manifest / path / vault boundaries | `obsidian_stage.py`, `obsidian.py`, `_obsidian_options`, `_doctor_paths`, `_daily_snapshot`, `_next_suggestions` | Obsidian path safety is improving; daily/config path checks still scattered. |
| Error handling / empty states | most command functions | Product copy is useful but tightly coupled to implementation branches. |
| Cross-command helpers | `_card_to_safe_dict`, `_safe_date`, recall helpers, doctor helpers, config helpers, daily helpers | These are service/presenter candidates once command groups are clearer. |

## Large Functions

Over 300 lines:

- `_do_bm25_recall` 322 lines: recall service + ranking + JSON/Markdown/table rendering.

Over 150 lines:

- `process` 279 lines: provider/pipeline/checkpoint/card-write/output in one command.
- `doctor` 222 lines: runtime/config/vault/safety/recovery rendering and policy checks.
- `recall` 204 lines: card loading, filtering, output modes, telemetry.
- `_next_suggestions` 195 lines: daily workflow use-case plus YAML/file peeking.
- `obsidian_stage` 183 lines: validation, adapter load, stage plan, output.
- `project_context` 166 lines: context assembly and rendering.
- `init` 160 lines: interactive flow, planning, execution, output.

80-150 lines:

- `review_weekly` 144 lines.
- `review_schedule` 111 lines.
- `scan` 103 lines.
- `_do_index_status` 103 lines.
- `approve_list` 93 lines.
- `backup_export` 90 lines.
- `review_due` 87 lines.
- `approve` 86 lines.
- `project_update_evidence` 85 lines.
- `llm_ping` 84 lines.

## Coupling Hotspots

Functions mixing business decisions and Rich output:

- `_do_bm25_recall`, `recall`, `process`, `doctor`, `_next_suggestions`, `obsidian_stage`, `review_weekly`, `review_schedule`, `approve_list`, `backup_export`.

Functions mixing path safety, file writes, and user prompts:

- `process`: state/checkpoint/card writes plus output.
- `backup_export`: export path creation, payload construction, manifest write, summary output.
- `obsidian_stage`: vault/source validation, staged write path, staged file write, user warning.
- `init`: target validation, template writes, interactive prompts, output.
- `review_schedule`: schedule calculation and optional output file writes.

Priority to split:

1. `_do_bm25_recall` and `recall` because recall is core user workflow and already has service modules to call.
2. `process` because v0.8 real LLM opt-in will otherwise land in a 279-line command.
3. `_next_suggestions` / daily helpers because they are pure local workflow logic and easy to service-test.
4. `doctor` because safety policy and presentation are heavily mixed.
5. `backup_export` because payload/manifest building can become a focused service.

Do not touch first:

- Typer app creation and command names.
- SourceAdapter / SourceDocument / processor / approval / recall contracts.
- Existing Obsidian write-gate semantics.
- Large test-file structure, until main code boundaries are clearer.

## Target Module Boundaries

### `mindforge/cli.py`

Keeps Typer app, command parameters, exit-code mapping, calls into services, and calls presenter functions. It may depend on Typer and Rich.

Must not own long use-case algorithms, manifest payload decisions, safety policy definitions, or complex path scans.

### `mindforge/app_context.py`

Future candidate. Builds console-independent command context: loaded config, global vault override, resolved state paths, active profile override, optional repo/project root facts.

Must not depend on Typer or Rich. Can be service-tested directly.

### `mindforge/obsidian_stage.py`

Already exists. Owns staged export plan, manifest payload, staged-only diff plan, source/vault helper, Obsidian next plan, and dogfooding command rows.

Must not depend on CLI, Typer, or Rich. Must not write formal Obsidian notes.

### `mindforge/obsidian_preflight.py`

Future candidate if `obsidian.py` grows too broad. Would own manifest loading, PASS/BLOCKED/WARNING aggregation, forbidden derived path checks, and future write-gate policy.

Must not depend on CLI, Typer, or Rich. Must not execute writes.

### `mindforge/obsidian_workflow.py`

Future candidate only if `obsidian_stage.py` becomes too mixed. Would own `obsidian next`, dogfooding path, and workflow status.

Must not run commands or write files.

### `mindforge/cli_presenters.py`

Future candidate. Owns Rich rendering for scan/status/recall/review/Obsidian tables.

May depend on Rich, but should not load config, read cards, write files, or decide business status.

### `mindforge/safety_policy.py`

Future candidate. Owns named safety facts: no formal notes, no `.env`, no real LLM, no telemetry upload, no RAG/embedding/plugin, forbidden runtime/cache/index/log/sqlite/vector/graph path parts.

Must not depend on CLI, Typer, or Rich.

### `mindforge/backup_export.py`

Future candidate. Owns backup manifest and payload building. CLI handles options and rendering.

Must not upload, read `.env`, or include source raw text.

### `mindforge/daily.py`

Future candidate. Owns `DailySnapshot` and `NextSuggestion` calculation.

Must not depend on Rich/Typer; can read local state/cards/index paths via config.

### `mindforge/commands/`

Do not create yet. Splitting by command modules is a later step after service and presenter boundaries are clearer.

## Decomposition Route

### v0.7.11: Main code decomposition plan

- Split: no code slice unless a trivial helper appears.
- Why first: avoid continuing feature work with no shared map.
- Risk: low.
- Tests: full ruff/pytest only.
- Expected `cli.py` reduction: 0 lines.
- Behavior unchanged: all commands.
- Do not touch: tests, command names, core contracts.

### v0.7.12: Recall service extraction

- Split: extract recall result shaping and BM25/hybrid presentation-neutral payload planning from `_do_bm25_recall` and `recall`.
- Why: `_do_bm25_recall` is the largest function at 322 lines and recall is a core daily workflow.
- Risk: medium.
- Tests: existing recall CLI tests plus new service-level tests for no-result action, summary, hit payloads, include-drafts, no RAG/no LLM boundary.
- Expected `cli.py` reduction: 250-400 lines.
- Behavior unchanged: `mindforge recall` output modes and local lexical boundary.
- Do not touch: lexical scoring internals unless needed for dependency injection.

### v0.7.13: Process workflow extraction

- Split: move provider/profile/pipeline/checkpoint/card-write orchestration into a `process_workflow.py` service returning structured outcomes.
- Why: v0.8 real LLM opt-in should not land inside a 279-line CLI command.
- Risk: medium-high.
- Tests: process fake smoke, ai_draft write behavior, no auto approve, no `.env` for fake profile, checkpoint/state writes.
- Expected `cli.py` reduction: 180-300 lines.
- Behavior unchanged: fake provider default, output semantics, card statuses.
- Do not touch: SourceAdapter, SourceDocument, Pipeline stage contracts.

### v0.7.14: Daily workflow extraction

- Split: move `DailySnapshot`, `_daily_snapshot`, `_next_suggestions`, `_compact_next_suggestions`, start/today/next data shaping into `daily.py`.
- Why: `_next_suggestions` is 195 lines of pure local workflow logic and can be directly service-tested.
- Risk: medium.
- Tests: start/today/next CLI tests plus service tests for empty state, ai_draft, human_approved, index missing, Obsidian dogfooding suggestions.
- Expected `cli.py` reduction: 250-400 lines.
- Behavior unchanged: onboarding commands and safety text.
- Do not touch: actual command names or global `--vault` normalization.

### v0.7.15: Safety policy extraction

- Split: move canonical no-write/no-env/no-real-LLM/no-telemetry/no-RAG/plugin facts and forbidden derived path names into `safety_policy.py`.
- Why: safety copy and policy facts are scattered across doctor, setup, config, recall, and Obsidian paths.
- Risk: low-medium.
- Tests: policy unit tests and existing no `.env` / no real LLM / no write CLI tests.
- Expected `cli.py` reduction: 80-180 lines plus less duplicated copy.
- Behavior unchanged: safety boundaries remain visible.
- Do not touch: actual write-gate enablement.

### v0.7.16: Backup/export service extraction

- Split: move backup manifest, safe card export, state summary, review schedule payload into `backup_export.py`.
- Why: `backup_export` mixes file layout, payload safety, manifest construction, and rendering.
- Risk: medium.
- Tests: export smoke, manifest content, no `.env`, no source raw text, local-only path behavior.
- Expected `cli.py` reduction: 120-220 lines.
- Behavior unchanged: backup directory contents and safety manifest.
- Do not touch: recovery apply/restore features.

### v0.7.17: CLI presenters

- Split: move table rendering for recall/review/Obsidian/status into `cli_presenters.py`.
- Why: after services return structured data, presentation can move without moving business logic.
- Risk: medium.
- Tests: selected CLI snapshot/fragments only for user behavior, service tests for data.
- Expected `cli.py` reduction: 300-600 lines.
- Behavior unchanged: command output semantics.
- Do not touch: Typer command registration.

### v0.7.18: Test boundary cleanup

- Split: only then split large historical test files by behavior area.
- Why: after main code boundaries exist, tests can target service/presenter/CLI layers cleanly.
- Risk: medium.
- Tests: full suite.
- Expected `cli.py` reduction: 0 lines.
- Behavior unchanged: all commands.
- Do not touch: product behavior.

## This Round

No code slice was made in this round. The repository already had a fresh v0.7.10 code extraction, and the safer move is to freeze a main-code decomposition map before cutting into recall/process/daily workflow. That avoids accidental large rewrites disguised as cleanup.

## Do Not Do

- Do not enter v0.8 Real LLM Opt-in yet.
- Do not build RAG, embeddings, an Obsidian plugin, Web UI, or TUI.
- Do not write formal Obsidian notes.
- Do not auto-approve.
- Do not upload telemetry.
- Do not prioritize splitting large test files before main code boundaries are clearer.
