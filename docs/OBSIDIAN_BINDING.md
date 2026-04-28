# Obsidian Binding

This document defines the v0.5 direction for connecting MindForge with an
Obsidian vault. It is a design boundary, not an implementation note.

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

## v0.5 Minimal Scope

- Configure an Obsidian vault path.
- Read Markdown files without modifying them.
- Parse frontmatter, tags, `[[wikilinks]]`, and directory structure.
- Add an `ObsidianVaultSource` adapter concept to the source adapter system.
- Design a staging/review output area for candidate MindForge artifacts.
- Keep machine indexes and intermediate state outside formal vault notes.

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
