# MindForge

> **Project Status: Paused / Soft Archived**
> MindForge is currently preserved as a vibe-coding learning project and postmortem artifact. The standalone Web knowledge-base product direction is no longer actively pursued. The code remains available for reference, learning, and possible future experiments. See [docs/postmortem/](docs/postmortem/) for details.

[中文](README.md) | [English]

MindForge is a local-first personal AI knowledge tool. It turns local Markdown, TXT, HTML, PDF, and DOCX materials into reviewable knowledge-card drafts, waits for explicit human approval, then uses approved cards to build a personal Wiki.

It is designed for people who want a small, inspectable knowledge loop over their own files. MindForge provides both a Web console and a CLI. AI output starts as `ai_draft`; official knowledge requires explicit approval into `human_approved`.

```
Source → AI Draft → Human Review → Explicit Approve → Approved Card
                                                        ├── Library
                                                        ├── Recall (BM25)
                                                        └── Topic View (runtime)
```

## What It Is

MindForge's main path is the **Knowledge Card Workflow**:

1. Import or watch local source files.
2. Generate `ai_draft` knowledge-card drafts with the model you configure in Web Setup.
3. Review drafts manually.
4. Explicitly approve useful drafts into `human_approved`.
5. Browse approved cards in Library, search with Recall, and rebuild a Wiki from approved cards.

MindForge is not a RAG platform. It does not use embeddings, vector databases, or automatic approval.

## Who It Is For

- People turning notes, research files, course material, or project records into reviewable knowledge cards.
- Users who want local lexical search over approved knowledge instead of opaque retrieval over raw files.
- Users who want a personal Wiki derived only from reviewed material.
- Small-scale, non-sensitive personal knowledge workflows.

MindForge is not yet recommended for private sensitive vaults, company-confidential material, or large production archives.

## Current Capabilities

- **Source import/watch** — use `mindforge import <path>` for one-time import or `mindforge watch add <path>` for registered sources.
- **AI draft card** — five-step workflow: Triage → Distill → Link Suggestion → Review Questions → Action Extraction.
- **Human review/approval** — every draft requires CLI or Web Review approval.
- **Knowledge Library** — browse approved `human_approved` cards.
- **Topic View** — browse approved cards grouped by Topic via runtime API (`/api/topics`).
- **Source provenance** — keep source, hash, and available page/paragraph/line provenance for traceability.
- **Related cards** — deterministic relationships such as same source, same tag, same wiki section, and same review batch.
- **Knowledge Health** — read-only maintenance report for review backlog, low-quality cards, missing provenance, duplicate candidates, orphan cards, stale wiki, and suggested actions.
- **Local Graph Preview** — local relationship preview based on deterministic source/tag/wiki-section/review-batch relations. It does not use a vector database and is not GraphRAG.

## Safety Boundaries

| Boundary | Meaning |
|----------|---------|
| offline by default | A fresh workspace does not call real LLM/API services and does not upload telemetry by default; external model calls require explicit provider/API key setup plus an explicit import/watch processing action |
| local-first | Single-user local workspace; reads and writes local files by default |
| local API key setup | Configure keys through Web Setup; keys are stored in the local secret store (`.mindforge/secrets.json`) |
| no automatic secret disclosure | MindForge does not automatically read environment files or secret store values for source processing and print API keys, tokens, or secrets |
| no automatic local-data outflow | Raw sources, API keys, tokens, and secrets do not go into Git, the Web frontend, or telemetry by default |
| do not paste keys | Do not paste API keys into chats, issues, terminal logs, README files, or YAML |
| no automatic approval | `ai_draft` never enters Library automatically; `human_approved` requires explicit approve |
| Topic View uses approved cards only | Topic View does not bypass approval, does not include unapproved content, and does not read raw sources |
| real model calls are explicit | Model + API key + explicit import/watch processing trigger |
| legacy `.doc` unsupported | Old Word `.doc` files are reported with a friendly conversion hint |
| no OCR | PDF support is text-layer only; scanned PDFs are not recognized |
| Graph is not GraphRAG | Local Graph Preview is a local view based on deterministic relations such as same_source, same_tag, same_wiki_section, same_review_batch, and source_location_neighbor; there is currently no standalone global Graph page, and it is not Vector DB, Graph DB, Embedding, or GraphRAG |

Custom strategy support is currently declarative preview only: preview packet is review-only, not ai_draft, not human_approved; no arbitrary python, no shell; preview to future implementation requires a reviewed built-in implementation path and still requires explicit approval and explicit opt-in.

For first runs, use synthetic source files or a temporary folder before connecting real personal material.

## Requirements

- Python >=3.11
- pip
- An available LLM API key (Anthropic, OpenAI, or compatible protocol)
- Node/npm for building the Web frontend (the Web UI and Setup page require built frontend assets)

## Quick Start

```bash
git clone https://github.com/yaoziyaoguai/mindforge.git
cd mindforge

# Install Python dependencies
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .

# Build Web frontend (needed for Web UI / Setup page)
cd web
npm install
npm run build
cd ..

mkdir -p /tmp/mindforge-first-run
cd /tmp/mindforge-first-run
mindforge init

mindforge start
mindforge status
mindforge web --open
```

`mindforge init` creates a local **workspace** with a vault skeleton and runtime config. The workspace path is remembered in `~/.mindforge/current_workspace.json`, so later commands can find it from any directory.

Open `http://127.0.0.1:8765`, go to **Setup** → **Add model**, and configure your LLM provider:

- model id, for example `main`
- type: `anthropic` / `anthropic_compatible` / `openai` / `openai_compatible`
- base URL
- model name
- API key

Keys are stored in the local secret store, not in Git, YAML, or the browser frontend.

## First Source

```bash
printf '# First note\n\nA short note for MindForge.\n' > vault/00-Inbox/first-note.md

mindforge watch add vault/00-Inbox/first-note.md
# Or one-time import:
mindforge import vault/00-Inbox/first-note.md
```

Check processing:

```bash
mindforge runs list
mindforge runs show <run_id>
```

Review and approve:

```bash
mindforge approve list
mindforge approve show --card 1 --show-content
mindforge approve 1 --confirm
```

Browse, search, and rebuild Wiki:

```bash
mindforge library list
mindforge recall --query "MindForge"
mindforge wiki status
mindforge wiki show
```

## Watch Frequency

`watch add` defaults to **manual** frequency, so it does not scan automatically. To enable periodic scanning:

```bash
mindforge watch add <path> --every daily
mindforge watch add <path> --frequency "every 6h"
```

Supported frequencies:

| Frequency | Behavior |
|-----------|----------|
| `manual` | Default; no auto-scan; manual `mindforge watch scan` only |
| `hourly` | Every 1 hour |
| `daily` | Every 24 hours |
| `weekly` | Every 7 days |
| `every 1h` | Every 1 hour |
| `every 6h` | Every 6 hours |
| `every 12h` | Every 12 hours |
| `every 24h` | Every 24 hours |

Check current frequency:

```bash
mindforge watch status
```

Frequency can be set via CLI (`--every` / `--frequency`) or Web UI (Setup → Add Source, or Sources → Edit frequency).

## Supported Source Formats

The base install supports Markdown, TXT, and local HTML. For PDF and DOCX support:

```bash
pip install "mindforge[pdf,docx]"
```

| Format | Status | Notes | Dependency |
|--------|--------|-------|------------|
| Markdown | Supported | `.md` files | Base install |
| TXT | Supported | Plain text | Base install |
| HTML | Supported | Local files only; no URL crawling | Base install |
| PDF (text-based) | Supported | Text extraction only; no OCR, no scanned documents | `pypdf` (optional) |
| DOCX | Supported | Modern `.docx` format | `python-docx` (optional) |
| DOC (legacy) | Unsupported | Friendly conversion hint to DOCX/TXT/PDF | — |

Supported means MindForge can attempt import, extraction, triage, and `ai_draft` generation when model setup is complete. It does not guarantee every file will produce a card. Low-value content, empty files, textless PDFs, oversized files, or model errors may result in skipped or failed runs.

## Path Rules

`vault/` is the local knowledge-base directory. Local runtime config is gitignored.

**Web Add Source requires absolute paths.**

- `~/Documents/note.md` is expanded to `/Users/<name>/Documents/note.md`
- `note.md` returns 400; use an absolute path
- missing paths return 400

**CLI source paths may be relative** and are resolved by cwd → project-root → active-vault.

## Library / Recall / Wiki

```bash
mindforge library list
mindforge library show <ref>
mindforge recall --query "keyword"
```

Topic View is a **runtime view** over `human_approved` cards, grouped by Topic/Track. Access it via the `/api/topics` endpoints or CLI:

```bash
mindforge wiki status
mindforge wiki show
```

Topic View only uses approved cards. It does not bypass approval to read raw sources. Approved cards are the source of truth; Topic View is a derived runtime view. LLM-based Wiki synthesis (`llm_rebuild_wiki`) is deprecated in v0.5.

## Web Console

Start with `mindforge web --open`:

| Page | Purpose |
|------|---------|
| **Home** | Status overview, safety summary, next steps |
| **Setup** | Configure models, inspect workflow, add sources |
| **Sources** | Manage watched sources, Process now, Import |
| **Review** | View AI drafts, approve, or move to Trash |
| **Library** | Browse approved cards, related cards, and Local Graph Preview |
| **Trash** | Safe recycle bin with Restore |
| **Recall** | Local BM25 lexical search |
| **Wiki** | Topic View — runtime knowledge browsing by Topic |

## CLI Reference

| Command | Description |
|---------|-------------|
| `mindforge init` | Initialize local workspace |
| `mindforge start` | Show first-run checklist |
| `mindforge status` | Workspace / vault / draft status |
| `mindforge web` | Start Web console |
| `mindforge import <path>` | One-time source import and processing |
| `mindforge watch add <path>` | Register and process a source |
| `mindforge runs list` | List processing runs |
| `mindforge runs show <run_id>` | Show run details |
| `mindforge approve list` | List pending `ai_draft` cards |
| `mindforge approve show <ref>` | Show draft content |
| `mindforge approve <ref> --confirm` | Explicitly approve |
| `mindforge library list` | Browse Library |
| `mindforge recall --query "keyword"` | BM25 search |
| `mindforge wiki status` | Show Wiki status |
| `mindforge wiki rebuild` | Rebuild Wiki |
| `mindforge health` | Generate read-only Knowledge Health report |
| `mindforge doctor` | Environment/config/risk diagnostics |
| `mindforge version` | Version and config summary |

## Current Status / Versioning

- Package version: `0.7.22`
- Product milestone: `v0.3 Local AI Knowledge Loop / Knowledge Quality & Navigation`

Package version tracks Python package iteration and distribution. Product milestone describes the product roadmap and release stage. They are separate numbering systems, so `0.7.22` and `v0.3` can both be correct.

The current feature stage focuses on a local, single-user, explicit-approval knowledge loop plus quality, provenance, relationship, and maintenance diagnostics.

## Documentation

| Document | Description |
|----------|-------------|
| [中文 README](README.md) | Chinese GitHub entry |
| [Getting Started (CN)](docs/zh-CN/getting-started.md) | 中文快速入门 |
| [User Guide (CN)](docs/zh-CN/user-guide.md) | 中文用户指南 |
| [Sources (CN)](docs/zh-CN/sources.md) | 中文 Source 管理 |
| [Troubleshooting (CN)](docs/zh-CN/troubleshooting.md) | 中文故障排除 |
| [Getting Started (EN)](docs/en/getting-started.md) | English getting started |
| [User Guide (EN)](docs/en/user-guide.md) | English user guide |
| [Sources (EN)](docs/en/sources.md) | English source guide |
| [Troubleshooting (EN)](docs/en/troubleshooting.md) | English troubleshooting |
| [Model Setup](docs/zh-CN/model-setup.md) | LLM provider configuration |
| [Release Notes](docs/RELEASE_NOTES.md) | Release notes |
| [Developer Docs](docs/dev/) | Architecture, testing, contributing |
| [Design Docs](docs/design/) | RFCs, SDDs, roadmap |

## License

MIT
