# v0.7.12 Recall Service Extraction

## Goal

Move query-path recall / BM25 / hybrid result shaping out of `src/mindforge/cli.py` while keeping CLI commands and output semantics unchanged.

## Why Recall

`_do_bm25_recall` was the largest function in `cli.py` at about 322 lines. Recall is also a daily core workflow, so keeping BM25 ranking, explain payloads, empty-state decisions, and output rendering in one command made future changes risky.

## Extracted

- Added `src/mindforge/recall_service.py`.
- Moved BM25 index selection, memory rebuild decisions, hybrid weight validation, BM25/hybrid search execution, local card stats, safe hit shaping, matched-term extraction, explain payload shaping, and recall next-action text into service-level helpers.
- CLI now loads config, parses Typer options, logs local run metadata, and renders existing output formats.

## Service Boundary

`recall_service` does not depend on Typer, Rich, console, LLM providers, `.env`, embeddings, RAG, telemetry upload, or Obsidian. It reads local Knowledge Card safe fields and optional local BM25 index data, then returns structured results.

## Behavior Kept

- `mindforge recall --query ...` command shape is unchanged.
- `--include-drafts`, `--limit`, `--explain`, `--ranking bm25|hybrid`, and hybrid weight overrides keep their existing semantics.
- JSON, markdown, table, and compact outputs keep the same user-facing meaning.
- Query plaintext remains out of local run logs.
- Recall remains local lexical search only: no RAG, no embedding, no LLM, no `.env`, no upload.

## Still Not Extracted

- Non-query M4 recall filtering path.
- Recall Rich/table presenter functions.
- App context / config-path loading.
- Safety policy constants shared across commands.

## Next Candidates

- v0.7.13 CLI presenter extraction.
- v0.7.13 app context extraction.
- v0.7.13 safety policy consolidation.
