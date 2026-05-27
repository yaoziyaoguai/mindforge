# Product Main Path Real Dogfood v2 — Plan

Date: 2026-05-27
Audit reference: `docs/audits/2026-05-27-133-codex-independent-strategic-red-team-audit.md` §10.A
Task type: `dogfood`

## Goal

Run the full MindForge product main path with browser-level UX validation, recording friction points per Codex audit acceptance criteria.

## Prerequisites

- Synthetic/non-private material only (MindForge repo docs)
- No real LLM — FakeProvider only
- No real Obsidian vault write
- Browser: Chrome DevTools MCP

## Pipeline Stages

### Stage 0: Workspace Setup
- Create isolated dogfood workspace (`/tmp/mindforge-dogfood-v2`)
- Copy MindForge repo docs as source material
- Start MindForge web server with fake config

### Stage 1: Browser Walkthrough (Chrome DevTools MCP)
Navigate each page and record:
- Does the page load without errors?
- Is the main task/CTA obvious?
- Are there confusing labels, missing actions, or broken flows?
- Does the page feel like a product or an engineering console?

Pages to verify (in user workflow order):
1. **Home** (`/`) — Status overview, next action clarity
2. **Setup** (`/setup`) — Provider configuration, safety boundary
3. **Sources** (`/sources`) — Add source, import flow
4. **Review** (`/review`) — Draft review, approve/reject
5. **Library** (`/library`) — Approved cards, filters, graph/community panels
6. **Recall** (`/recall`) — Search approved knowledge
7. **Wiki** (`/wiki`) — Wiki synthesis
8. **Export** (`/export`) — Export Markdown/ZIP

### Stage 3: Friction Collection
Categorize issues into:
- **Product**: Misleading labels, unclear value prop
- **UX**: Confusing layout, missing CTAs, overload
- **Architecture**: Performance, structural issues
- **Docs**: Inconsistencies between docs and UI

### Stage 4: Gates
- `git diff --check`
- `npm --prefix web run build`
- `python -m pytest tests/test_web_product_copy.py -q --tb=short`
- `npm --prefix web run test -- --run`

## Acceptance Criteria (from Codex Audit §10.A)

- [ ] User can complete full path without reading internal docs
- [ ] Draft review is understandable and safe
- [ ] Export produces expected output
- [ ] Recall/Wiki returns useful approved-card results
- [ ] Issues are categorized into product, UX, architecture, docs

## Safety Constraints

- 不调用真实 LLM/Cubox/Upstage
- 不处理真实私人资料
- 不写真实 Obsidian vault
- 不做 RAG/embedding/vector DB
- 不破坏 explicit approval 语义
