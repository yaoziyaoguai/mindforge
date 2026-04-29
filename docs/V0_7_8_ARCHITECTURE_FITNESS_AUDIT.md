# v0.7.8 Architecture Fitness Audit

## Current Conclusion

**中度 CLI 巨石化。**

Evidence: `src/mindforge/cli.py` is 5,937 lines, over 8x the next largest source file. It owns Typer command declarations, command orchestration, Rich rendering, daily `next` heuristics, backup export wiring, Obsidian staged export helpers, diff preview, path helpers, dogfooding flow text, and multiple safety messages. Core domain direction is still healthy: processors/adapters do not import CLI, Obsidian service logic lives partly in `src/mindforge/obsidian.py`, fake LLM remains default, and tests strongly protect no-write/no-env/no-real-LLM behavior.

## Top 10 Largest Files

| file | lines | risk | split? |
| --- | ---: | --- | --- |
| `src/mindforge/cli.py` | 5,937 | high | yes, incrementally |
| `tests/test_v0_5_obsidian.py` | 1,164 | medium | yes, later |
| `tests/test_v0_4_2.py` | 1,004 | medium | yes, later |
| `src/mindforge/config.py` | 729 | low-medium | not urgent |
| `src/mindforge/lexical_index.py` | 725 | low-medium | not urgent |
| `tests/test_v0_2_3.py` | 672 | medium | later |
| `tests/test_m5_3.py` | 554 | medium | later |
| `src/mindforge/obsidian.py` | 513 | low-medium | keep service-focused |
| `tests/test_m4.py` | 479 | medium | later |
| `src/mindforge/project_context.py` | 475 | low | no |

## Current Module Boundary

Good:

- `processors/` does not depend on CLI.
- Source adapters do not depend on CLI.
- `src/mindforge/obsidian.py` has pure local logic for scan scope, document loading, links, stage markdown, doctor rows, and preflight.
- `approver.py`, `reviewer.py`, `lexical_index.py`, `cards.py`, `vault.py`, `project_context.py`, and `telemetry.py` are service/domain modules with focused APIs.
- Tests repeatedly assert no `.env`, no real LLM, no network, no formal Obsidian note writes, no RAG/plugin claims.

Worse:

- `cli.py` owns too many command families and local helpers.
- Obsidian staged export, diff preview, filename uniqueness, formal-conflict scanning, and dogfooding snippets still live in `cli.py`.
- Rich output text and use-case decisions are often adjacent in the same function.
- Safety wording is repeated across commands instead of centralized as named policy helpers.
- Test files are version-bucketed and large; some tests assert exact output fragments, which makes presentation refactors brittle.

## `cli.py` Responsibility Analysis

Can stay in CLI:

- Typer app/subcommand declarations.
- CLI option parsing and exit-code mapping.
- Rich/Table rendering adapters.
- Thin calls into services/use-cases.

Should move out over time:

- Obsidian staged export manifest construction and unique path selection.
- Obsidian diff/preflight/dogfooding command plan data.
- Daily `start/today/next` snapshot and suggestion heuristics.
- Backup export payload construction.
- Recall output data shaping that is not purely Rich presentation.
- Repeated safety boundary strings and path policy checks.

## Obsidian Integration Boundary

Domain/use-case:

- `ObsidianScanOptions`, scope matching, document loading, link entries, stage markdown, doctor rows, and `obsidian_preflight`.

CLI presentation:

- Rich tables for scan/links/stage/preflight/doctor.
- Human next-step wording and dogfooding flow display.

Safety policy:

- No formal note writes, no `.env`, no real LLM, no telemetry upload, no runtime/cache/index/log/sqlite/vector/graph paths.
- Some policy is centralized in `obsidian.py`; some is repeated in `cli.py` text and staged export manifest creation.

Dogfooding helper:

- `_obsidian_dogfood_command_snippets` and `obsidian next` are currently CLI-local. This is acceptable for now, but should become a pure plan builder if it grows.

## Recommended Refactor Route

P0: must fix first

- Do not start v0.8 with more feature code in `cli.py`.
- Preserve current tests before extraction; do not weaken behavior assertions.

P1: v0.7.9 small cleanup

- Extract `mindforge/obsidian_export.py`: export filename, unique staged path, manifest payload, formal conflict detection.
- Add service-level tests for manifest payload and no-overwrite behavior.
- Keep CLI command names and output semantics unchanged.

P2: before v0.8

- Extract `mindforge/daily.py`: `DailySnapshot`, start/today/next suggestions.
- Extract `mindforge/backup_export.py`: export payload building.
- Move Obsidian dogfooding plan into a pure helper returning command rows.

P3: later

- Split tests by behavior area rather than historical version buckets.
- Consider small presentation modules only if Rich rendering keeps growing.
- Avoid framework-level command architecture until real pain appears.

## Do Not Do

- Do not do a large `cli.py` rewrite.
- Do not introduce a new framework or dependency.
- Do not change SourceAdapter, SourceDocument, processor, approval, or recall contracts.
- Do not build an Obsidian plugin, Web UI, RAG, embedding layer, or real-LLM default path.
- Do not touch real Obsidian notes or add formal-note write capability.
