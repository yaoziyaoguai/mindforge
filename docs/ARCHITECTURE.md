# MindForge Architecture

MindForge is a local-first CLI pipeline. It keeps raw inputs, generated cards, state, run logs, indexes, and telemetry separated so the system can be audited without leaking private content.

Obsidian is treated as personal knowledge context, not as a machine runtime
store. The v0.5 direction is a minimal read-only Obsidian binding that can
ingest vault notes through the same source adapter contract while keeping
generated output in staging/review areas and keeping runtime state outside
formal notes.

## Data Flow

```text
00-Inbox/<subdir>/*
  -> SourceAdapter
  -> SourceDocument
  -> LLM pipeline
  -> 20-Knowledge-Cards/<track>/*.md
  -> approve / recall / review / project context / vault helpers
```

v0.5 adds the design target below without changing the downstream contract:

```text
Obsidian vault Markdown (read-only)
  -> ObsidianVaultSource adapter
  -> SourceDocument
  -> existing pipeline / recall / review layers
  -> staging/review output only, never direct formal-note rewrites
```

## Core Layers

### Source Ingestion

`src/mindforge/scanner.py` dispatches files by `configs/mindforge.yaml.sources.registry`. Each source is handled by a `SourceAdapter` and normalized into `SourceDocument`.

Active adapter contract:

- [SOURCE_ADAPTER_PROTOCOL.md](./SOURCE_ADAPTER_PROTOCOL.md)
- `src/mindforge/sources/base.py`
- `src/mindforge/sources/registry.py`

For Obsidian, the intended source adapter is `ObsidianVaultSource`: it should
read Markdown notes, frontmatter, tags, `[[wikilinks]]`, and directory context
without modifying the vault.

### SourceDocument Contract

`SourceDocument` is the only downstream source interface. It contains `source_id`, `source_type`, `source_path`, metadata, highlights, `raw_text`, `content_hash`, and `adapter_name`.

The broader data contract remains in [MINDFORGE_PROTOCOL.md](./MINDFORGE_PROTOCOL.md).

### Processing Pipeline

The pipeline has five fixed stages:

1. `triage`
2. `distill`
3. `link_suggestion`
4. `review_questions`
5. `action_extraction`

Provider routing is static through `llm.active_profile` and per-stage aliases in `configs/mindforge.yaml`. Default profile is `fake`.

### Knowledge Cards

Cards are written to `20-Knowledge-Cards/<track>/*.md` and default to `status: ai_draft`. Cards become durable memory only after explicit `mindforge approve`.

### State, Runs, Telemetry

- `.mindforge/state.json`: processing state machine and content hashes.
- `.mindforge/runs/*.jsonl`: local per-run event chain.
- `.mindforge/telemetry.jsonl`: local command-use metadata only.
- `.mindforge/index/bm25.json`: local recall index built from safe card fields.

These files have separate responsibilities and should not be merged.
They also must not be written into formal Obsidian notes. Future SQLite,
vector, graph, cache, or checkpoint stores are derived machine layers and must
remain rebuildable from source vault content and MindForge artifacts.

### Obsidian Boundary

Obsidian has three roles in the target architecture:

1. **Personal knowledge source**: existing notes, daily notes, project notes,
   tags, frontmatter, wikilinks, and folders are input context.
2. **Human knowledge workbench**: MindForge may propose summaries, candidate
   cards, MOCs, review notes, or learning routes into a staging/review area.
3. **Not runtime state**: logs, checkpoints, caches, indexes, and intermediate
   state stay out of formal notes.

MindForge must not auto-organize the vault, move files, rewrite wikilinks, or
edit formal notes without a separate explicit review workflow.

Detailed v0.5 boundary: [OBSIDIAN_BINDING.md](./OBSIDIAN_BINDING.md).

### Recall And Review

Recall is local lexical search with optional hybrid ranking. Review scheduling is local plan/export only. There is no vector database, background scheduler, system calendar integration, or notification daemon.

Active detail docs:

- [M5_4_LEXICAL_RECALL_PROTOCOL.md](./M5_4_LEXICAL_RECALL_PROTOCOL.md)
- [M4_RECALL_REVIEW_PROTOCOL.md](./M4_RECALL_REVIEW_PROTOCOL.md)

### Project Context

Project context joins safe card summaries with `30-Projects/<name>.md` frontmatter. Project note bodies are not read. `update-evidence` writes only a controlled START/END block in project files.

Active detail doc:

- [M5_3_PROJECT_CONTEXT_PROTOCOL.md](./M5_3_PROJECT_CONTEXT_PROTOCOL.md)

## Extension Points

- Add source formats through `SourceAdapter`.
- Add provider integrations through `src/mindforge/llm/`.
- Add CLI polish in `src/mindforge/cli.py`.

Avoid adding architecture outside the current safety model without updating [SECURITY.md](./SECURITY.md), [ROADMAP.md](./ROADMAP.md), and tests.
