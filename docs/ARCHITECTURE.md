# MindForge Architecture

MindForge is a local-first CLI pipeline. It keeps raw inputs, generated cards, state, run logs, indexes, and telemetry separated so the system can be audited without leaking private content.

## Data Flow

```text
00-Inbox/<subdir>/*
  -> SourceAdapter
  -> SourceDocument
  -> LLM pipeline
  -> 20-Knowledge-Cards/<track>/*.md
  -> approve / recall / review / project context / vault helpers
```

## Core Layers

### Source Ingestion

`src/mindforge/scanner.py` dispatches files by `configs/mindforge.yaml.sources.registry`. Each source is handled by a `SourceAdapter` and normalized into `SourceDocument`.

Active adapter contract:

- [SOURCE_ADAPTER_PROTOCOL.md](./SOURCE_ADAPTER_PROTOCOL.md)
- `src/mindforge/sources/base.py`
- `src/mindforge/sources/registry.py`

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
