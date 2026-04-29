# v0.7.10 CLI / Service Boundary Cleanup

## Goal

Continue reducing Obsidian-related decision logic in `src/mindforge/cli.py` without changing commands or enabling formal Obsidian note writes.

## Extracted

- Added structured `DiffPreviewPlan` for staged-only diff preview data.
- Added structured `PreflightDisplayPlan` for PASS / BLOCKED / WARNING next-action decisions.
- Added structured `ObsidianNextPlan` and dogfooding command rows for `obsidian next`.
- Moved first Markdown hint lookup into the Obsidian stage service.

## CLI Now Keeps

- Typer command options and exit-code handling.
- Rich/table rendering and human-facing wording.
- Staged export file writes inside the staged directory only.
- Preflight command shape and existing output semantics.

## Behavior Kept

- `obsidian stage`, `obsidian preflight`, and `obsidian next` keep the same external command flow.
- `preflight` still exits `2` only for BLOCKED.
- Diff preview remains staged-only.
- `obsidian next` remains navigation only and does not execute commands.

## Still Not Extracted

- Obsidian scan / links / doctor presentation.
- Daily `start` / `today` / `next` heuristics.
- Backup/export payload shaping.
- Large historical test file split.

## Safety Boundary

v0.7.10 remains local-only and no-write for formal Obsidian notes. It does not read `.env`, call real LLMs, upload telemetry, auto-approve cards, apply staged files back to a vault, or add RAG, embedding, plugin, Web UI, or TUI behavior.
