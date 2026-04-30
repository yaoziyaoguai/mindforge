# v0.7.14 Obsidian Workflow Service

## Goal

Move Obsidian dogfooding / next-action planning into a dedicated service module without adding new Obsidian behavior.

## Extracted

- Added `src/mindforge/obsidian_workflow.py`.
- Moved `ObsidianNextPlan`, dogfooding command snippets, and next-action planning out of staged-export helpers.
- `obsidian next` now renders a structured plan instead of owning the workflow decisions.

## Boundaries

- `obsidian_workflow`: reads directory state and returns next-action data.
- `obsidian_stage`: staged export, manifest, diff, and path helpers.
- `cli.py`: Typer parameters and user-facing rendering.

`obsidian_workflow` must not depend on Typer/Rich, read `.env`, call LLMs, do RAG/embedding, create directories, or write formal Obsidian notes.

## Behavior Kept

- `mindforge obsidian next` command and wording remain semantically unchanged.
- Flow still stops at dry-run / staged export / diff / preflight / manual inspection.
- No apply/write-back/plugin behavior exists in this version.

## Still Not Extracted

- Obsidian doctor/scan/links rendering remains in `cli.py`.
- Stage dry-run rendering remains in `cli.py`.
- App config/path context remains in `cli.py`.
