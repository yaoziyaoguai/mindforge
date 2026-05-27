# MindForge Codex Independent Strategic Red Team Audit

Date: 2026-05-27
Auditor: Codex independent red-team audit
Scope: strategic product, capability, architecture, Web UX, governance, gates, and safety audit
Mode: read-only product/code audit; no product code, Web code, test code, secrets, real LLM, real private data, real Obsidian vault, RAG, embedding, vector DB, Graph expansion, or `/mf-autopilot` modifications.

## Repo Facts And Evidence Scope

Required repo facts were collected before the audit:

```text
pwd
/Users/jinkun.wang/work_space/mindforge

git status --short
(clean)

git rev-parse --abbrev-ref HEAD
main

git rev-list --left-right --count @{u}...HEAD || true
0 0
```

Recent HEAD context:

```text
e6dbe9b fix: close AUDIT-118 P1 product debt — Export docs, Dogfood nav, HANDOFF semantics, browser smoke
8507c82 docs: handoff — frontend test workstream complete (6 files/50 tests), remaining AUDIT-118 P1 debts
7acb47e test: add Breadcrumb (9) + SafetyBar (16) component tests — 6 files/50 tests
140a472 docs: update architecture.md — add mindforge_web/presenters/ + fix web_facade line count
7223203 test: expand frontend component tests — 1→4 files, 2→25 tests
91f5ec7 docs: Documentation Reset Batch 2 — DOC-01/02/03 closed, English README created
fb98003 feat: v3.7 Quality Platform — frontend tests + coverage + config env extraction
e159e29 chore: fix mf-autopilot cross-workstream continuation
ff3d210 docs: finalize hash references in state docs after Slice 2 push
70a1475 refactor: Slice 2 — extract web_facade.py private helpers to presenters
2cba857 refactor: Slice 1 — move processing run logic to core, fix core→web layer violation
c4f5c25 docs: update state docs and handoff after Architecture Quality Reset Slice 0
8eb3fd4 test: add Slice 0 architecture boundary tests for targeted quality reset
1b39edb chore: finalize HANDOFF.md with accurate repo snapshot
7844bf0 chore: update progress-ledger with final commit hash
56b3d23 chore: harden mf-autopilot auto-continue policy
6145b72 fix: reduce post-dogfood web IA debt
97d57fb feat: improve FakeProvider keyword extraction — title + raw_text
20a3038 docs: audit post-governance MindForge state
```

Mandatory documents reviewed:

- Governance: `.claude/commands/mf-autopilot.md`, `docs/dev/CURRENT_PROJECT_STATE.md`, `docs/dev/progress-ledger.md`, `docs/dev/HANDOFF.md`, `docs/dev/engineering-workflow.md`
- Recent audit and notes: `docs/audits/2026-05-27-118-post-governance-global-red-team-audit.md`, `docs/implementation-notes/2026-05-27-132-audit-118-product-debt-closure.md`, latest 10 implementation notes, latest 5 audit docs
- Product docs: `README.md`, `docs/README.md`, `docs/en/user-guide.md`, `docs/zh-CN/user-guide.md`
- Architecture docs: `docs/dev/architecture.md`, `docs/dev/quality-debt-ledger.md`

Code sampling scope:

- File population: `src/mindforge/` 215 files, `src/mindforge_web/` 59 files, `web/src/` 86 files, `tests/` 220 files.
- Sampled core modules: approval, processing, recall, wiki, library, provider setup, dogfood, import/export, safety tests.
- Sampled Web backend modules: `src/mindforge_web/services/web_facade.py`, `web_config_service.py`, `web_source_service.py`, `web_import_export_service.py`, `web_lab_service.py`, `web_recall_service.py`, `web_review_service.py`, routers, schemas, presenters.
- Sampled frontend modules: `web/src/App.tsx`, `web/src/components/Sidebar.tsx`, Home, Setup, Sources, Review, Library, Card Workspace, Recall, Wiki, Export, Health, Dogfood, Graph, Sensemaking pages, i18n, API types, component tests.
- Sampled tests: product copy, user journey smoke, architecture boundaries, approval boundaries, provider opt-in, package safety, Web component tests, Playwright smoke script.

Browser limitation:

- The `browse` skill setup check returned `NEEDS_SETUP`; no fresh browser/MCP walkthrough was performed in this audit.
- Web conclusions below are based on source review, prior documented Chrome DevTools MCP smoke evidence in `docs/implementation-notes/2026-05-27-132-audit-118-product-debt-closure.md`, and frontend/backend code inspection. They are not claimed as fresh browser QA evidence.

# 1. Executive Summary

Overall score: **6.4 / 10**

Verdict: **Conditional Go**

One-sentence truth: **MindForge 的真实战略资产仍然是 approval-first personal knowledge compiler，而不是 AI PKM/Graph/RAG；它已经具备可 dogfood 的本地主路径雏形，但真实用户喜欢度、Web 易用性、治理可信度和架构可持续性还没有被充分证明。**

Recommended primary next loop: **A. Product Main Path Real Dogfood v2**

Recommended secondary next loop: **B. Web Product UX Deepening**

Active workstream changed: **No. This audit does not take over or rewrite the current `/mf-autopilot` active workstream.**

## Top 10 Strengths

| # | Strength | Evidence | Why it matters |
|---|---|---|---|
| 1 | Approval-first boundary is real in core code. | `src/mindforge/approver.py`, `src/mindforge/approval_service.py`, `src/mindforge_web/services/web_review_service.py`, `tests/test_review_approval_boundary.py` | The product's strongest strategic difference has concrete implementation and tests. |
| 2 | Main path exists across API and Web surfaces. | `tests/test_user_journey_smoke.py`, `web/src/pages/HomePage.tsx`, `SourcesPage.tsx`, `ReviewPage.tsx`, `LibraryPage.tsx`, `RecallPage.tsx`, `WikiPage.tsx`, `ExportPage.tsx` | Source/import to review, library, recall/wiki, and export is no longer only aspirational. |
| 3 | Safety posture is stronger than a typical AI note demo. | `README.md`, `tests/test_provider_opt_in_boundary.py`, `tests/test_package_safety.py`, `src/mindforge/providers/fake.py` | Local-first, fake provider, explicit approval, and no default RAG reduce user harm. |
| 4 | AUDIT-118 P1 product debts were materially reduced. | `docs/implementation-notes/2026-05-27-132-audit-118-product-debt-closure.md` | Export docs, Dogfood nav, HANDOFF semantics, and browser smoke were not ignored. |
| 5 | WebFacade was substantially reduced from earlier architecture debt. | `docs/implementation-notes/2026-05-27-125-architecture-reset-slice2-web-facade-presenters.md`, `src/mindforge_web/services/web_facade.py` | 2163/1487-line facade debt was reduced to 922 lines through presenter extraction. |
| 6 | Architecture boundary tests now exist. | `tests/test_architecture_boundaries.py` | The repo now has executable guardrails against some core-to-web and RAG regressions. |
| 7 | Frontend test platform exists and has real component tests. | `web/package.json`, `web/src/components/__tests__/` | Vitest, Testing Library, and 6 component test files are a real base for UX gates. |
| 8 | Product copy tests protect important public claims. | `tests/test_web_product_copy.py` | Copy around approval, internal/lab visibility, and product promise is no longer fully unguarded. |
| 9 | Documentation has canonical state docs and explicit handoff semantics. | `docs/dev/CURRENT_PROJECT_STATE.md`, `docs/dev/progress-ledger.md`, `docs/dev/HANDOFF.md` | Agents have a place to discover current state instead of reading random historical notes first. |
| 10 | The repo resists fashionable but currently distracting directions. | `README.md`, `tests/test_architecture_boundaries.py` | No embedding/vector/RAG by default keeps the product closer to its approval-first wedge. |

## Top 10 Risks

| # | Risk | Severity | Evidence | Recommended remediation | Blocks next loop |
|---|---|---|---|---|---|
| 1 | Product habit is unproven. | P1 | No real-user or real-longitudinal dogfood evidence in current docs; `tests/test_user_journey_smoke.py` is API-level only. | Run Product Main Path Real Dogfood v2 with time-to-value, review friction, recall usefulness, and export completion criteria. | Yes |
| 2 | Web still exposes engineering-control-panel complexity. | P1 | `web/src/pages/LibraryPage.tsx` renders graph/community panels in the core Library; `GraphPage.tsx` and `SensemakingPage.tsx` remain routeable. | Deepen IA around the approved-card workflow; demote graph/community from core user path unless they prove recall value. | Yes |
| 3 | Governance truth is drifting again. | P1 | `docs/dev/CURRENT_PROJECT_STATE.md` audit baseline says `fb98003` while HEAD is `e6dbe9b`; `docs/dev/progress-ledger.md` has stale `(pending)` commit fields. | Tighten state doc update rules and add a lightweight consistency check for HEAD/ledger/audit index. | Yes |
| 4 | Export story is internally inconsistent. | P1 | `docs/en/user-guide.md` and `docs/zh-CN/user-guide.md` describe JSON/OPML and Library-page controls; `web/src/pages/ExportPage.tsx` offers Markdown/ZIP on `/export`; `schemas/import_export.py` says `markdown/json/opml`. | Pick one user-facing export model and align docs, schema, backend, and Web copy. | Yes |
| 5 | `WebFacade` is smaller but still an architectural hub. | P1 | `src/mindforge_web/services/web_facade.py` is 922 lines; all 19 routers import `WebFacade`. | Split route-specific facades/services after product loop identifies stable boundaries. | No |
| 6 | New service giants remain. | P2 | `web_config_service.py` 998 lines, `web_source_service.py` 713 lines, `wiki_service.py` 867 lines, `processing/run_store.py` 629 lines. | Target high-change/high-coupling modules only; avoid a broad reset before dogfood. | No |
| 7 | Schema modularization is incomplete. | P2 | `src/mindforge_web/schemas/__init__.py` still defines response/request classes and is 399 lines. | Make `schemas/__init__.py` a true barrel re-export; move remaining classes to domain schema modules. | No |
| 8 | Tests are better but still not a product-usefulness proof. | P2 | Web tests are component-only; Playwright smoke does not cover Export/Library/Wiki and was not run here. | Add page-level browser smoke for main path and keep component tests for primitives. | Yes for UX confidence |
| 9 | `/mf-autopilot` is capable but over-complex. | P2 | `.claude/commands/mf-autopilot.md` has task-type routing, queue rules, stale-window rules, stop tokens, gate policies, and banned phrases in one large command. | Add a thinner `/mf-run-next` or simplify orchestration into stable subcommands. | No |
| 10 | Real LLM opt-in readiness is not yet proven by negative tests. | P2 | Provider opt-in tests exist, but no end-to-end negative test proves Web setup cannot silently call a real LLM or leak secret values. | Add explicit negative tests before any real LLM dogfood. | Yes for real LLM loop |

# 2. Product Strategy Audit

## What MindForge Is

MindForge is currently a **local-first, approval-first personal knowledge compiler**:

- It ingests or imports source material.
- It produces `ai_draft` knowledge cards.
- It asks the human to explicitly approve drafts.
- Only `human_approved` cards become durable library knowledge.
- It lets the user recall, inspect, organize, wiki-summarize, and export approved knowledge.

Evidence:

- `README.md` describes a local-first AI knowledge library and explicitly excludes auto-approval, RAG, embedding, vector DB, GraphRAG, and Obsidian plugin ambitions.
- `src/mindforge/approver.py` only promotes `ai_draft` to `human_approved`.
- `src/mindforge_web/services/web_review_service.py` requires explicit review confirmation and only approves drafts.
- `tests/test_user_journey_smoke.py` covers API-level Source -> Draft -> Approval -> Library -> Recall -> Wiki -> Export.

## Does Approval-First Personal Knowledge Compiler Still Hold?

Verdict: **Yes, and it is still the strongest positioning.**

Why:

- The product's trust boundary is concrete in code and tests.
- This differentiates MindForge from generic AI note apps that blur model output with durable knowledge.
- The approval boundary gives a natural reason for users to review, curate, and trust the library.

But the positioning is weakened by residual graph/community/sensemaking surfaces and by Web IA that still makes MindForge feel partly like an internal engineering workbench.

Evidence:

- `web/src/pages/LibraryPage.tsx` keeps `GraphExplorer` and `KnowledgeCommunityPanel` on the core Library screen.
- `web/src/pages/GraphPage.tsx` and `web/src/pages/SensemakingPage.tsx` remain routeable lab/internal pages.
- `web/src/api/types.ts` still documents an 8-node graph ontology and fact/candidate graph language.

## Why Users Would Use It

Likely early users would use MindForge if they:

- Read many documents and want a trusted, personally approved knowledge base.
- Need provenance and review history, not just AI summaries.
- Want local-first operation and fake/local provider defaults while testing.
- Need exportable approved notes, not a locked SaaS workspace.
- Care more about durable personal memory than social/team collaboration.

Evidence:

- `README.md` and user guides emphasize local-first workflow, explicit approval, and export.
- `ExportPage.tsx` now gives a dedicated export surface.
- Recall and Wiki pages exist for approved-library reuse.

## Why Users Would Not Use It

Users may reject MindForge because:

- Setup and provider choices still expose too much machinery.
- The Web app still has lab/internal, graph, quality, health, provider, and dogfood concepts that can dilute the main workflow.
- Recall quality is likely lexical/local rather than obviously better than search.
- Export format expectations are inconsistent across docs/API/Web.
- No evidence yet proves that a real user can build a habit over several days.

Evidence:

- `docs/en/user-guide.md` and `docs/zh-CN/user-guide.md` describe export JSON/OPML and Library-page export controls, while the current Web uses `/export` Markdown/ZIP.
- `web/src/components/Sidebar.tsx` hides Dogfood under Lab, but Graph and Sensemaking are still routeable.
- `tests/web_smoke/playwright_smoke.js` covers only Home, Setup, Sources, Review, and Search; not Export, Library detail, or Wiki.

## First Real Users

Best first users:

- Solo technical knowledge workers.
- Engineers, researchers, consultants, and founders who read dense source material.
- Users who already maintain a local notes/vault workflow and value provenance.
- Users willing to review AI drafts because they distrust fully automatic summaries.

Bad first users:

- Casual note takers who want instant capture with no review.
- Team/workspace users expecting collaboration, permissions, and cloud sync.
- Users primarily seeking graph exploration, RAG chat, or vector search.
- Users who want MindForge to be a full Obsidian, Tana, or Readwise replacement.

## Can It Form A Long-Term Habit?

Current answer: **Possible, not proven.**

The habit loop would be:

1. Capture source.
2. Review drafts quickly.
3. Trust approved cards.
4. Recall or wiki-summarize later.
5. Export durable knowledge when needed.

The loop is structurally present. It is not yet proven to be pleasant, fast, or valuable enough for repeated use.

## Scores

| Dimension | Score | Verdict |
|---|---:|---|
| Product score | 6.8 / 10 | Real wedge, not yet proven lovable |
| Innovation score | 7.2 / 10 | Approval-first compiler is differentiated |
| Competitive score | 6.0 / 10 | Strong wedge, weak breadth and UX polish |

Product positioning verdict: **Continue, but narrow. MindForge should be an approval-first knowledge compiler, not a general AI PKM, graph workspace, or RAG product.**

What to double down on:

- Source/import -> `ai_draft` -> explicit approval -> `human_approved` -> Library -> Recall/Wiki -> Export.
- Fast review, strong provenance, clear safety boundary, local-first trust.
- Recall quality over graph spectacle.
- Export that makes approved knowledge portable.

What to stop doing:

- Expanding Graph/Sensemaking/Entity/Community.
- Treating docs cleanup as the primary product loop.
- Adding RAG/embedding/vector DB before lexical recall and approval value are proven.
- Building more internal/lab surfaces.
- Running architecture resets that are not tied to product pain.

# 3. Capability Audit

| Capability | Status | Evidence | User value | Current risk | Recommended action |
|---|---|---|---|---|---|
| Source / Import | Core | `web/src/pages/SourcesPage.tsx`, `src/mindforge_web/routers/sources.py`, `src/mindforge_web/services/web_source_service.py`, `src/mindforge_web/services/web_import_export_service.py` | Gives the user a way to bring material into the compiler. | `web_source_service.py` is 713 lines; source/import mental model may still be operational. | Keep core; simplify UX around "add source" and split service only when product behavior stabilizes. |
| `ai_draft` | Core | `src/mindforge/approver.py`, `src/mindforge/approval_service.py`, `tests/test_review_approval_boundary.py` | Clear draft state prevents AI output from becoming trusted knowledge automatically. | Copy and docs must keep distinguishing draft from approved knowledge. | Preserve as a hard invariant; add negative browser/API tests for no auto-approve. |
| Review / Approval | Core | `web/src/pages/ReviewPage.tsx`, `src/mindforge_web/services/web_review_service.py` | This is the product's trust engine. | Review speed and clarity are not yet proven by real users. | Make Review the highest-quality interaction in the app. |
| Library | Core | `web/src/pages/LibraryPage.tsx`, `src/mindforge/library_service.py`, `src/mindforge_web/routers/library.py` | Durable approved-card surface. | Library is crowded by graph/community panels; this weakens the core mental model. | Make approved cards and provenance primary; demote graph/community to optional/lab. |
| Recall | Core | `web/src/pages/RecallPage.tsx`, `src/mindforge/recall_service.py`, `src/mindforge_web/services/web_recall_service.py` | Lets approved knowledge become useful later. | Current quality appears lexical/local; value over ordinary search is not yet proven. | Run Recall/Search Quality Lab after real dogfood reveals recall failures. |
| Wiki | Support | `web/src/pages/WikiPage.tsx`, `src/mindforge/wiki_service.py`, `src/mindforge_web/routers/wiki.py` | Helps convert approved cards into navigable summaries. | `wiki_service.py` is 867 lines; wiki usefulness may be secondary to recall. | Keep as support; do not expand until approved-card library is valuable. |
| Export | Core | `web/src/pages/ExportPage.tsx`, `src/mindforge_web/schemas/import_export.py`, `src/mindforge_web/routers/library.py` | Makes approved knowledge portable and closes the user path. | Docs/API/Web disagree: Markdown/ZIP vs JSON/OPML vs Library-page export. | Align export model immediately in the next product or Web loop. |
| Provider setup | Support | `web/src/pages/SetupPage.tsx`, `src/mindforge_web/services/web_config_service.py`, `tests/test_provider_opt_in_boundary.py` | Lets users understand fake/local/real provider boundary. | `web_config_service.py` is a 998-line service; secret readiness claims are slightly overconfident. | Keep opt-in; add negative tests before real LLM readiness. |
| Dogfood | Internal | `web/src/pages/DogfoodPage.tsx`, `src/mindforge/dogfood/`, `docs/implementation-notes/2026-05-27-132-audit-118-product-debt-closure.md` | Useful for project self-observation. | Still routeable and exposes internal metrics such as `search_index_path`; can confuse users if surfaced. | Keep hidden under Lab/Internal; do not treat dogfood pass as user delight. |
| Web UI | Core | `web/src/App.tsx`, `web/src/components/Sidebar.tsx`, page modules | Main product experience. | No fresh browser QA in this audit; page-level tests are thin. | Run Web UX Deepening with browser evidence after dogfood. |
| Graph / Sensemaking / Entity / Community | Lab / Cut unless proven | `web/src/pages/GraphPage.tsx`, `SensemakingPage.tsx`, `web/src/api/types.ts`, `web/src/pages/LibraryPage.tsx` | Could support recall explainability in limited form. | Strong risk of pulling the product back into AI PKM/GraphRAG territory. | Freeze expansion; hide or reduce to recall support unless real dogfood proves value. |
| Documentation governance | Support | `docs/README.md`, `docs/dev/CURRENT_PROJECT_STATE.md`, `docs/dev/progress-ledger.md` | Helps agents and humans avoid stale context. | Current truth and historical notes are drifting again. | Fix only the canonical-truth drift; do not run another broad doc cleanup as primary loop. |
| `/mf-autopilot` | Internal | `.claude/commands/mf-autopilot.md`, `docs/dev/engineering-workflow.md` | Can continue workstreams with less human babysitting. | Complex command may still stop, over-route, or bury queue state in hidden comments. | Add a thinner run-next abstraction or simplify command; do not block product dogfood on this. |

# 4. Architecture & Code Quality Audit

## Scores

| Dimension | Score | Verdict |
|---|---:|---|
| Architecture | 6.2 / 10 | Improved boundaries, still facade/service-heavy |
| Code quality | 6.4 / 10 | Many solid pieces, several high-risk large modules |
| Maintainability | 6.0 / 10 | Sustainable only if next refactors are targeted |

## Core Domain Clarity

Core domain is clearer than before:

- Approval state is explicit and tested.
- Library, recall, wiki, provider, import/export, and dogfood domains are separated enough to reason about.
- RAG/vector/embedding exclusions are protected by tests.

Evidence:

- `src/mindforge/approver.py`
- `src/mindforge/approval_service.py`
- `src/mindforge/recall_service.py`
- `src/mindforge/wiki_service.py`
- `tests/test_architecture_boundaries.py`

Remaining issue:

- Several core services remain large enough that their internal responsibilities are hard to audit quickly.
- `wiki_service.py` at 867 lines and `processing/run_store.py` at 629 lines are likely future bottlenecks if Wiki/processing complexity grows.

## Application Service Cohesion

Mixed.

Healthy examples:

- `src/mindforge_web/services/web_review_service.py` has a clear approval role.
- `src/mindforge_web/services/web_recall_service.py` is comparatively small at 177 lines.
- Presenter extraction in `src/mindforge_web/presenters/` reduced private helper gravity in `WebFacade`.

Problem examples:

- `src/mindforge_web/services/web_config_service.py` is 998 lines.
- `src/mindforge_web/services/web_source_service.py` is 713 lines.
- `src/mindforge_web/services/web_facade.py` is still 922 lines.

Why it matters:

- High-change product loops will likely touch Setup, Sources, Export, and Library.
- Large services make it easy to add another branch instead of sharpening domain boundaries.

## Web Adapter Clarity

Routers are mostly thin, but thin routers all depending on one facade is not enough architectural health.

Evidence:

- All 19 `src/mindforge_web/routers/*.py` modules import `WebFacade`.
- `src/mindforge_web/routers/library.py` has meaningful export and card-detail logic and is 298 lines.
- `src/mindforge_web/routers/wiki.py` is 378 lines.

Risk:

- The facade pattern centralizes too much product surface even after helper extraction.
- Thin routers can hide a thick adapter layer.

## Schema Modularization

Improved but incomplete.

Evidence:

- Schema modules exist: `src/mindforge_web/schemas/import_export.py`, `library.py`, `setup.py`, etc.
- `src/mindforge_web/schemas/__init__.py` remains 399 lines and still defines multiple request/response classes directly.

Verdict:

- This is not a pure barrel module yet.
- It is no longer the worst debt, but it still blurs ownership.

## `web_facade.py` Health

Current verdict: **reduced, not healthy.**

Evidence:

- `src/mindforge_web/services/web_facade.py` is now 922 lines.
- Public method surface remains broad: home, setup, sources, watch, library, provenance, lab graph/sensemaking, quality, import, drafts, recall, safety, dogfood, provider, lifecycle.
- `docs/implementation-notes/2026-05-27-125-architecture-reset-slice2-web-facade-presenters.md` confirms presenter extraction from prior 1487-line state.

Why it matters:

- The facade still anchors too many routes and product concepts.
- It can become the place every new Web feature lands.

Recommended remediation:

- Do not start a broad v4.8 reset immediately.
- After Product Main Path Real Dogfood v2, split only the surfaces that real product work touches most: config/setup, export/library, sources/import, dogfood/lab.

Blocks next loop: **No**, unless the next loop is a broad Web rewrite.

## Fake/Local/Dogfood Pollution

Verdict: **mostly contained, but not fully invisible.**

Evidence:

- Dogfood is hidden under a collapsed Lab section in `web/src/components/Sidebar.tsx`.
- `web/src/pages/DogfoodPage.tsx` still displays internal metrics and uses hardcoded Chinese/internal warning copy.
- `src/mindforge_web/services/web_facade.py` still owns `dogfood_report`, despite `src/mindforge_web/services/web_dogfood_service.py` existing.

Recommended remediation:

- Keep dogfood internal.
- Move dogfood report assembly out of `WebFacade` when touching Web services next.

## Lab/Internal Pollution

Verdict: **still a product risk.**

Evidence:

- `web/src/pages/GraphPage.tsx` and `web/src/pages/SensemakingPage.tsx` remain routeable.
- `web/src/pages/LibraryPage.tsx` keeps graph/community on a core page.
- `web/src/api/types.ts` still describes an 8-node graph ontology and fact/candidate graph.

Why it matters:

- Users may infer MindForge is a graph/sensemaking product.
- Agents may re-expand Graph/Sensemaking because code and types still look first-class.

Recommended remediation:

- Freeze Graph/Sensemaking/Entity/Community expansion.
- Decide whether Library graph/community are support affordances or lab-only.
- Remove or rewrite over-promising type comments.

## Approval Semantics Protection

Verdict: **strong in core, needs more end-to-end negative tests.**

Evidence:

- `src/mindforge/approver.py` promotes only `ai_draft`.
- `src/mindforge_web/services/web_review_service.py` requires confirmation and source review.
- `tests/test_review_approval_boundary.py` and `tests/test_provider_opt_in_boundary.py` exist.

Risk:

- Current tests are stronger at unit/API level than browser workflow level.
- Real LLM readiness needs negative tests proving no implicit model call and no secret leak from Web setup paths.

## Top Architecture Risks

| Risk | Severity | Evidence | Recommended remediation | Blocks next loop |
|---|---|---|---|---|
| WebFacade remains a multi-domain hub. | P1 | `src/mindforge_web/services/web_facade.py` 922 lines, imported by all routers. | Split only along product-proven seams after dogfood. | No |
| Config/setup service is a new giant. | P1 | `web_config_service.py` 998 lines. | Extract provider readiness, secret display/masking, and config persistence if Setup loop touches it. | No |
| Sources service is too broad. | P2 | `web_source_service.py` 713 lines. | Separate source discovery/import/watch concerns. | No |
| Schema barrel still defines models. | P2 | `schemas/__init__.py` 399 lines. | Move remaining definitions to named schema modules. | No |
| Library mixes product core with graph/community. | P1 | `LibraryPage.tsx`, backend graph/community schemas. | Demote or prove these panels through dogfood. | Yes for UX loop |
| Architecture tests preserve some debt. | P2 | `tests/test_architecture_boundaries.py` allows known graph/web facade exceptions. | Convert exceptions to tracked debt with expiration criteria. | No |
| Export API contract unclear. | P1 | `ExportCardsRequest.format` vs Web Markdown/ZIP. | Align backend schema and user-facing export choices. | Yes |
| Internal dogfood remains in facade. | P3 | `WebFacade.dogfood_report`. | Move to dogfood service when nearby code is touched. | No |
| Frontend manual routing may get brittle. | P3 | `web/src/App.tsx` path-condition routing. | Leave alone unless navigation complexity grows. | No |
| Core service size may slow future changes. | P2 | `wiki_service.py`, `run_store.py`, `recall_service.py`. | Refactor only when real feature work identifies pressure. | No |

## Top Modules To Refactor

1. `src/mindforge_web/services/web_config_service.py`
   Reason: 998-line setup/config/secret/provider concentration.

2. `src/mindforge_web/services/web_facade.py`
   Reason: still broad route hub; refactor only by extracting proven product domains.

3. `src/mindforge_web/services/web_source_service.py`
   Reason: source/import/watch concerns are likely to change in dogfood.

4. `src/mindforge_web/schemas/__init__.py`
   Reason: still contains concrete schema definitions.

5. `web/src/pages/LibraryPage.tsx`
   Reason: central product page still mixes approved cards with graph/community surfaces.

## Top Modules To Leave Alone

1. `src/mindforge/approver.py`
   Reason: core approval invariant is simple and valuable.

2. `src/mindforge_web/services/web_review_service.py`
   Reason: approval semantics are clear and bounded.

3. `src/mindforge/providers/fake.py`
   Reason: fake provider is central to safe dogfood.

4. `web/src/components/Breadcrumb.tsx`, `SafetyBar.tsx`, `EmptyState.tsx`, `ErrorState.tsx`, `LoadingSkeleton.tsx`, `StatusCard.tsx`
   Reason: newly tested primitives should remain stable unless UX loop requires changes.

5. `tests/test_provider_opt_in_boundary.py` and `tests/test_review_approval_boundary.py`
   Reason: these are high-value safety tests.

## Recommended Architecture Roadmap

1. Do **not** run a broad global architecture reset as the next primary loop.
2. First run Product Main Path Real Dogfood v2 and collect actual friction.
3. Then perform a targeted architecture reset on the modules touched by the dogfood/Web UX loop.
4. Make the first reset acceptance criteria concrete:
   - `WebFacade` loses one route family.
   - `web_config_service.py` drops below a clear responsibility boundary.
   - `schemas/__init__.py` becomes a true re-export module.
   - Graph/lab types are not first-class on the main path.

# 5. Web Design / Usability Audit

## Scores

| Dimension | Score | Verdict |
|---|---:|---|
| Web design | 6.4 / 10 | Visually more product-like than before, still uneven |
| Usability | 5.8 / 10 | Main path exists, cognitive load remains high |
| IA / cognitive load | 5.5 / 10 | Too many concepts compete with approval-first flow |

## Evidence Limitation

Fresh browser/MCP evidence was not available in this audit because the browse setup check returned `NEEDS_SETUP`. This section is based on source inspection and prior recorded smoke evidence in `docs/implementation-notes/2026-05-27-132-audit-118-product-debt-closure.md`.

## Page-Level Audit

| Page | Verdict | Evidence | Issue | Recommended action |
|---|---|---|---|---|
| Home | Supportive | `web/src/pages/HomePage.tsx`, `web/src/App.tsx` status loading | Likely communicates product state, but may still show operational health more than next action. | Make next primary action obvious: add source, review drafts, search approved library. |
| Setup | Necessary but heavy | `web/src/pages/SetupPage.tsx`, `web_config_service.py` | Provider, secret, readiness, and local/real boundaries are complex. | Treat Setup as first-run trust education, not a config console. |
| Sources | Core but operational | `web/src/pages/SourcesPage.tsx`, `web_source_service.py` | Source/watch/import complexity may overwhelm new users. | Make "add/import source" the clear CTA; hide maintenance details. |
| Review | Core | `web/src/pages/ReviewPage.tsx`, `web_review_service.py` | This should be the highest-polish page; current evidence is code-level, not user-tested. | Optimize for fast confident approve/reject/edit. |
| Library | Overloaded | `web/src/pages/LibraryPage.tsx` | Graph/community panels compete with approved-card library. | Make cards, provenance, and next recall/export actions primary. |
| Card detail / workspace | Useful support | `web/src/pages/CardWorkspacePage.tsx`, `CardDetailPage.tsx` | Likely valuable for provenance and editing. | Keep focused on card trust and source context. |
| Recall | Strategically important | `web/src/pages/RecallPage.tsx`, `web_recall_service.py` | Needs quality proof; lexical search may not impress. | Measure recall success in dogfood before adding AI/RAG. |
| Wiki | Support | `web/src/pages/WikiPage.tsx` | Could be useful, but risks becoming another surface before Library habit is proven. | Keep secondary until real library use exists. |
| Export | Product-critical but inconsistent | `web/src/pages/ExportPage.tsx`, `docs/en/user-guide.md`, `schemas/import_export.py` | Web says Markdown/ZIP; docs/API mention JSON/OPML. | Align the export promise and UI. |
| Health | Internal/support | `web/src/pages/HealthPage.tsx` | Useful for development and safety but not primary user value. | Keep available but not emphasized for normal users. |
| Lab/Internal | Still visible by URL | `GraphPage.tsx`, `SensemakingPage.tsx`, `DogfoodPage.tsx` | Lab concepts remain routeable and can mislead agents/users. | Freeze expansion and reduce from core IA. |

## Direct Answers

Does each page make the main task obvious?

- Home/Review/Export likely do better now.
- Library, Setup, Sources, and Lab pages remain concept-heavy.

Are CTAs clear?

- Export appears to have clear Markdown/ZIP actions.
- Sources and Review need browser dogfood confirmation.
- Library CTA hierarchy is diluted by graph/community panels.

Is information overloaded?

- Yes, especially Library, Setup, Health, Graph, Sensemaking, Dogfood.

Do users understand the safety boundary?

- Better than before, because product copy and safety bars exist.
- Still needs end-to-end browser validation for first-run users.

Is Export clear?

- The Web Export page is clearer than prior Library-hidden export.
- The overall export story is not clear because docs/API/Web disagree.

Are Dogfood/internal surfaces downgraded?

- Partially. Dogfood is under collapsed Lab/Internal navigation.
- Graph/Sensemaking remain routeable and Library still contains graph/community.

Does Web now look like a knowledge product?

- Partly. The shape is closer to a knowledge product than a CLI wrapper.
- The information architecture still feels like an engineering console in several places.

## Top UX Issues

| Issue | Severity | Evidence | Why it matters | Recommended remediation | Blocks next loop |
|---|---|---|---|---|---|
| Library is not purely an approved knowledge home. | P1 | `web/src/pages/LibraryPage.tsx` graph/community panels | Users may not know whether the product is cards, graph, or communities. | Move graph/community behind progressive disclosure or Lab until proven. | Yes |
| Export contract inconsistency. | P1 | Web Markdown/ZIP vs docs/API JSON/OPML | A user cannot form a reliable mental model of what export does. | Align copy, docs, API schema, and UI. | Yes |
| Setup likely feels like infrastructure. | P2 | `SetupPage.tsx`, `web_config_service.py` | First-run trust can become configuration anxiety. | Rewrite around safe default, opt-in real provider, and next action. | No |
| Lab/Internal pages still look first-class by URL. | P2 | `GraphPage.tsx`, `SensemakingPage.tsx`, `DogfoodPage.tsx` | Agents and power users may revive deprecated directions. | Add clear route-level lab framing and avoid main-path links. | No |
| No fresh browser evidence in this audit. | P2 | `browse` setup `NEEDS_SETUP` | Source review cannot catch layout, loading, or interaction issues. | Run browser smoke after dev server setup. | Yes for UX confidence |

## Recommended Web Roadmap

1. Use Product Main Path Real Dogfood v2 to collect actual screen-by-screen friction.
2. Fix Export contract and Library IA first.
3. Add page-level tests for Home -> Setup -> Sources -> Review -> Library -> Recall -> Wiki -> Export.
4. Do not polish Graph/Sensemaking.
5. Do not add more visual decoration before task clarity is proven.

# 6. Competitive / Industry Comparison

## Obsidian / Logseq

What MindForge should learn:

- Local-first trust.
- File/export portability.
- Fast navigation and durable linking.
- A sense that the user owns the library.

What MindForge should not copy:

- Plugin sprawl.
- Graph-as-product theater.
- Expecting users to manually maintain every structure.

Current verdict:

- MindForge should complement, not replace, Obsidian/Logseq.
- The export path should make approved cards portable to a local vault-like system, but MindForge should not become an Obsidian plugin project now.

## Readwise / Reader

What MindForge should learn:

- Capture -> inbox -> review cadence.
- Low-friction resurfacing.
- A clear habit loop.

What MindForge should not copy:

- Passive capture without trust boundary.
- Cloud-first assumptions.
- User-visible queues that do not explain why review matters.

Current verdict:

- MindForge's closest product loop should be Readwise-like review, but with stronger explicit approval and local-first semantics.

## Tana

What MindForge should learn:

- Structured knowledge can be powerful when schema supports work.
- The best structured tools make repeated workflows fast.

What MindForge should not copy:

- Schema-first cognitive load.
- Power-user ontology before user value.
- Turning every note into a type system problem.

Current verdict:

- Entity/community/type expansion should stay frozen unless dogfood proves a narrow need.

## AI PKM / RAG / GraphRAG-like Systems

What MindForge should learn:

- Users want answers from their knowledge.
- Explainability and provenance matter.
- Search quality must become visibly useful.

What MindForge should not copy:

- Blurring generated candidates with facts.
- Adding embedding/vector DB before user need is proven.
- Selling a graph/RAG story when the differentiator is approval.

Current verdict:

- MindForge should continue no embedding/no vector/no RAG for now.
- Real LLM opt-in can be prepared, but only after negative tests and explicit user decision.

Most unique point:

**Approval-first compilation of personal knowledge into a trusted, local, exportable library.**

Is it worth continuing?

**Yes, conditionally.** The wedge is real, but the next 1-2 weeks must prove repeated product value, not add breadth.

# 7. Governance / Autopilot Audit

## Scores

| Dimension | Score | Verdict |
|---|---:|---|
| Governance | 5.7 / 10 | Better process, still truth drift |
| Autopilot maturity | 6.4 / 10 | Capable, complex, not yet overnight-safe without constraints |

## CURRENT_PROJECT_STATE.md

Verdict: **useful but not fully trustworthy.**

Evidence:

- `docs/dev/CURRENT_PROJECT_STATE.md` records recent AUDIT-118 closure and queue markers.
- It still states an audit baseline HEAD of `fb98003`, while current HEAD is `e6dbe9b`.
- Its visible next-loop list after "AUDIT-118 全部 P1 项已关闭。按推荐顺序:" is blank, while actionable queue data exists mainly in hidden HTML comments.

Why it matters:

- Agents are told to read this first.
- If the canonical state doc drifts, `/mf-autopilot` can choose the wrong starting point.

Recommended remediation:

- Keep active workstream untouched in this audit.
- Add or enforce a low-cost canonical state consistency check after commits.

## progress-ledger.md

Verdict: **directionally useful, mechanically stale.**

Evidence:

- `docs/dev/progress-ledger.md` has a current active workstream section for Quality Platform / Frontend Test Coverage.
- It includes stale commit placeholders such as `(pending)` for work that appears committed.
- It reports gate evidence not perfectly aligned with implementation note 132.

Why it matters:

- The ledger is supposed to be an audit trail, not just a narrative.
- Small mismatches weaken trust in automation.

Recommended remediation:

- Append concise audit-complete entries.
- Avoid rewriting active workstream unless the current loop explicitly owns it.
- Add explicit "source of truth" for gate evidence.

## HANDOFF.md

Verdict: **status semantics are improved, content can still confuse if ignored improperly.**

Evidence:

- `docs/dev/HANDOFF.md` now has a `status: resolved` style instruction and says to ignore inactive next instructions.
- It still contains stale repo snapshot/context from earlier AUDIT-118 work.

Recommended remediation:

- Keep the status semantics.
- Do not rely on handoff content when status is resolved.

## `/mf-autopilot`

Verdict: **powerful, but over-complex.**

Evidence:

- `.claude/commands/mf-autopilot.md` includes required reads, task type routing, active workstream, loop queue, stale-window reconciliation, low-context handoff, hard stops, gates, push, and banned soft-stop phrases.

Why past loops often stopped:

- Spec loops and commit/push loops historically treated "documented" or "pushed" as completion.
- Active workstream intent was not always explicit enough.
- Documentation and state truth drifted after commits.

Does it now prevent "spec written then stop"?

- Better than before, because the command explicitly bans soft-stop phrases and requires ACTION tokens.
- Not guaranteed, because the command is long and cognitively heavy.

Does it prevent "commit/push then stop"?

- Better than before; auto-continue policy exists.
- Still depends on state docs staying fresh and queue rules being visible.

Is active workstream clear?

- Partially. Hidden markers are clear enough for an agent, but visible prose is not clear enough for a human.

Is it ready for overnight loops?

- **Conditional only.** It can run bounded implementation loops, but not strategic loops, broad architecture resets, or product-direction decisions without a human decision point.

Does it need `/mf-run-next`?

- Yes, likely. A thinner command that reads state, chooses the next queue item, executes one loop, records evidence, and exits would reduce command complexity.

## Top Process Risks

| Risk | Severity | Evidence | Required process fix |
|---|---|---|---|
| Canonical state drift. | P1 | `CURRENT_PROJECT_STATE.md` stale HEAD. | Add HEAD/ledger/audit consistency check to completion template. |
| Hidden queue is clearer than visible queue. | P1 | Queue markers in HTML comments; visible ordered list blank. | Keep hidden markers but add visible next-action summary. |
| Gate evidence drift. | P2 | Ledger and implementation notes differ on some gate claims. | Record exact command, exit code, and source note path in one place. |
| Autopilot command size. | P2 | `.claude/commands/mf-autopilot.md` combines many policies. | Add `/mf-run-next` or split command by task type. |
| Handoff stale content. | P3 | `HANDOFF.md` stale snapshot but resolved status. | Treat resolved handoff as historical only. |

# 8. Test / Gate Reliability Audit

## Scores

| Dimension | Score | Verdict |
|---|---:|---|
| Test quality | 6.8 / 10 | Stronger safety/product-copy base; weak page-level UX proof |
| Gate reliability | 6.3 / 10 | Better exact gates, still vulnerable to stale narrative evidence |

## Python Tests

Evidence:

- `tests/test_user_journey_smoke.py` covers the API-level main path.
- `tests/test_review_approval_boundary.py` protects approval semantics.
- `tests/test_provider_opt_in_boundary.py` protects provider opt-in.
- `tests/test_package_safety.py` protects package/secrets exclusion.
- `tests/test_architecture_boundaries.py` guards architecture constraints and no-RAG dependencies.

Verdict:

- Python tests provide meaningful safety and architecture confidence.
- They do not prove product delight or browser usability.

## Frontend Tests

Evidence:

- `web/src/components/__tests__/` includes tests for Breadcrumb, EmptyState, ErrorState, LoadingSkeleton, SafetyBar, StatusCard.
- `web/package.json` has Vitest, Testing Library, happy-dom, Playwright scripts.

Verdict:

- Good foundation.
- Current frontend tests are mostly component primitives, not page-level workflows.

## Product Copy Tests

Evidence:

- `tests/test_web_product_copy.py` protects product copy around safety, internal/lab, and route labels.

Verdict:

- Valuable.
- Static copy tests can also freeze suboptimal wording if not paired with UX review.

## Browser/MCP Smoke

Evidence:

- Prior browser smoke is recorded in `docs/implementation-notes/2026-05-27-132-audit-118-product-debt-closure.md`.
- `tests/web_smoke/playwright_smoke.js` exists but covers Home, Setup, Sources, Review, and Search only.
- This audit did not run browser QA because `browse` setup returned `NEEDS_SETUP`.

Verdict:

- Browser evidence is not strong enough for Web usability confidence.

## Architecture Boundary Tests

Evidence:

- `tests/test_architecture_boundaries.py`

Strength:

- It catches forbidden RAG/vector/embedding dependencies.
- It catches core-to-web direction problems.

Weakness:

- Some exceptions preserve existing debt, including lab/graph and WebFacade public methods.
- A test that locks a giant public surface can become an anti-refactor anchor.

## Gate Evidence Quality

Evidence:

- Implementation notes increasingly record exact gates.
- `docs/implementation-notes/2026-05-27-132-audit-118-product-debt-closure.md` records exact commands and exit codes for diff/build/product-copy tests.
- `docs/dev/progress-ledger.md` has some stale pending commit fields and gate mismatch risk.

Verdict:

- Better than earlier tail/head/truncated patterns.
- Still needs consistency between implementation notes, ledger, and current state.

## Missing Tests

1. Page-level browser smoke for Home -> Setup -> Sources -> Review -> Library -> Recall -> Wiki -> Export.
2. Negative test proving no implicit real LLM call from Web setup/import/review without explicit opt-in.
3. Negative test proving Web/API never exposes raw secrets.
4. Test proving `human_approved` cannot be produced outside explicit review/approval paths.
5. Export contract tests aligning Web choices with backend response/schema and docs.
6. Test that Lab/Internal pages are not first-class in main navigation.
7. Recall quality regression tests using approved-card fixtures.
8. Governance consistency check for current HEAD, ledger latest entry, and audit index.

## Low-Value / Risky Tests

| Test area | Risk | Recommended action |
|---|---|---|
| Static copy tests that encode current lab language | Can freeze rough product wording. | Keep but update after UX decisions. |
| Architecture allowlists for known violations | Can normalize debt. | Add expiration criteria or comments pointing to planned retirement. |
| WebFacade method contract test | Can preserve giant facade shape. | Narrow to required external API or convert into route-level smoke. |
| Browser smoke without full main path | Gives false confidence. | Extend to Library/Wiki/Export and report exact exit codes. |

## Recommended Minimum Gates

For docs-only work:

- `git diff --check`
- `ruff check docs/ .claude/commands/` when meaningful
- `python -m pytest tests/test_web_product_copy.py -q --tb=short`

For Product Main Path Real Dogfood v2:

- `python -m pytest tests/test_user_journey_smoke.py tests/test_review_approval_boundary.py tests/test_provider_opt_in_boundary.py tests/test_package_safety.py -q --tb=short`
- `python -m pytest tests/test_web_product_copy.py -q --tb=short`
- `npm --prefix web run build`
- `npm --prefix web run test -- --run`
- A browser smoke covering the full main path, with exact command and exit code.

# 9. Safety / Approval Semantics Audit

Safety verdict: **CONDITIONAL**

The core approval semantics pass the current audit. The conditional status is because real LLM readiness, Web setup, secret exposure, export/vault safety, and lab fact/candidate boundaries need stronger negative end-to-end tests before broader dogfood.

## Approval Boundary

Verdict: **strong.**

Evidence:

- `src/mindforge/approver.py` only promotes `_PROMOTABLE_STATUS = "ai_draft"` to `_TARGET_STATUS = "human_approved"`.
- `src/mindforge_web/services/web_review_service.py` requires `confirm` and reviewed source context.
- `tests/test_review_approval_boundary.py` covers approval boundary behavior.

Risk:

- Browser-level negative tests are still missing.

## Auto-Approve Risk

Verdict: **low in core, still needs end-to-end protection.**

Evidence:

- Core approval path is explicit.
- Product docs reject auto-approval.

Required negative test:

- API and Web workflow attempts to create `human_approved` without explicit review action must fail.

## Fake Provider Default / Real LLM Opt-In

Verdict: **mostly safe.**

Evidence:

- `src/mindforge/providers/fake.py`
- `tests/test_provider_opt_in_boundary.py`
- `README.md` warns no default real LLM.

Risk:

- Real provider readiness is not yet a product loop. Do not run real LLM dogfood until opt-in and negative tests are complete.

## Secrets / `.env`

Verdict: **mostly safe, with one semantic concern.**

Evidence:

- This audit did not read `.env`, secrets, or `src/mindforge/assets/.mindforge/secrets.json`.
- `tests/test_package_safety.py` protects packaging exclusions.
- `src/mindforge/providers/secret_store.py` masks and stores secrets locally.

Concern:

- `SecretStore.present()` calls `get()`, which reads the raw secret internally to return a boolean.
- `model_setup_readiness.py` says readiness checks do not read raw key value. The value is not exposed, but the implementation semantics are less strict than the wording.

Recommended remediation:

- Add a metadata-only presence check if the safety copy promises no raw-value read.

## Export Safety

Verdict: **safe enough for local approved-card export, contract unclear.**

Evidence:

- `ExportPage.tsx` focuses on approved-card export.
- Backend export routes are local.

Risk:

- Format mismatch can cause users to misunderstand what leaves the system.

Required negative tests:

- Export should include only intended approved cards.
- Export should not include secrets or hidden internal paths.

## Obsidian Write Safety

Verdict: **safe by absence.**

Evidence:

- No real Obsidian write was performed in this audit.
- README explicitly says no Obsidian plugin ambition.

Risk:

- Docs or future loops may reintroduce vault write assumptions.

Recommended remediation:

- Keep real vault writes out of automatic loops.
- Require explicit user path and dry-run preview before any future vault write feature.

## Graph / Sensemaking Fact Boundary

Verdict: **conditional.**

Evidence:

- `web/src/api/types.ts` still comments on fact graph + candidate graph and 8 node types.
- Lab pages remain routeable.

Risk:

- Users or agents may treat candidates/communities/entities as confirmed knowledge.

Recommended remediation:

- Keep Graph/Sensemaking lab-only.
- Remove over-promising comments/copy.
- Add tests that candidate outputs are labeled as candidates where displayed.

## P0/P1 Safety Risks

| Risk | Severity | Evidence | Required action |
|---|---|---|---|
| No P0 safety issue found. | P0 | Evidence insufficient for P0. | Continue current boundaries. |
| Real LLM opt-in not fully protected by end-to-end negative tests. | P1 | Provider tests exist; Web end-to-end negative tests are missing. | Add negative tests before real LLM loop. |
| Export could include unintended data if contract stays vague. | P1 | Export docs/API/Web mismatch. | Align contract and test approved-only export. |
| Graph/candidate surfaces can imply facts. | P1 | Routeable lab pages and graph type comments. | Keep lab-only and label candidate status. |

Required negative tests:

1. No real LLM call without explicit provider opt-in and key.
2. No raw secret appears in API responses, logs, Web props, or exported files.
3. No card becomes `human_approved` without explicit approval.
4. Export includes only selected/approved user-visible card fields.
5. Graph/Sensemaking candidate outputs cannot be rendered as confirmed facts.

# 10. Recommended Roadmap

## A. Product Main Path Real Dogfood v2

Value:

- Directly tests whether MindForge is useful and habit-forming.

Risk:

- Can expose that recall/review/export are less valuable than expected.

Effort:

- Medium.

Prerequisites:

- Use synthetic or explicitly approved non-private material.
- No real LLM unless separately approved.
- No real Obsidian write.

First loop:

- Run a complete source/import -> draft -> review -> approval -> library -> recall/wiki -> export session.
- Record friction, time-to-value, abandoned steps, confusing copy, and where user trust improves or breaks.

Acceptance criteria:

- User can complete full path without reading internal docs.
- Draft review is understandable and safe.
- Export produces expected output.
- Recall/Wiki returns useful approved-card results.
- Issues are categorized into product, UX, architecture, and docs.

Can `/mf-autopilot` run it automatically?

- **Partially.** It can run scripted synthetic dogfood and record evidence. It should not decide product positioning or use real private data automatically.

## B. Web Product UX Deepening

Value:

- Converts the existing Web app from engineering console toward a product experience.

Risk:

- Can become visual polish if not anchored in main path.

Effort:

- Medium.

Prerequisites:

- Dogfood friction list from roadmap A.
- Browser setup available.

First loop:

- Fix Library IA, Export contract, Setup clarity, and full main-path page smoke.

Acceptance criteria:

- Main tasks and CTAs are obvious on every core page.
- Lab/internal pages are not perceived as the product.
- Browser smoke covers Home, Setup, Sources, Review, Library, Recall, Wiki, Export.

Can `/mf-autopilot` run it automatically?

- **Yes, if scoped to a concrete UX checklist with browser gates.**

## C. Recall/Search Quality Lab

Value:

- Makes approved knowledge actually useful after creation.

Risk:

- Can drift into RAG/embedding/vector work too early.

Effort:

- Medium to high.

Prerequisites:

- Approved-card fixture set from real dogfood.
- Clear no-RAG/no-vector constraint unless user explicitly changes strategy.

First loop:

- Build recall quality fixtures and measure lexical recall failures.

Acceptance criteria:

- Queries from dogfood have expected card hits.
- Recall explanations are understandable.
- No embedding/vector/RAG dependency added.

Can `/mf-autopilot` run it automatically?

- **Yes for fixture-based quality loops; no for strategic RAG decision.**

## D. Targeted Architecture Quality Reset

Value:

- Reduces future change cost where product loops actually hurt.

Risk:

- Can become architecture work for its own sake.

Effort:

- Medium to high.

Prerequisites:

- Product/Web loop identifies hot modules.

First loop:

- Split one route family out of `WebFacade` and reduce one service giant without changing behavior.

Acceptance criteria:

- No product behavior change.
- Tests remain green.
- A specific module's responsibility becomes smaller and easier to explain.

Can `/mf-autopilot` run it automatically?

- **Yes if scoped to one slice; not as broad global reset.**

## E. Real LLM Opt-In Readiness

Value:

- Enables higher-quality draft generation and more realistic product evaluation.

Risk:

- Can violate safety/trust if secrets, external calls, or user expectations are mishandled.

Effort:

- Medium.

Prerequisites:

- User decision to allow real LLM opt-in work.
- Negative safety tests for no implicit external calls and no secret leakage.

First loop:

- Add readiness checks and negative tests without calling real providers.

Acceptance criteria:

- Fake/local path remains default and safe.
- Real provider path requires explicit setup.
- Tests prove no real LLM call occurs without opt-in.

Can `/mf-autopilot` run it automatically?

- **Only for test/readiness code. It must not call real LLM or handle real secrets automatically.**

## F. Documentation/Governance Cleanup If Still Needed

Value:

- Restores trust in canonical state docs.

Risk:

- Can consume time without improving product.

Effort:

- Low to medium.

Prerequisites:

- Exact cleanup rules.

First loop:

- Fix current-truth drift only: HEAD, audit index, latest notes, visible queue summary.

Acceptance criteria:

- `CURRENT_PROJECT_STATE.md`, `progress-ledger.md`, and `docs/README.md` agree on current state.
- Active workstream is not accidentally changed.

Can `/mf-autopilot` run it automatically?

- **Yes, for narrow canonical-truth cleanup.**

## Recommended Order

Primary next loop: **A. Product Main Path Real Dogfood v2**

Secondary next loop: **B. Web Product UX Deepening**

Tertiary loop: **D. Targeted Architecture Quality Reset**, but only after A/B identify real pressure.

What not to do next:

- Do not resume Graph/Sensemaking/Entity/Community expansion.
- Do not add RAG, embedding, vector DB, or GraphRAG.
- Do not start a broad v4.8 architecture reset before product dogfood.
- Do not make Documentation Reset Batch 2 the primary loop unless the user explicitly chooses governance cleanup.
- Do not call real LLMs or write real Obsidian vaults in automation.

What requires user decision:

- Whether to permit real LLM opt-in readiness.
- Whether Graph/Sensemaking should be cut further or kept as hidden lab.
- Whether Export should support Markdown/ZIP only or also JSON/OPML as user-facing formats.
- Whether `/mf-autopilot` should get a simplified `/mf-run-next` command.

# 11. Final Verdict

MindForge is worth continuing **conditionally**.

It should continue as:

> An approval-first, local-first personal knowledge compiler that turns source material into human-approved, reusable, exportable knowledge.

The next 1-2 weeks should focus on:

1. Product Main Path Real Dogfood v2.
2. Web Product UX Deepening based on real friction.
3. Targeted architecture cleanup only where the product loop exposes pain.

Directions to freeze:

- Graph/Sensemaking/Entity/Community expansion.
- RAG, embedding, vector DB, GraphRAG.
- Obsidian plugin/vault-write automation.
- Broad architecture reset without product evidence.
- Generic visual polish detached from main workflow.

Capabilities to cut or hide further:

- First-class Graph/Sensemaking pages unless kept explicitly lab-only.
- Community/entity surfaces on the core Library page unless proven useful.
- Internal dogfood details from normal user navigation.

Capabilities to deepen:

- Review/approval quality.
- Recall usefulness over approved knowledge.
- Export clarity and portability.
- Setup trust boundary.
- Page-level Web workflow tests.
- Canonical governance truth.

Final strategic judgment:

**The product has a real wedge, but it will fail if it keeps acting like a broad AI knowledge workbench. The next loop must prove that a human can repeatedly compile, trust, retrieve, and export approved knowledge with less cognitive load than maintaining notes manually.**
