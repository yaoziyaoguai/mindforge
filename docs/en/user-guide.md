# User Guide

Complete feature documentation for MindForge.

---

## Concept Model

| Concept | Description |
|---------|-------------|
| **Workspace** | MindForge's working directory, containing vault and local config |
| **Vault** | Local knowledge base directory for source files and generated cards |
| **Source** | Original file — input for AI processing |
| **ai_draft** | AI-generated draft card, preview only |
| **human_approved** | Officially approved knowledge card after explicit confirmation |
| **Run** | A source processing task with multiple steps |
| **Wiki** | Structured topic pages via LLM synthesis over approved cards |

---

## Workspace Management

### Initialize

```bash
mindforge init
```

Creates a MindForge workspace in the current directory. Path is recorded in `~/.mindforge/current_workspace.json`.

### Status

```bash
mindforge status
```

Shows workspace path, vault state, draft count, etc.

### Diagnostics

```bash
mindforge doctor
```

Checks environment, configuration, and potential risks.

---

## Source Management

### Adding Sources

```bash
# Watch (reprocess on file changes)
mindforge watch add <path>

# One-time import
mindforge import <path>
```

Place sources under `vault/00-Inbox/` — no need to pre-create subdirectories.

### Path Rules

- **Web Add Source**: Absolute paths only. `~/Documents/note.md` auto-expands.
- **CLI**: Relative paths supported, resolved by cwd → project-root → active-vault.

### Supported Formats

| Format | Status |
|--------|--------|
| Markdown (`.md`) | Supported |
| TXT (`.txt`) | Supported |
| HTML (`.html`) | Supported |
| DOCX (`.docx`) | Supported |
| PDF (`.pdf`) | Text-based supported |
| Legacy `.doc` | Not supported |

### Watch Frequency

`watch add` defaults to **manual** frequency — no automatic scanning. Set via CLI `--every` / `--frequency` or Web UI (Setup → Add Source frequency dropdown, Sources → Edit frequency). Options: `manual` / `hourly` / `daily` / `weekly` / `every 1h` / `every 6h` / `every 12h` / `every 24h`. Check frequency: `mindforge watch status`. See [Sources](sources.md) for details.

### Stopping Watch

Use the Web **Sources** page. Stop watching does not delete source files.

---

## Model Configuration

### Model Pool

Configure multiple models under `llm.models`, each with id, type, base URL, and model name.

### Default Model

`llm.default_model` specifies the default model for all workflow steps.

### Model Routing

Optional per-step model assignment:

```yaml
llm:
  routing:
    triage: main
    distill: main
    link_suggestion: main
    review_questions: main
    action_extraction: main
```

Missing steps fall back to default_model.

### Timeout & Retry

- `timeout_seconds`: Single HTTP request timeout (default 120s)
- `max_retries`: Limited retries per call (default 1)

For details, see [Model Setup](model-setup.md).

---

## Processing Workflow

Processing a source goes through five fixed steps:

| Step | Description |
|------|-------------|
| **Triage** | Evaluate source value, output track / value_score |
| **Distill** | Extract core knowledge, generate card body |
| **Link Suggestion** | Suggest related topics and links |
| **Review Questions** | Generate review and self-test questions |
| **Action Extraction** | Extract actionable follow-up items |

Each step can use a different model (model routing).

```bash
mindforge runs list              # List all runs
mindforge runs show <run_id>     # View run details and current step
```

---

## Approval

### CLI

```bash
mindforge approve list                   # List pending ai_draft
mindforge approve show --card 1          # View draft summary
mindforge approve show --card 1 --show-content  # View full content
mindforge approve 1 --confirm            # Explicitly approve
```

### Web

Go to **Review** page, view AI drafts, click **Approve** with confirmation.

### Semantics

- `ai_draft`: AI-generated draft, preview only, not in Library
- `human_approved`: Explicitly approved knowledge, in Library, Recall, Wiki
- **No automatic approval** — every approve path requires explicit confirmation

---

## Library

Browse approved knowledge cards:

```bash
mindforge library list           # List all approved cards
mindforge library show <ref>     # View card details
```

Library can show Related cards and Local Graph Preview based on deterministic source, tag, wiki section, and review batch relationships. This is local navigation, not a vector database or GraphRAG.

---

## Recall

Local BM25 lexical search:

```bash
mindforge recall --query "keyword"
```

BM25 lexical matching only — no semantic search, no RAG, no embeddings, no vector database.

---

## Knowledge Health

```bash
mindforge health
```

Knowledge Health is a read-only maintenance report for review backlog, low-quality cards, missing provenance, duplicate candidates, orphan cards, stale wiki, and suggested actions. It does not modify cards, sources, or Wiki.

---

## Wiki

### Generate

```bash
mindforge wiki status            # View Wiki status
mindforge wiki rebuild           # LLM synthesis rebuild
mindforge wiki show              # View Wiki content
```

Or click **Generate Wiki** on the Web **Wiki** page.

### How It Works

- Wiki only uses `human_approved` cards
- LLM-first synthesis: summarizes and rewrites approved cards
- Never reads raw sources (bypasses approval)
- Must be manually triggered — never runs automatically

### Configuration

```yaml
wiki:
  mode: llm                 # LLM-first synthesis
  model: main               # Model id (must reference llm.models)
  auto_rebuild_on_approve: false
```

### Troubleshooting Fallback

The Web Wiki **Advanced** section provides Safe fallback rebuild (deterministic template rebuild) for emergencies when no model is available. Not the recommended path.

---

## Web Console

Start with `mindforge web --open`, visit `http://127.0.0.1:8765`:

| Page | Purpose |
|------|---------|
| **Home** | Status overview, safety summary, next steps |
| **Setup** | Configure models, manage workflow, add sources |
| **Sources** | Manage sources, Process now, Import |
| **Review** | View AI drafts, approve or trash |
| **Library** | Browse approved knowledge cards |
| **Trash** | Safe recycle bin with Restore |
| **Recall** | Local BM25 lexical search |
| **Wiki** | LLM synthesis Wiki generation |

Port in use? Switch ports:

```bash
mindforge web --port 8766 --open
```

---

## Trash

Deleted knowledge cards go to Trash with Restore support. Manage on the Web **Trash** page.

---

## Safety

| Principle | Description |
|-----------|-------------|
| API key not in Git | `.mindforge/` gitignored, key in local secret store only |
| API key not in frontend | API returns masked values only |
| No auto-approval | All approve paths require explicit confirmation |
| Wiki from approved only | Unreviewed content never enters Wiki |
| Source file protection | Stop watching + Move to Trash don't touch source files |
| Real LLM opt-in | Model + API key + explicit trigger required |

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Model can't generate draft | Add API key in Web Setup for that model |
| Run skipped by triage | Source flagged low-value; check `runs show` |
| Running for minutes | Real model processing takes time; check `runs show` |
| Provider timed out | Check endpoint/network/proxy; split long docs or increase `timeout_seconds` |
| Already processed | Source already processed; no duplicate drafts |
| Approve ref expired | Renumber after approval; re-run `approve list` |
| Port already in use | Switch port: `mindforge web --port 8766 --open` |
| Command not found | `source .venv/bin/activate && pip install -e .` |

**Never paste API keys into chat, issues, logs, or documentation.**

---

## Known Limitations

- Suitable for non-sensitive material at small scale
- Long documents may need splitting or increased `timeout_seconds`
- No RAG, embeddings, vector database, or semantic merge
- No Obsidian plugin
- No automatic approval
