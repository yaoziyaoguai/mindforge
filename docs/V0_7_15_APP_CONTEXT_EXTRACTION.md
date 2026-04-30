# v0.7.15 App Context Extraction

## Goal

Extract the lowest-risk config/path resolution helper from `cli.py` so command entrypoints do not each own config loading and vault override behavior.

## Extracted

- Added `src/mindforge/app_context.py`.
- Added `load_app_config`, `apply_vault_override`, and `build_app_context`.
- `_load_cfg` in `cli.py` now delegates config loading and vault override to app context while keeping the same CLI error wording.

## Boundaries

- `app_context`: config loading, vault override, resolved path snapshot.
- `cli.py`: decides whether to load `.env`, maps structured errors to Typer exit and Rich output.
- service modules: continue to consume already-loaded config and must not parse CLI state.

`app_context` does not depend on Typer/Rich, does not read `.env`, does not call LLMs, and does not write files.

## Behavior Kept

- Existing `--config` and global `--vault` behavior remains unchanged.
- Commands still use the same config format.
- No command names or user-facing semantics changed.

## Still Not Extracted

- Many commands still call `_load_cfg` from `cli.py`.
- Daily `start/today/next` snapshot logic remains in `cli.py`.
- Further cleanup can move more repeated path/status helpers into app context after service boundaries are stable.
