# MindForge Implementation Guide

This guide is the code tour for the current local-first CLI + Web system. It is
not a release diary. Start here when you need to understand where behavior lives
before changing it.

## First Files To Read

- `src/mindforge/cli.py` - top-level Typer command registry.
- `src/mindforge/status_cli.py` - real-data CLI status and doctor-style output.
- `src/mindforge/app_context.py` - local config/path context resolution.
- `src/mindforge/sources/base.py`, `src/mindforge/sources/registry.py`, and
  `src/mindforge/scanner.py` - SourceAdapter discovery and SourceDocument
  normalization.
- `src/mindforge/provider_readiness.py` and `src/mindforge/cubox_readiness.py`
  - readiness checks that avoid real external calls.
- `src/mindforge/approval_service.py` and `src/mindforge/approver.py` -
  approval workflow and single-card promotion boundary.
- `src/mindforge/recall_service.py` - local lexical recall use case.
- `src/mindforge/lexical_index.py` and `src/mindforge/recall_index_cli.py` -
  BM25/local index build and inspection.
- `src/mindforge/web_cli.py` - `mindforge web` CLI adapter.
- `src/mindforge_web/` - FastAPI app, routers, schemas, and Web facade.
- `web/src/` - React Local Console implementation.

## CLI Entry

`mindforge` is registered in `pyproject.toml` as `mindforge.cli:main`.
`src/mindforge/cli.py` owns command registration only. Command modules should
parse options, build an app context, call a service/facade, then hand structured
results to a presenter. New behavior should not be hidden in the command body.

The real-data usability milestone added terminal-friendly status paths. Their
job is to explain local state without exposing private content:

- workspace/vault existence and readability
- `.env` key presence, never values
- fake/real/missing provider readiness, without provider calls
- Cubox local readiness, without Cubox API calls
- pending `ai_draft`, approved card, and recall availability
- next safe command

## Web First Slice

`mindforge web` lives in `src/mindforge/web_cli.py`. It parses host, port,
browser-open, and vault override options, then starts `mindforge_web.server`.
The default host is `127.0.0.1`.

The API is built with FastAPI:

- `src/mindforge_web/app.py` creates the app and mounts routers.
- `src/mindforge_web/routers/` contains thin APIRouter controllers.
- `src/mindforge_web/schemas.py` defines API-facing Pydantic shapes.
- `src/mindforge_web/services/web_facade.py` coordinates Web scenarios.

The facade is the Web-specific orchestration boundary. It may combine existing
MindForge services, but it must not reimplement core approval, recall, provider,
or workspace rules.

The frontend lives in `web/` and uses React + Vite + TypeScript + Tailwind. Its
core pages mirror the product flow: Home, Setup, Sources, Drafts, Draft Detail,
and Recall. `DESIGN.md` is the design-system constraint for these surfaces.

## Local Status and Readiness

Readiness checks are deliberately side-effect-light:

- Provider readiness inspects active profile and key-name presence. It does not
  call OpenAI, Upstage, or any other real LLM.
- Cubox readiness checks configured metadata/path/token presence. It does not
  call the real Cubox API.
- Secret handling reports configured/missing by key name only. It must never
  print or return secret values.
- Workspace checks can inspect local paths and MindForge artifact counts, but
  ordinary status output should avoid dumping private source bodies.

When configuration is complex, presenters should explain:

1. What happened.
2. Why it matters.
3. How to fix it.
4. The safest next command.

## Source Adapters

Adapters convert source-specific files or exports into `SourceDocument`.
Current adapter families include Markdown/plain notes, Cubox JSON export,
webclip/chat export, optional PDF/docx text extraction, and read-only
Obsidian-flavored Markdown. Cubox HTTP ingestion is not active; the supported
Cubox path is local JSON export inspection and preview.

PDF/docx support is intentionally conservative. Missing optional dependencies
or textless scanned PDFs should fail with a friendly explanation rather than
attempt OCR.

## Approval Boundary

Approval code is intentionally narrow. The service layer delegates the actual
single-card promotion to the established approval primitive. This preserves the
security invariant that `human_approved` only appears after an explicit user
action.

Tests should keep proving:

- no confirmation means no `human_approved`
- approve uses the explicit approval service boundary
- list/detail/status/recall endpoints do not promote drafts
- Web approve requires confirmation payload
- CLI approve requires explicit confirmation

## Recall

Recall is local lexical search. The implementation is in `recall_service.py`
and supporting index/card modules. It reads approved cards by default and should
describe itself honestly as lexical retrieval, not RAG or embeddings.

The local index is derived state. It can be rebuilt from approved cards and must
not become a source of truth or a vector store.

## Custom Strategies

Custom strategies are declarative metadata definitions. Users expose local
definitions with an explicit `--custom-path`. Discovery is not execution,
loading is not execution, and explicit path loading is required. MindForge does
no implicit home scan, no implicit vault scan, and does not read `.env` to
discover custom definitions. Validation error output should tell the user what
field failed without running the strategy.

MindForge does no arbitrary Python plugin loading, no arbitrary python runtime,
no shell strategy, and no executable strategy runtime. Real provider use remains
explicit opt-in.

Preview packets are review-only: not ai_draft, not human_approved, not
`ai_draft`, and not `human_approved`. Any future implementation still needs
explicit approval. The preview to future implementation path is: keep the
definition declarative, add a reviewed built-in implementation, preserve fake
default behavior, and keep approval separate.

Review-only artifact kinds include preview packets, readiness checks, and real smoke output.
None of these artifacts is a Knowledge Card or an approval event.

## Config and Workspace

Configuration and path resolution belong in context/readiness modules, not in
presenters or routers. Vault/workspace status should be returned as structured
state first, then rendered for CLI or Web. This keeps Web and CLI consistent
without making either surface depend on the other.

## Tests As Boundaries

The suite includes behavior tests and architecture fitness tests. Important
coverage areas:

- FastAPI status/config/drafts/approval safety.
- CLI status/doctor/config/workspace friendliness.
- approval confirmation and non-approval paths.
- secret non-disclosure assertions.
- provider and Cubox readiness without real external calls.
- recall lexical behavior and empty-query guidance.
- source adapter normalization without downstream source-specific coupling.
- custom strategy declarative-only loading/discovery.
- no user-input subprocess or arbitrary dynamic plugin imports.
- no RAG/embedding/semantic merge implementation entry points.
- no automated git tag/release behavior.

When changing docs only, do not edit tests unless a doc path is intentionally
renamed and the test is a documentation-contract test.
