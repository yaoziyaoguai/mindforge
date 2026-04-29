# v0.7.9 CLI / Service Boundary Cleanup

## Goal

Reduce `src/mindforge/cli.py` responsibility without changing CLI commands or enabling Obsidian writes.

## Extracted

- Added `src/mindforge/obsidian_stage.py`.
- Moved staged export filename planning, unique staged path selection, staged export directory resolution, formal same-name conflict detection, and manifest payload construction out of CLI.
- Added service-level tests for manifest evidence, no-overwrite behavior, path safety, preflight aggregation, and no `.env` / no real LLM / no formal note writes.

## CLI Now Keeps

- Typer options and exit codes.
- Rich/table rendering and user-facing wording.
- Staged markdown + manifest file writes inside the staged export directory only.
- Diff preview rendering.

## Still Not Extracted

- `obsidian next` and dogfooding flow presentation.
- Daily `start` / `today` / `next` suggestions.
- Backup/export payload shaping.
- Large historical test files.

## Safety Boundary

v0.7.9 is still dry-run / staged-export / preflight only. It does not write formal Obsidian notes, does not apply changes back to a vault, does not read `.env`, does not call a real LLM, does not upload telemetry, and does not add RAG, embedding, plugin, Web UI, or TUI behavior.
