# MindForge Architecture

MindForge is a local-first personal AI learning memory tool with two user
surfaces: CLI for precise local control and Web for a localhost-only personal
console. The architecture serves a single user and one local workspace. It is
not SaaS, not a cloud sync service, not a multi-user admin product, and not a
hidden automation layer over private notes.

## Product Shape

MindForge helps a person review their own learning material safely:

```text
SourceAdapter
  -> SourceDocument
  -> processing pipeline
  -> ai_draft
  -> explicit human approval
  -> human_approved
  -> local recall / review / Obsidian or OPS binding
```

The central object crossing ingestion boundaries is `SourceDocument`. Cubox is
only one `SourceAdapter`; it must not become the architecture center. Processor
and `KnowledgeStrategy` implementations depend on `SourceDocument`, not on a
specific upstream product.

AI output is advisory. It can produce `ai_draft` cards only. A card becomes
long-term memory only through an explicit approval action performed by the user.

## Source And Card Contracts

`SourceDocument` is the information-hiding boundary between adapters and the
processing pipeline. Adapters may understand Cubox exports, Markdown files,
web clips, chat exports, PDF/docx text extraction, or Obsidian-flavored
Markdown, but downstream processors should only see normalized source fields.

Core source fields include stable identifiers, `source_type`, `source_path`,
adapter metadata, title, timestamps where available, safe metadata, content
hash, highlights, and `raw_text`. The raw source body is allowed inside the
pipeline, but user-facing status, readiness, recall, logs, and telemetry should
prefer summaries and safe fields.

Knowledge Cards are Markdown artifacts with frontmatter. Newly generated cards
default to `status: ai_draft`; recall and review use `human_approved` by
default. Draft inclusion is always explicit.

## Boundaries

### CLI

The CLI is a thin adapter. It parses arguments, loads local context, delegates
to services/facades, and renders human-friendly output. It should not own core
approval, provider, recall, or workspace business rules.

### Web

The Web first slice is a local presentation/control layer:

```text
React UI
  -> FastAPI APIRouter controller
  -> mindforge_web service/facade
  -> existing mindforge service / policy / storage
  -> local files under configured workspace/vault
```

Routers are controllers, not business modules. They validate payloads and call
the Web facade. The facade may orchestrate Web scenarios, but it must reuse the
existing MindForge services and policies.

### Service and Presenter

Services hold business semantics and return structured results. Presenters hold
output shape. CLI/Web adapters may choose format, but they should not duplicate
domain decisions.

### Provider and Readiness

The fake provider is the default safe path. A fake provider keeps first-run
dogfood offline and cheap. Real providers are opt-in. A real provider can be
used only after explicit profile selection and readiness/smoke checks. Provider
readiness reports configuration state and key presence, but must not call a real
LLM. Cubox readiness follows the same rule: report local configuration/path
state, do not call the real Cubox API during readiness checks.

### Approval

Approval is the trust boundary:

- `ai_draft -> human_approved` requires an explicit user action.
- Web approve requires `confirm: true` and `reviewed_source: true`.
- CLI approve requires the explicit confirmation path.
- No status, recall, scan, import, or background command may create
  `human_approved`.
- Reject/defer must be honest if persistence is unavailable; no fake success.

### Workspace, Obsidian, and OPS

Obsidian or an OPS workspace is a human knowledge workbench. It must not be used
as a dumping ground for machine runtime/state/cache/index/logs/vector stores or
graph-derived layers. MindForge may read or stage into controlled locations, but
it must not automatically reorganize a real private vault.

## Recall

Current recall is local lexical retrieval, backed by approved cards and BM25-like
ranking where available. It is not RAG, not embeddings, not semantic search, and
not semantic merge. Drafts are excluded unless a command explicitly asks for
draft inclusion.

## Current Non-Goals

MindForge currently does not do:

- RAG, embeddings, vector stores, or semantic merge.
- Obsidian plugin development.
- Automatic organization of a real vault.
- Real LLM calls by default.
- Real Cubox API calls by default.
- Cloud sync, login, OAuth, payment, hosting, or multi-user permissions.

## Long-Term Architecture Principles

- High cohesion: each module should have one clear reason to change.
- Low coupling: adapters depend on stable service contracts, not internal file
  layout.
- Information hiding: secret values, raw provider payloads, and private note
  bodies stay behind explicit user actions.
- Thin adapters: CLI, FastAPI routers, and React components should not grow into
  new monoliths.
- Domain names over generic helpers: avoid `common` or `utils` dumping grounds.
- Tests protect behavior and boundaries, not arbitrary file-size metrics.

## Product Landscape

MindForge borrows selectively from neighboring tools without copying their
product shape. OpenAI Agents SDK and LangGraph show why explicit runtime
boundaries matter; Dify shows why MindForge should not become a hosted workflow
builder; Obsidian, Logseq, Tana, Anytype, Readwise, and Cubox show useful
personal knowledge and source-capture patterns. The differentiation is a
local-first, single-user approval pipeline: source-grounded drafts become
durable memory only after explicit human review.

## Focused Protocols

The canonical architecture above is the source of truth for active design.
Historical protocol documents have been retired into this page and the focused
references. Keep future design changes here instead of creating new milestone
documents.

Focused references:

- [Security](SECURITY.md)
- [Implementation](IMPLEMENTATION.md)
- [Usage](USAGE.md)
