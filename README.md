# MindForge

> Local-first AI learning memory: turn scattered notes, clips, documents, and chat exports into reviewed, reusable Knowledge Cards.

MindForge is a CLI pipeline for personal knowledge processing. It scans local inbox files, normalizes them through SourceAdapters, runs a staged LLM pipeline, writes Knowledge Cards into a vault, and keeps state, run logs, recall indexes, review plans, and telemetry local.

v0.5 adds a read-only Obsidian Binding / Bridge: an Obsidian vault can be
scanned as personal knowledge context, while generated candidates go only to
staging/review and machine runtime state stays outside formal notes. v0.5.1
promotes Local Usability as a roadmap milestone: the local fake-provider path
should feel like a usable product loop, not just a set of developer commands.

Current version: **v0.7.22** — Architecture Quality Milestone in progress
(monolith decomposition: `process_service`, `approve_presenter`,
`review_presenter`; CLI adapter kept thin; presenters never mutate business
state). v0.5.2 Packaging / Install Readiness remains active (default prompts,
templates, and configs are bundled as package assets and resolved with
`importlib.resources`, while user override paths remain supported).

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

发现可用知识归纳策略（不调真实 LLM、不读 `.env`、不写 vault）：

```bash
mindforge strategies list
```

输出会列出每个内建策略的 `strategy_id` / `display_name` /
`status` / `provider_mode` / `safety_policy` / `output_schema_id` /
描述。当前内建策略：

- `default_knowledge_card`（**implemented**，离线确定性）
- `five_stage`（**implemented**，LLM 驱动，默认走 fake provider，真实
  LLM 仅显式 opt-in 时启用）
- `concept_extraction`（**preview**，离线确定性骨架；可执行但语义仍在演化）
- `action_item`（**planned**，仅登记元数据，调用 `mindforge process
  --strategy action_item` 会礼貌拒绝并提示可执行替代）

`status` 三态约定：

- `implemented`：生产可用，可执行；
- `preview`：可执行，但语义/字段集合仍在演化，不要按生产质量要求；
- `planned`：仅登记元数据，**不可执行**；执行会抛
  `NotYetImplementedStrategyError`，并明确建议 implemented 替代，绝
  不会偷偷 fallback 到 default 策略。

To try the product without using your own data:

```bash
mindforge doctor --vault examples/demo-vault
mindforge commands
mindforge next --vault examples/demo-vault
mindforge scan --vault examples/demo-vault
mindforge process --profile fake --limit 1 --vault examples/demo-vault
mindforge approve list --vault examples/demo-vault
mindforge index rebuild --vault examples/demo-vault
mindforge recall --query "checkpoint runtime" --ranking hybrid --explain --vault examples/demo-vault
mindforge review weekly --format markdown --vault examples/demo-vault
mindforge project context my-first-agent --target claude-code --vault examples/demo-vault
mindforge obsidian doctor --vault examples/demo-vault
mindforge obsidian scan --vault examples/demo-vault --limit 5
mindforge obsidian links --vault examples/demo-vault
mindforge obsidian stage --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --dry-run
```

The demo vault is fictional and safe to inspect. See [examples/demo-vault/README.md](examples/demo-vault/README.md).

## What It Does

- Ingests local sources through adapters: Cubox markdown, plain markdown, web clips, chat exports, text PDFs, docx files, and read-only Obsidian notes.
- Converts every source to a frozen `SourceDocument` contract before downstream processing.
- Runs a five-stage pipeline: triage, distill, link suggestion, review questions, action extraction.
- Writes Knowledge Cards under `20-Knowledge-Cards/`, defaulting to `status: ai_draft`.
- Requires explicit human approval before cards become `human_approved`.
- Provides local BM25/hybrid recall, review scheduling, project context packs, vault indexes, and local-only telemetry.

## What It Does Not Do

- No automatic approval of AI output.
- No remote telemetry or cloud sync.
- No complex RAG, embedding, vector database, or graph database implementation in v0.5.
- No OCR for scanned PDFs.
- No Obsidian plugin; v0.5 is CLI/adapter-level binding only.
- No automatic edits, file moves, or wikilink rewrites in a real Obsidian vault.
- No real LLM calls in the default local usability path.
- No repo-root dependency for default runtime prompts/templates/configs after
  packaged install.
- No background daemon, system calendar integration, email, or desktop notifications.

## Safety Defaults

- Default `active_profile=fake`, so `mindforge process` does not call real LLMs after clone.
- `.env` is never printed; doctor/next do not read `.env` contents.
- Raw inbox files are read-only and never modified by MindForge.
- Real Obsidian vault notes are treated as read-only until a staging/review workflow is explicitly implemented.
- Telemetry is local-only and uses a strict metadata whitelist.
- Recall indexes Knowledge Cards only, not raw source documents.
- Machine state stays in `.mindforge/` or other derived stores, not formal Obsidian notes.

See [docs/SECURITY.md](docs/SECURITY.md) for the full safety contract.

## Documentation

Start here:

- [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) - documentation map
- [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) - first successful run
- [docs/REAL_DOGFOOD_QUICKSTART.md](docs/REAL_DOGFOOD_QUICKSTART.md) - 10-minute new-user real-data dogfood loop (Cubox JSON export + project-vault dry-run; fake-default + dry-run path only)
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - daily commands and workflows
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - system shape and data flow
- [docs/SECURITY.md](docs/SECURITY.md) - boundaries and invariants
- [docs/SOURCE_ADAPTER_PROTOCOL.md](docs/SOURCE_ADAPTER_PROTOCOL.md) - adding or auditing source adapters
- [docs/OBSIDIAN_BINDING.md](docs/OBSIDIAN_BINDING.md) - v0.5 Obsidian source/staging boundary
- [docs/LLM_PROVIDER_CONFIG.md](docs/LLM_PROVIDER_CONFIG.md) - real provider setup
- [docs/LOCAL_FIRST_PRIVACY_CONTRACT.md](docs/LOCAL_FIRST_PRIVACY_CONTRACT.md) - canonical fake-default + real-opt-in privacy contract (v0.13)
- [docs/V0_13_DOGFOODING_READINESS.md](docs/V0_13_DOGFOODING_READINESS.md) - v0.13 dogfooding readiness scaffolding
- [docs/V0_13_INDUSTRY_PATTERN_MAP.md](docs/V0_13_INDUSTRY_PATTERN_MAP.md) - offline industry pattern map (OpenAI Agents SDK / LangGraph / Dify / Obsidian / Readwise / ...)
- [docs/V0_14_FUTURE_GATES.md](docs/V0_14_FUTURE_GATES.md) - v0.14/v1.0 future gate specifications (G1-G6)
- [docs/ROADMAP_COMPLETION_LEDGER.md](docs/ROADMAP_COMPLETION_LEDGER.md) - single-page Roadmap status table (pushed / future-gated / release-gated / forbidden)
- [docs/EVIDENCE_COMMANDS.md](docs/EVIDENCE_COMMANDS.md) - copy-paste evidence cookbook (10 sections; quality / fake / refusal / opt-in / preflight / approval / sweep / boundary / roadmap / push)
- Provider readiness CLI: `mindforge provider readiness` (no network, no secret print) and `mindforge provider smoke --allow-real` (gated synthetic real-LLM smoke)
- [docs/TESTING.md](docs/TESTING.md) - smoke tests and quality gates
- [docs/ROADMAP_PROGRESS.md](docs/ROADMAP_PROGRESS.md) - current completion snapshot
- [docs/CHANGELOG.md](docs/CHANGELOG.md) - version history

## Development Status

- Latest local usability milestone: `v0.5.1`.
- Latest packaging/install readiness milestone: `v0.5.2`.
- Latest architecture governance milestones (cli/presenter/service boundary
  hardening): `v0.7.20` – `v0.7.23`.
- Latest source-plugin / strategy registry / declarative custom-strategy
  milestones: `v0.10` – `v0.12`.
- Latest real-capable opt-in readiness milestone: `v0.13 Stage 1` (real
  provider opt-in is gated; default path stays fake; `human_approved`
  cannot be machine-generated). See
  [docs/LOCAL_FIRST_PRIVACY_CONTRACT.md](docs/LOCAL_FIRST_PRIVACY_CONTRACT.md)
  and `mindforge provider readiness --help`.
- Latest v0.5.1 smoke: full `examples/demo-vault` local path, including
  doctor / commands / next / scan / fake process / approve list / index /
  recall / review / project context / Obsidian dry-run.
- Latest v0.5.1 quality gate is recorded in
  [docs/V0_5_1_LOCAL_USABILITY_REVIEW.md](docs/V0_5_1_LOCAL_USABILITY_REVIEW.md).

Recommended next step after v0.13 Stage 1: keep treating real provider /
Cubox / Obsidian as opt-in surfaces; use `mindforge provider readiness`
before any opt-in attempt; never bypass approval.
