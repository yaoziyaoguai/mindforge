# Obsidian Binding

This document defines the v0.5 read-only bridge between MindForge and an
Obsidian vault.

## Positioning

Obsidian is a first-class personal knowledge source for MindForge:

- existing notes, project records, learning tracks, daily notes, Knowledge Cards,
  tags, frontmatter, wikilinks, and folder structure are input context;
- the first implementation stage must be read-only against a real vault;
- source material from Obsidian should enter the same `SourceAdapter` and
  `SourceDocument` contract as other inputs.

Obsidian is also a human knowledge workbench:

- future generated summaries, candidate cards, MOCs, review notes, and learning
  route suggestions may be written only to a staging/review area;
- MindForge must not directly rewrite formal notes, move files, or rewrite
  wikilinks;
- human confirmation is required before anything becomes part of the user's
  maintained vault.

Obsidian is not a machine runtime store:

- checkpoints, run logs, caches, vector indexes, graph indexes, SQLite metadata,
  and intermediate task state do not belong in formal notes;
- machine state belongs in `.mindforge/` or other derived stores;
- derived indexes must be rebuildable from the vault and MindForge artifacts.

## v0.5 Implemented MVP

- Configure an Obsidian vault path.
- Read Markdown files without modifying them:
  `mindforge obsidian scan --vault <path>`.
- Parse frontmatter, tags, aliases, created/updated fields, `[[wikilinks]]`,
  headings, file path, relative path, and content hash.
- Add `ObsidianVaultSourceAdapter` with `source_type: obsidian_note`.
- Inspect links read-only:
  `mindforge obsidian links --vault <path>`.
- Check binding safety:
  `mindforge obsidian doctor --vault <path>`.
- Generate candidate output only into staging/review:
  `mindforge obsidian stage --source <note> --dry-run`.
- Keep machine indexes and intermediate state outside formal vault notes.

`stage` defaults to dry-run. Real writes require `--write --confirm` and the
output directory must be inside `obsidian.staging_dir` or `obsidian.review_dir`.

## Demo Smoke

```bash
mindforge obsidian doctor --vault examples/demo-vault
mindforge obsidian scan --vault examples/demo-vault --limit 5
mindforge obsidian links --vault examples/demo-vault
mindforge obsidian stage --vault examples/demo-vault \
  --source 02-Knowledge/agent-runtime-observer.md --dry-run
```

The demo vault is fictional. These commands do not read `.env`, call a real LLM,
open sockets, or modify formal notes.

## v0.5 Non-Goals

- Do not auto-organize the full vault.
- Do not modify formal notes.
- Do not move files.
- Do not rewrite wikilinks.
- Do not implement complex RAG.
- Do not implement a graph database.
- Do not implement a vector database.
- Do not run large-scale real-vault dogfooding before the read-only boundary is
  designed and tested.

## Before Real Dogfooding

- Verify scan/links/stage dry-run on a small non-sensitive vault sample.
- Confirm include/exclude directories match the user's real vault structure.
- Confirm staging/review location is acceptable to the human workflow.
- Confirm `.mindforge/` and other runtime artifacts remain outside formal notes.
