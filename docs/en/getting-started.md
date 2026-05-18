# Getting Started

Installation, initialization, and first-use guide for MindForge.

---

## Requirements

- Python 3.11+
- pip
- An available LLM API key (Anthropic, OpenAI, or compatible protocol)

---

## Installation

```bash
git clone https://github.com/yaoziyaoguai/mindforge.git
cd mindforge
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify:

```bash
mindforge version
```

---

## Initialize Workspace

A workspace is MindForge's working directory — it contains the vault (knowledge base) and local runtime config.

```bash
mkdir -p ~/mindforge-workspace
cd ~/mindforge-workspace
mindforge init
```

`mindforge init` creates the vault skeleton and local config. The workspace path is remembered automatically — you can run MindForge commands from any directory afterward.

Check status:

```bash
mindforge start     # View first-run checklist
mindforge status    # Workspace / vault / draft status
```

---

## Configure a Model

MindForge needs an LLM model to generate knowledge cards and Wiki.

```bash
mindforge web --open
```

Open `http://127.0.0.1:8765`:

1. Go to **Setup** page
2. Click **Add model**
3. Fill in:
   - **Model id**: alias like `main`
   - **Type**: `anthropic` / `anthropic_compatible` / `openai` / `openai_compatible`
   - **Base URL**: model endpoint
   - **Model**: model name
   - **API key**: your real API key
4. Save

API keys are stored in the local secret store (`.mindforge/secrets.json`) — never in Git, YAML, or the browser.

### Supported Model Types

| Type | Protocol | Use Case |
|------|----------|----------|
| `anthropic` | Anthropic Messages API | Direct Anthropic Claude |
| `anthropic_compatible` | Anthropic-compatible protocol | DashScope, OpenRouter |
| `openai` | OpenAI Chat Completions API | Direct OpenAI |
| `openai_compatible` | OpenAI-compatible protocol | Ollama, LM Studio, DeepSeek |

Local models (Ollama, LM Studio) use `openai_compatible` + `api_key_optional: true`.

For detailed configuration, see [Model Setup](model-setup.md).

---

## Add Your First Source

A source is a local file you want AI to process. Place files under `vault/00-Inbox/`:

```bash
printf '# First note\n\nA test note for MindForge.\n' > vault/00-Inbox/first-note.md
mindforge watch add vault/00-Inbox/first-note.md
```

`watch add` registers the source and starts background processing. AI-generated drafts appear on the Review page when ready.

For one-time import (without watching):

```bash
mindforge import vault/00-Inbox/first-note.md
```

### Supported Formats

Markdown (`.md`), TXT (`.txt`), HTML (`.html`), DOCX (`.docx`), text-based PDF (`.pdf`). Legacy `.doc` is not supported.

---

## Check Progress

```bash
mindforge runs list              # List all processing runs
mindforge runs show <run_id>     # View run details
```

Real model processing may take minutes — `running` doesn't mean stuck.

---

## Approve Knowledge Cards

AI generates `ai_draft` (preview only). Explicit approval is required for `human_approved` (official knowledge).

```bash
mindforge approve list                   # List pending drafts
mindforge approve show --card 1 --show-content  # View draft content
mindforge approve 1 --confirm            # Explicitly approve
```

Or use the Web **Review** page. **Approval is always explicit. No automatic approval.**

---

## Browse & Search

```bash
mindforge library list           # Browse approved cards
mindforge library show <ref>     # View card details
mindforge recall --query "keyword"  # BM25 lexical search
mindforge health                 # Read-only Knowledge Health report
```

Knowledge Health checks review backlog, low-quality cards, missing provenance, duplicate candidates, orphan cards, stale wiki, and suggested maintenance actions. It does not modify your content.

---

## Generate Wiki

Wiki uses LLM-first synthesis over all `human_approved` cards.

```bash
mindforge wiki status
mindforge wiki rebuild
mindforge wiki show
```

Or click **Generate Wiki** on the Web **Wiki** page.

Wiki only uses approved cards — it never bypasses approval. LLM synthesis must be triggered manually.

Related cards and Local Graph Preview in Library / Wiki use deterministic source, tag, wiki section, and review batch relationships for local navigation. They are not a vector database or GraphRAG.

---

## Next Steps

- [User Guide](user-guide.md) — Complete feature documentation
- [Model Setup](model-setup.md) — LLM provider configuration
- [README](../../README.md) — Project overview
