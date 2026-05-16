# MindForge

**A local-first, LLM-first personal AI knowledge processor.** Turn local files into reviewable knowledge cards, then synthesize approved knowledge into structured Wiki pages via LLM-first synthesis. Web console + CLI.

All data stays in your local vault — no RAG, no embeddings, no vector database. AI generates drafts only; explicit human approval is required before any content becomes official knowledge.

---

## Core Workflow

```
Source → AI Draft → Human Review → Explicit Approve → Approved Card
                                                        ├── Library
                                                        ├── Recall (BM25)
                                                        └── Wiki (LLM synthesis)
```

---

## Quick Start

```bash
git clone https://github.com/yaoziyaoguai/mindforge.git
cd mindforge
python -m venv .venv
source .venv/bin/activate
pip install -e .

mkdir -p /tmp/mindforge-first-run
cd /tmp/mindforge-first-run
mindforge init
mindforge status
mindforge web --open
```

Open `http://127.0.0.1:8765`, go to **Setup** → **Add model**, and configure your LLM provider with an API key. Keys are stored in the local secret store — never in Git, YAML, or the browser.

Add your first source:

```bash
printf '# First note\n\nTesting MindForge.\n' > vault/00-Inbox/first-note.md
mindforge watch add vault/00-Inbox/first-note.md
```

Review and approve drafts, then browse the Library, search with Recall, or generate a Wiki.

---

## Features

- **Multi-format ingestion** — Markdown, TXT, HTML, DOCX, PDF (text-based)
- **AI draft generation** — Five-stage processing: Triage → Distill → Link Suggestion → Review Questions → Action Extraction
- **Explicit approval** — No automatic approval. `ai_draft` → `human_approved` requires manual confirmation
- **BM25 Recall** — Local lexical search over approved cards
- **LLM-first Wiki** — Synthesize approved cards into structured topic pages
- **Web console + CLI** — Same Python service layer, dual entry points

## Safety

| Principle | Implementation |
|-----------|---------------|
| local-first | Single-user, no telemetry, no upload |
| API key safety | Local secret store only; masked in API responses |
| No auto-approval | Every approve path requires explicit confirmation |
| Wiki from approved only | Unreviewed content never enters Wiki |
| Real LLM opt-in | Model + API key + explicit trigger required |

## Current Status

- **v0.1** — Stable release with complete local-first / LLM-first pipeline
- **v0.2** — Release candidate: main feature work complete, in pre-release validation

Suitable for non-sensitive material at small scale. Not recommended for private/sensitive vaults yet.

## Documentation

| Document | Description |
|----------|-------------|
| [README.zh-CN.md](README.zh-CN.md) | 中文入口 (Chinese entry) |
| [Getting Started (CN)](docs/zh-CN/getting-started.md) | 中文快速入门 |
| [User Guide (CN)](docs/zh-CN/user-guide.md) | 中文用户指南 |
| [Getting Started (EN)](docs/en/getting-started.md) | English getting started |
| [User Guide (EN)](docs/en/user-guide.md) | English user guide |
| [Model Setup](docs/zh-CN/model-setup.md) | LLM provider configuration |
| [Release Notes](docs/RELEASE_NOTES.md) | First release notes |
| [Developer Docs](docs/dev/) | Architecture, testing, contributing |
| [Design Docs](docs/design/) | RFCs, SDDs, roadmap |

## License

MIT
