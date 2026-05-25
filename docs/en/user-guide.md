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

### Source Location / Provenance

Each card's Library detail page shows provenance tracking information:

- **Source Location**: The card's position within its original source file (section heading + paragraph index)
- **Provenance fields**: source_id, source_path, source_type, and adapter_name are fully preserved

Source Location enables neighbor-based relationship discovery in Related Cards and provenance completeness checks in Knowledge Health.

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

## Provider Readiness

The **Provider Readiness** diagnostics report which model aliases are available, blocked, or need configuration:

- **Ready**: Model has valid API key and endpoint configuration
- **Blocked**: Missing API key, unreachable endpoint, or incompatible protocol
- **Unknown**: Not yet configured

Check on the Web **Setup** page under the Provider Readiness panel. The diagnostics never return raw API key values — keys are always masked.

---

## Processing Workflow

### Knowledge Lifecycle

Each card progresses through a defined lifecycle visible on the **Home** page:

```
Source → ai_draft → human_approved
                      ├── Library (browse/search)
                      ├── Wiki (LLM synthesis)
                      └── Recall (BM25 retrieval)
```

The Home page groups cards by source, showing how many are in each stage. Click any source to see its full Source-to-Card lifecycle timeline.

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

## Card Quality

Each knowledge card undergoes deterministic quality assessment during generation. Results are stored in the card's frontmatter.

### Scoring Dimensions

| Dimension | Description |
|-----------|-------------|
| **Completeness** | Whether the card has title, body, source references, and other required elements |
| **Structure** | Whether the card has clear sections and hierarchy |
| **Provenance** | Whether source_id, source_path, source_type, and adapter_name are fully preserved |

### Quality Levels

- **high** — All dimensions are well-covered
- **medium** — Usable, some dimensions could improve
- **low** — Significant gaps; consider regenerating or splitting

The Web Library page shows a color-coded quality badge on each card. Low-quality cards trigger Knowledge Health warnings.

## Library

Browse approved knowledge cards:

```bash
mindforge library list           # List all approved cards
mindforge library show <ref>     # View card details
```

### Related Cards

Each card's detail page shows a Related Cards panel. Relationships are computed via deterministic field matching — no embeddings or vector search:

- **same_source**: From the same source file
- **same_tag**: Share common tags
- **same_wiki_section**: Belong to the same Wiki section
- **same_review_batch**: Processed in the same batch
- **source_location_neighbor**: Adjacent positions within the same source

At most 5 results per relationship type, sorted by strength descending.

### Community Browser

The Web **Library** page supports a community browser view — knowledge cards are grouped into deterministic topic communities based on shared tags, sources, and wiki sections. Community detection is purely structural (no LLM, no embeddings). Each community shows its member cards and connection rationale.

### Local Graph Preview

The card detail page displays a 1-hop local graph centered on the current card, visualizing relationships to sources, tags, and wiki sections. Purely deterministic — no full-graph expansion, no force-directed layout engine.

### Multi-hop Relations

Related cards support multi-hop navigation — from a card, you can explore its related cards, then their related cards, forming explainable provenance trails. Each hop shows the relation type and evidence.

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

### Wiki Quality

The Wiki page footer displays a Quality Bar with the current Wiki's quality metrics:

| Metric | Description |
|--------|-------------|
| **Coverage** | Proportion of approved cards referenced by the Wiki |
| **Faithfulness** | How faithfully the Wiki content reflects source cards |
| **Staleness** | Approved cards not yet covered by Wiki (stale) |
| **Knowledge Gaps** | Knowledge gaps detected between Wiki sections |

The Quality Bar updates automatically on each Wiki rebuild. Data is stored as embedded JSON at the end of the Wiki file.

---

## Web Console

Start with `mindforge web --open`, visit `http://127.0.0.1:8765`:

| Page | Purpose |
|------|---------|
| **Home** | Status overview, safety summary, knowledge lifecycle view |
| **Setup** | Configure models, manage workflow, provider readiness check |
| **Sources** | Manage sources, Process now, Import, folder import |
| **Review** | View AI drafts, approve or trash |
| **Library** | Browse approved knowledge cards, related cards, local graph preview |
| **Recall** | Local BM25 lexical search |
| **Wiki** | LLM synthesis Wiki generation, Wiki quality bar |
| **Health** | Knowledge health diagnostics, maintenance suggestions |
| **Dogfood** | Workspace usage reports, metrics dashboard |
| **Trash** | Safe recycle bin with Restore |
| **Import/Export** | Markdown folder import, batch paste, JSON/OPML/Zip export |

Port in use? Switch ports:

```bash
mindforge web --port 8766 --open
```

---

## Import & Export

MindForge supports safe local import and export with explicit approval enforcement.

### Import

All imports create `ai_draft` only — explicit approval is never bypassed.

| Method | Description |
|--------|-------------|
| **Web Add Source** | Add a single file as a source for processing |
| **Markdown Folder Import** | Scan a folder and import all `.md` files as drafts |
| **Batch Paste Import** | Paste multiple documents separated by `---` delimiter |

Import dedup detection checks for exact title matches and fuzzy Jaccard similarity before creating new drafts. Validation runs before import to catch structural issues early.

### Export

Export knowledge cards in multiple formats:

| Format | Description |
|--------|-------------|
| **JSON** | Full card data with metadata and relations |
| **OPML** | Outline format for mind-mapping tools |
| **Zip** | Streaming zip package with `cards.md` + `manifest.json` |

All exports preserve provenance data and approval status. Use the Web **Import/Export** page to preview before downloading.

### Safety

- All imports go to `ai_draft` — never auto-approved
- Source files on disk are never modified by import
- Export never includes API keys or secret store data
- Validation runs pre-import; invalid files are rejected with clear messages

---

## Dogfood (Usage Reports)

The **Dogfood** page provides workspace usage analytics and infrastructure status:

| Section | Description |
|---------|-------------|
| **Activity Summary** | Total sources, cards, wikis, runs over time |
| **Engagement Metrics** | Approval rate, review turnaround, processing throughput |
| **Infrastructure** | Provider readiness, storage stats, index health |
| **Suggestions** | Actions based on detected patterns (stale cards, unused sources, etc.) |

Dogfood reports run entirely locally — no telemetry, no external analytics.

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
- No RAG answering, embeddings, vector database, or semantic search
- No Obsidian plugin
- No automatic approval
- Graph and community detection are deterministic only — no learned embeddings or GNN-based graph learning
- Embedded graph backend (Kuzu) is spike-only; not in production path
