# v0.7.13 CLI Presenter Extraction

## Goal

Extract the recall output rendering path from `cli.py` without changing CLI commands or recall behavior.

## Extracted

- Added `src/mindforge/recall_presenter.py`.
- Moved recall JSON / markdown / table / compact rendering out of `_do_bm25_recall`.
- Kept `cli.py` responsible for Typer parameters, config loading, RunLogger, and calling `recall_service`.

## Boundaries

- `recall_service`: BM25 / hybrid recall, ranking, filtering, explain data.
- `recall_presenter`: Rich / JSON / Markdown rendering only.
- `cli.py`: command entrypoint and orchestration.

`recall_presenter` may depend on Rich, but it must not read files, parse config, call LLMs, do embedding/RAG, or write Obsidian notes.

## Behavior Kept

- `mindforge recall` command shape is unchanged.
- JSON schema remains versioned as before.
- Markdown/table/compact output keeps the same user-facing meaning.
- no-result and explain output still use the structured recall result.

## Still Not Extracted

- Other command presenters remain in `cli.py`.
- Obsidian next/dogfooding workflow rendering remains in `cli.py`.
- app config/path resolution remains in `cli.py`.
