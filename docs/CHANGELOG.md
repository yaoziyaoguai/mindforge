# MindForge Changelog

This file summarizes user-visible and architecture-relevant changes. Detailed historical reviews live in `docs/archive/`.

## v0.5.0

- Added read-only `ObsidianVaultSourceAdapter` with `source_type: obsidian_note`.
- Added `mindforge obsidian doctor`, `scan`, `links`, and `stage`.
- Added Obsidian config for vault path, staging/review dirs, include/exclude dirs, and `read_only`.
- Added staging bridge with dry-run default and `--write --confirm` guard.
- Kept Obsidian runtime/state/cache/index/log boundaries explicit: no formal-note edits, file moves, wikilink rewrites, RAG, vector DB, graph DB, or plugin.

## v0.4.3

- Added `mindforge init --interactive`.
- Polished `doctor` and `next` output with sections, status markers, priorities, and JSON schema `version=2`.
- Chinese-localized more user-facing errors.
- Added executable onboarding smoke coverage for `examples/demo-vault/`.

## v0.4.2

- Added `mindforge commands`.
- Added `mindforge next`.
- Formalized [SourceAdapter Protocol](./SOURCE_ADAPTER_PROTOCOL.md).
- Added `SourceDocument.adapter_name`.
- Added fictional `examples/demo-vault/`.

## v0.4.1

- Added iCal export for review schedules.
- Added weekly review reports.
- Added first versions of `GETTING_STARTED.md`, `USER_GUIDE.md`, and `ROADMAP_PROGRESS.md`.

## v0.4.0

- Added review scheduling MVP: schedule, backlog, stats, and `review mark --dry-run --note`.

## v0.3.x

- Added local BM25 recall.
- Added local hybrid ranking.
- Added configurable BM25/hybrid weights and config drift detection.
- Added index info JSON and recall explain improvements.

## v0.2.x

- Added review due, recall, and project context.
- Added multi-project context and project evidence block updates.
- Added local-only telemetry.
- Added WebClip and ChatExport adapters.
- Added PDF/docx text adapters with lazy optional dependencies and no OCR.
- Added `mindforge init`, approval workflow polish, doctor, and global `--vault`.

## v0.1.x

- Built the main source ingestion and five-stage processing pipeline.
- Added fake, OpenAI-compatible, and Anthropic-compatible provider layers.
- Added Knowledge Card writing and explicit human approval safety gate.
- Established the core protocol, state, runs, and safety boundaries.
