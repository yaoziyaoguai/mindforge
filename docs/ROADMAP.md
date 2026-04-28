# MindForge Roadmap

This roadmap tracks product direction and explicit non-goals. Completed release details are summarized in [CHANGELOG.md](./CHANGELOG.md); current completion state is in [ROADMAP_PROGRESS.md](./ROADMAP_PROGRESS.md).

## Current Position

Current version: **v0.5.0**.

MindForge v0.x is a local-first CLI for personal learning memory:

- local source ingestion through adapters;
- five-stage LLM processing with safe fake default;
- explicit human approval;
- local lexical/hybrid recall;
- local review planning;
- project context packs;
- local-only telemetry;
- CLI onboarding and demo vault.
- read-only Obsidian Binding / Bridge.

## Completed v0.4.3 Follow-Up

The docs cleanup after v0.4.3 is complete: active docs were consolidated into
user, developer, roadmap, changelog, and archive layers. Historical milestone
reviews and superseded design notes now live under `docs/archive/`.

## v0.5 Completed

v0.5 implements the minimal safe Obsidian bridge:

- configure an Obsidian vault path;
- scan Markdown read-only;
- parse frontmatter, tags, `[[wikilinks]]`, and directory structure;
- introduce `ObsidianVaultSourceAdapter` in the SourceAdapter system;
- add `mindforge obsidian doctor|scan|links|stage`;
- write candidate output only to Obsidian staging/review;
- never modify real vault source notes in the first phase;
- keep machine indexes, caches, runtime logs, and intermediate state in derived
  layers such as `.mindforge/`, SQLite, vector stores, or graph stores rather
  than formal Obsidian notes.

## Near-Term Priority

Next: validate v0.5 on a small, non-sensitive Obsidian sample with dry-run first.
Do not start broad real-vault dogfooding until include/exclude rules,
staging/review location, and source-note preservation have been checked.

## Future Candidate Work

See [M5_BACKLOG.md](./M5_BACKLOG.md) for current spike candidates. The active future set is intentionally small:

- Obsidian Binding polish from dry-run feedback.
- PDF/docx performance baselines.
- More onboarding and cross-platform terminal polish.
- RAG / embedding only as a later design spike if lexical recall proves
  insufficient after Obsidian binding.

## Explicit Non-Goals For v0.x

- No OCR.
- No remote telemetry.
- No cloud sync.
- No automatic approval.
- No background daemon.
- No system calendar or notification integration.
- No SM-2 / FSRS automation.
- No RAG/embedding in mainline without a separate design and review.
- No graph database or vector database implementation in v0.5.
- No automatic Obsidian vault reorganization.
- No automatic formal-note edits, file moves, or wikilink rewrites.
- No large-scale real-vault dogfooding before read-only Obsidian binding is
  designed and tested.

## Stable Architecture References

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [SECURITY.md](./SECURITY.md)
- [MINDFORGE_PROTOCOL.md](./MINDFORGE_PROTOCOL.md)
- [SOURCE_ADAPTER_PROTOCOL.md](./SOURCE_ADAPTER_PROTOCOL.md)
- [OBSIDIAN_BINDING.md](./OBSIDIAN_BINDING.md)
- [LLM_PROVIDER_CONFIG.md](./LLM_PROVIDER_CONFIG.md)

## When To Update This Roadmap

Update this file when a future direction changes. Use [CHANGELOG.md](./CHANGELOG.md) for completed version history and `docs/archive/` for detailed historical reviews.
