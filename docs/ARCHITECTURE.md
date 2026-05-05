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

The fake provider is the default safe path. Real providers are opt-in. Provider
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

## Focused Protocols

The canonical architecture above is intentionally short. Detailed historical
protocols remain available because code and tests still reference them:

- [Human Approval Protocol](M3_HUMAN_APPROVAL_PROTOCOL.md)
- [Recall / Review Protocol](M4_RECALL_REVIEW_PROTOCOL.md)
- [SourceAdapter Protocol](SOURCE_ADAPTER_PROTOCOL.md)
- [Lexical Recall Protocol](M5_4_LEXICAL_RECALL_PROTOCOL.md)
- [Local-First Privacy Contract](LOCAL_FIRST_PRIVACY_CONTRACT.md)
- [Security](SECURITY.md)
