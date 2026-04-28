# MindForge

> Local-first AI learning memory: turn scattered notes, clips, documents, and chat exports into reviewed, reusable Knowledge Cards.

MindForge is a CLI pipeline for personal knowledge processing. It scans local inbox files, normalizes them through SourceAdapters, runs a staged LLM pipeline, writes Knowledge Cards into a vault, and keeps state, run logs, recall indexes, review plans, and telemetry local.

Current version: **v0.4.3** (`init --interactive`, doctor/next polish, Chinese-localized user errors, onboarding smoke).

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

mindforge init --interactive
mindforge doctor
mindforge commands
mindforge next
```

To try the product without using your own data:

```bash
mindforge --vault examples/demo-vault doctor
mindforge --vault examples/demo-vault next
mindforge --vault examples/demo-vault scan
mindforge --vault examples/demo-vault index rebuild
mindforge --vault examples/demo-vault recall --query "checkpoint runtime" --ranking hybrid
mindforge --vault examples/demo-vault project context my-first-agent --target claude-code
```

The demo vault is fictional and safe to inspect. See [examples/demo-vault/README.md](examples/demo-vault/README.md).

## What It Does

- Ingests local sources through adapters: Cubox markdown, plain markdown, web clips, chat exports, text PDFs, and docx files.
- Converts every source to a frozen `SourceDocument` contract before downstream processing.
- Runs a five-stage pipeline: triage, distill, link suggestion, review questions, action extraction.
- Writes Knowledge Cards under `20-Knowledge-Cards/`, defaulting to `status: ai_draft`.
- Requires explicit human approval before cards become `human_approved`.
- Provides local BM25/hybrid recall, review scheduling, project context packs, vault indexes, and local-only telemetry.

## What It Does Not Do

- No automatic approval of AI output.
- No remote telemetry or cloud sync.
- No RAG, embedding, or vector database in v0.x.
- No OCR for scanned PDFs.
- No Obsidian plugin yet.
- No background daemon, system calendar integration, email, or desktop notifications.

## Safety Defaults

- Default `active_profile=fake`, so `mindforge process` does not call real LLMs after clone.
- `.env` is never printed; doctor/next do not read `.env` contents.
- Raw inbox files are read-only and never modified by MindForge.
- Telemetry is local-only and uses a strict metadata whitelist.
- Recall indexes Knowledge Cards only, not raw source documents.

See [docs/SECURITY.md](docs/SECURITY.md) for the full safety contract.

## Documentation

Start here:

- [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) - documentation map
- [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) - first successful run
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - daily commands and workflows
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - system shape and data flow
- [docs/SECURITY.md](docs/SECURITY.md) - boundaries and invariants
- [docs/SOURCE_ADAPTER_PROTOCOL.md](docs/SOURCE_ADAPTER_PROTOCOL.md) - adding or auditing source adapters
- [docs/LLM_PROVIDER_CONFIG.md](docs/LLM_PROVIDER_CONFIG.md) - real provider setup
- [docs/TESTING.md](docs/TESTING.md) - smoke tests and quality gates
- [docs/ROADMAP_PROGRESS.md](docs/ROADMAP_PROGRESS.md) - current completion snapshot
- [docs/CHANGELOG.md](docs/CHANGELOG.md) - version history

## Development Status

- Latest local commit: `dc67474`
- Tag: `v0.4.3`
- Quality gate at tag: `344 passed, 2 skipped`; `ruff` clean; `git diff --check` clean
- No remote push was performed in this local repository state.

Recommended next step: run 1-2 weeks of real dogfooding with non-sensitive personal material, record pain points, then decide whether v0.5 should be design-only Obsidian/RAG exploration or more CLI polish.
