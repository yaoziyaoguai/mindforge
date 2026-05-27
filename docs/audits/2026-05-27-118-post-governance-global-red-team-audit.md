# Post-Governance Global Red Team Audit

Date: 2026-05-27
Audit baseline HEAD: `7312245`
Task type: `audit_only`
Scope: read-heavy global red team audit plus documentation/status updates only.

## Executive Summary

**Overall score: 6.1 / 10**

**Verdict: Conditional Go**

**One-sentence truth:** MindForge 现在不是成熟的 PKM 或 AI workspace，而是一个安全边界较强、能在 fake/local 环境跑通的 approval-first 知识卡片编译器；它最缺的不是更多功能，而是真实主路径 dogfood、前端可用性证据，以及把文档/架构债从“标记已解决”变成真实收敛。

**Recommended next workstream:** D. Product Main Path Real Dogfood.

这轮不建议继续自由推进 Documentation Reset Batch 2。Batch 2 只能在明确 archive/delete 规则后做小范围处理；当前更高价值的下一轮是用安全、隔离、可复现的数据跑真实主路径，并用结果驱动 Web IA 和架构收敛。

### Top 10 Issues

1. **Export 真实状态与用户文档冲突。** `web/src/pages/ExportPage.tsx` 和 `/export` 已存在，但 `docs/en/user-guide.md` / `docs/zh-CN/user-guide.md` 仍写“无独立 Import/Export page”。
2. **Dogfood 被放在主导航，和 internal 定位冲突。** `web/src/components/Sidebar.tsx` 将 `/dogfood` 放在 tools 分组；`CURRENT_PROJECT_STATE.md` 将 Dogfood 定义为开发者/维护者工具。
3. **`web_facade.py` 仍是架构债核心。** 目前约 1487 行，所有 routers 仍依赖 `WebFacade`，且 lab/recall services 反向 import facade helper。
4. **架构台账过早宣称债务 resolved。** `docs/dev/quality-debt-ledger.md` 将 web_facade/schema 债务标记 resolved，但代码证据不支持“边界已真正清晰”。
5. **Web IA 仍暴露内部/英文术语。** `LocalGraphPreview.tsx`、`DogfoodPage.tsx`、`GraphPage.tsx` 仍有 English/internal copy。
6. **测试主要保护 API 和静态文案，不足以证明真实用户路径可用。** `tests/test_user_journey_smoke.py` 是 FastAPI smoke；没有 frontend test files；本轮 Browser/MCP 未可用。
7. **文档治理仍混杂 current truth 与 historical evidence。** `docs/README.md` 最新 notes 列表滞后，`documentation-inventory.md` / `documentation-debt-ledger.md` 与 Batch 1 后真实状态不完全一致。
8. **`docs/dev/HANDOFF.md` 是模板但被 autopilot 设为优先读取对象。** 这会让低上下文恢复规则存在误读风险。
9. **安全语义强，但 secret/presence 说明存在内部实现不一致。** `SecretStore.present()` 通过 `get()` 读取 raw value 判断存在；`model_setup_readiness.py` 注释表达比实现更强。
10. **Graph/Sensemaking 已降级，但残留页面和 copy 仍可能让用户以为这是确认事实图或 GraphRAG 能力。**

### Top 10 Strengths

1. **approval-first 差异点仍然清楚。** `ai_draft` 到 `human_approved` 的显式审批边界在 core 和 Web review service 中都有实现。
2. **默认 fake/local-first，真实外部 provider 不是默认路径。**
3. **主路径后端 API 已能串起来。** Source/Import、Review、Approval、Library、Recall、Wiki、Export 都有实现证据。
4. **Graph/Sensemaking/RAG 方向已被文档明确降级或拒绝，避免产品走偏。**
5. **Export MVP 的安全模型正确：浏览器下载，不写真实 Obsidian vault。**
6. **docs reset 已开始建立 canonical state 和 progress ledger。**
7. **architecture boundary tests 已存在，虽然目前更像 guardrail/known-violations ledger。**
8. **Web design 已有明确审美方向，不再像 generic SaaS dashboard。**
9. **README 的 safety/non-goals 较诚实，明确 no auto approve/no default real LLM/no GraphRAG。**
10. **`/mf-autopilot` 已有 task-type entry、stale window、active workstream、handoff、gate evidence 规则。**

## Audit Method And Repo Facts

### Hard limits honored

- No product code edits.
- No doc deletion, movement, tag, or feature implementation.
- No `.env` read.
- No `src/mindforge/assets/.mindforge/secrets.json` content read.
- No real LLM, Cubox, Upstage, external service, real private data, or real Obsidian vault write.

### Browser / MCP limitation

Fresh Browser/MCP QA was not performed. The local gstack browse setup check returned `NEEDS_SETUP`; no setup/build/install was run because this audit was scoped as read-only and non-invasive. Web conclusions below are therefore based on source code, prior implementation notes, static UI text, and historical browser/MCP notes only.

Where fresh browser evidence would be required, this report says **Evidence insufficient**.

### Required repo facts

The repo path was verified before audit. It was exactly:

```text
/Users/jinkun.wang/work_space/mindforge
```

Required commands were run:

| Command | Report |
|---------|--------|
| `pwd` | `/Users/jinkun.wang/work_space/mindforge` |
| `git status --short` | clean before audit edits |
| `git rev-parse --abbrev-ref HEAD` | `main` |
| `git rev-list --left-right --count @{u}...HEAD || true` | `0 0` |
| `git log --oneline -40` | ran; latest baseline commit `7312245 docs: update commit hash in state/ledger after residual refs cleanup` |
| `find docs -maxdepth 3 -type f \| sort` | ran; 213 files reported |
| `find src -maxdepth 4 -type f \| sort` | ran; 485 files reported, including `__pycache__` files and the forbidden secret path name but not its contents |
| `find tests -maxdepth 4 -type f \| sort` | ran; 636 files reported, including `__pycache__` files |
| `find web/src -maxdepth 4 -type f \| sort || true` | ran; 79 files reported |

Latest 40 commits observed:

```text
7312245 docs: update commit hash in state/ledger after residual refs cleanup
ac6aa47 docs: clean residual references after docs batch 1
49c138c docs: update commit hash references post batch 1
fcb96c7 docs: remove stale documentation batch 1
64d7a52 chore: harden mf-autopilot loop governance
0248755 docs: add canonical project state, progress ledger, and task-type-aware autopilot
6f5db2c docs: add export page MVP implementation notes
fb87ce0 feat: add safe export page MVP with preview, download, and safety notice
9eb4108 docs: specify export page product direction + backend copy sanitization notes
7bb4a76 fix: sanitize backend generated web copy - health/wiki labels -> Chinese
a1556f9 docs: Web IA simplification implementation notes
f0427e7 fix: Web IA simplification - hide internal labels, format timestamps, replace BM25 jargon
54110d4 fix: map internal enum labels to user-friendly display values
3a83078 fix: P0 hooks ordering crash in GraphNavigationPanel + missing i18n keys
2b91a28 style: sidebar IA reorganization + SourcesPage progressive disclosure
a3842de style: progressive disclosure on SetupPage - collapse 3 onboarding/diagnostics details by default
05b0cbf docs: Stage 6 Design QA implementation notes
07bd8a0 style: Stage 6 - Design QA: page-header consistency pass
a2d622e docs: Stage 6 Design QA handoff - context threshold reached
03d4ba5 style: Stage 5 - Recall/Home/EmptyState editorial polish
29155ac style: Stage 4 - Library cards with B-style 4-layer shadows + editorial styling
af3aeb1 style: Stage 3 - Review Queue + Approval Panel editorial redesign
ffd4bdd style: Stage 2 - AppShell + Sidebar + PageHeader polish
a138177 style: Stage 1 - design system foundation (CSS tokens, fonts, focus ring)
65b00ce docs: finalize web design decision + production implementation plan
61b8a1b docs: explore MindForge web design variants
e69a482 docs: define MindForge web design direction + implementation roadmap
ab96ec8 docs: reconcile unpushed capability benchmark commit
30aee07 docs: v4.6 docs debt closure - superseded notes + ledger + archive plan
1b4b3d5 docs: Direction A4-A6 implementation notes - approval timeline + library filters + user journey tests
59c92be test: A6 user journey smoke tests - 21 tests covering main path API endpoints
8b2d284 feat: A5 Library organization MVP - filter bar (status/track/source/quality) + sort
2f27bdf feat: A4 approval timeline in ApprovalPanel - created_at + status badge + approved_at
f763d23 docs: Direction C Recall/Search Quality Lab implementation notes
2d9a271 feat: U5 Web RecallPage explain panel - BM25 边界说明 + 命中字段/匹配词展示
78fc4c7 feat: U3+U4 BM25 tuning config + recall quality gate script
4332e66 feat: U2 query explain - explain_zero_hits + explain_hits + QueryExplain dataclass
de077df feat: U1 golden recall benchmark - 12 cards + 14 golden queries + 4 negative queries
9744dcd docs: v4.9 MindForge-on-MindForge project knowledge dogfood
ad7db00 docs: close v4.8 architecture debt ledger + update docs
```

### Required documents read

Read and cross-checked:

- `.claude/commands/mf-autopilot.md`
- `docs/dev/CURRENT_PROJECT_STATE.md`
- `docs/dev/progress-ledger.md`
- `docs/dev/HANDOFF.md`
- `docs/dev/engineering-workflow.md`
- `docs/dev/documentation-reset-plan.md`
- `docs/dev/documentation-inventory.md`
- `docs/dev/documentation-debt-ledger.md`
- `docs/implementation-notes/2026-05-27-116-docs-cleanup-batch-1.md`
- `docs/implementation-notes/2026-05-27-117-docs-cleanup-residual-references.md`
- `README.md`
- `docs/README.md`
- `docs/en/user-guide.md`
- `docs/zh-CN/user-guide.md`
- `docs/audits/2026-05-25-092-current-capability-map.md`
- `docs/research/2026-05-25-093-industry-benchmark-and-gap-analysis.md`
- `docs/plans/2026-05-25-094-next-deepening-roadmap.md`
- `docs/dev/architecture.md`
- `docs/dev/quality-debt-ledger.md`
- `docs/audits/2026-05-26-099-global-architecture-quality-audit.md`
- `docs/design/2026-05-26-100-target-architecture-map.md`
- `docs/plans/2026-05-26-101-v4_8-global-architecture-quality-roadmap.md`
- Latest 10 implementation notes, including `108` through `117`
- `docs/design/2026-05-26-102-mindforge-web-design-direction.md`
- `docs/design/2026-05-26-105-final-web-design-decision.md`
- `docs/plans/2026-05-27-112-export-page-product-spec.md`

Missing expected docs:

- `docs/design/2026-05-26-108-stage-6-design-qa-report.md`: not present.
- `docs/audits/2026-05-26-111-web-information-architecture-audit.md`: not present.

## Scorecard

| Dimension | Score | Verdict |
|-----------|------:|---------|
| Product capability | 6.5 | 主路径存在，但 dogfood 仍偏 fake/local/API-first |
| Competitive position | 5.8 | 差异点明确，但产品体验还不足以赢 |
| Innovation clarity | 7.0 | approval-first knowledge compiler 是强差异点 |
| Architecture | 5.5 | Facade 和 service 边界仍重 |
| Code quality | 6.3 | 核心语义清楚，局部巨石/类型漂移明显 |
| Web design | 6.2 | 视觉方向成立，但内部术语/页面层级破坏体验 |
| Usability | 5.4 | 主任务不总是一眼可懂，Setup/Dogfood/Lab cognitive load 高 |
| Documentation governance | 5.6 | 有 canonical 入口，但 truth drift 仍明显 |
| Autopilot governance | 6.4 | 规则丰富，但复杂、易被 HANDOFF/decision stop 拖住 |
| Test/gate reliability | 6.0 | API/static tests 有价值，缺真实前端路径 gate |
| Safety semantics | 7.4 | approval 边界强，external/secret/vault 语义仍需负测和文案收敛 |
| Maintainability | 5.7 | 可维护性被 WebFacade、schema init、doc drift 拉低 |

## A. Product Capability & Value Audit

### What MindForge currently is

MindForge 是一个 local-first、approval-first 的个人知识编译器。它的真实核心不是 graph、RAG、AI chat 或 Obsidian replacement，而是把 source/import 产生的 `ai_draft` 强制经过人工 review/explicit approval，再进入 `human_approved` library/recall/wiki/export。

Evidence:

- `README.md`: defines local-first personal knowledge assistant, explicit safety/non-goals.
- `docs/dev/CURRENT_PROJECT_STATE.md`: documents the main path and non-goals.
- `src/mindforge/approval_service.py` / `src/mindforge/approver.py`: approval boundary implementation.
- `web/src/pages/ReviewQueuePage.tsx`, `web/src/pages/LibraryPage.tsx`, `web/src/pages/RecallPage.tsx`, `web/src/pages/WikiPage.tsx`, `web/src/pages/ExportPage.tsx`: visible main-path pages.

### Does the main path really work?

**Conditional yes.** The API/code path exists and is covered by smoke tests, but the evidence is stronger for backend/API than for real user UX.

Path audit:

| Step | Evidence | Verdict |
|------|----------|---------|
| Source / Import | `src/mindforge/sources/`, `src/mindforge_web/services/web_import_export_service.py`, `web/src/pages/SourcesPage.tsx` | Works as local/file-oriented capability |
| `ai_draft` | `src/mindforge/processors/`, tests using draft cards | Works in fake/local path |
| Review | `src/mindforge_web/services/web_review_service.py`, `web/src/pages/ReviewQueuePage.tsx` | Works, explicit confirmation required in Web service |
| explicit approval | `approve_explicit_card()` and `approve_card()` | Strong core boundary |
| `human_approved` | `src/mindforge/approver.py` frontmatter update | Strong |
| Library | `web/src/pages/LibraryPage.tsx`, `src/mindforge_web/routers/library.py` | Works |
| Recall/Wiki | `web/src/pages/RecallPage.tsx`, `web/src/pages/WikiPage.tsx`, service tests | Works in local/tested form |
| Export | `web/src/pages/ExportPage.tsx`, library router export API | Works as browser-local MVP, but docs drift |

### Dogfoodable vs lab/internal

Dogfoodable:

- Source/import with supported local files.
- Fake/local AI draft pipeline.
- Manual review and approval.
- Library browsing/filtering.
- BM25 recall.
- Wiki from approved cards.
- Markdown/ZIP browser download export.
- Knowledge health and provenance, as support tools.

Internal/lab:

- `/dogfood`: developer/operator page, not end-user product.
- `/graph`: internal/lab visualization, not GraphRAG.
- `/sensemaking`: heuristic lab.
- entity/community/topic detection.
- GraphRepository and GraphPort abstractions.

Hidden but still misleading:

- Graph/Sensemaking labels still suggest more maturity than the product supports.
- `LocalGraphPreview.tsx` exposes English graph terms inside the product surface.
- Dogfood in main navigation makes internal tooling feel like a product feature.
- User guides still say there is no standalone Export page, hiding a real current feature.

Low-value / misleading features:

- Main-nav Dogfood page for normal users.
- Standalone Graph/Sensemaking pages if treated as core product.
- Repository/Port abstractions around graph behavior that is not central to the current product.
- Design/architecture docs that imply resolved state without matching code evidence.

### Product verdict

**Product score: 6.5 / 10**

Core value assets:

- Explicit approval as product primitive.
- Local-first default.
- Approved-only library/wiki/export mental model.
- Browser-local export safety.
- Deterministic recall and provenance.

Product positioning verdict:

MindForge should position as **approval-first personal knowledge compiler**, not “AI PKM,” not “GraphRAG,” not “Obsidian competitor,” and not “read-it-later app.” Its current chance of being liked by real users depends on making the approval path feel calm, fast, and trustworthy; the graph/lab surface should stay secondary.

## B. Competitive & Innovation Audit

### Competitive score: 5.8 / 10

MindForge is not yet competitive as a general notes app or read-it-later product. It can become competitive in a narrower wedge: **turning messy sources into reviewed, approved, recallable knowledge cards without silently poisoning the user’s trusted library**.

### Innovation score: 7.0 / 10

The strongest innovation remains approval-first compilation. This is clearer and more defensible than graph exploration, generic AI chat, or local-first branding alone.

| Comparator | What MindForge should learn | What MindForge should not copy |
|------------|-----------------------------|--------------------------------|
| Obsidian / Logseq-like notes | Fast navigation, user-owned files, low-friction linking | Plugin sprawl, canvas/graph fetish, vault write promises |
| Readwise / Reader-like capture/review | Capture/review cadence, inbox clarity, highlight-to-knowledge workflow | Pure read-it-later backlog and passive collection |
| Tana-like structured workspace | Structured fields where they reduce ambiguity | High cognitive load, schema-first setup, everything-as-database UX |
| AI PKM / GraphRAG systems | Retrieval confidence, source traceability, explainability | Vector/RAG claims, auto-synthesis as truth, graph as proof |

Current drift risk:

- Web still devotes visible surface to Dogfood/Graph/Sensemaking.
- Architecture still preserves graph/lab coupling.
- Docs still need to keep repeating “not GraphRAG,” which suggests the product surface still invites that misunderstanding.

Double down on:

- Review queue as the product center.
- Approved-only library/wiki/export.
- Recall explainability without BM25 jargon.
- Provenance and source trust.
- Safe local export.

Stop doing:

- Adding graph/sensemaking breadth.
- Treating dogfood/operator diagnostics as user-facing core.
- Continuing documentation deletion as the primary workstream.
- Claiming architecture reset completion while `WebFacade` remains central.

## C. Architecture & Code Quality Audit

### Architecture score: 5.5 / 10

### Code quality score: 6.3 / 10

The codebase has real modular pieces, but the Web backend still has a central orchestration gravity well. Schema modularization and service extraction improved file size, but they did not fully fix boundaries.

Key evidence:

- `src/mindforge_web/services/web_facade.py`: about 1487 lines, class `WebFacade`, still owns many unrelated page/API capabilities.
- `src/mindforge_web/routers/*.py`: all 19 routers import `WebFacade`.
- `src/mindforge_web/services/web_lab_service.py`: imports helpers from `web_facade.py`.
- `src/mindforge_web/services/web_recall_service.py`: imports graph helpers from `web_facade.py`.
- `src/mindforge_web/schemas/__init__.py`: about 399 lines and still defines many schema classes; it is not just a re-export index.
- `tests/test_architecture_boundaries.py`: architecture tests exist but explicitly allow current lab/facade known violations.

### Top 10 architecture/code risks

1. **`WebFacade` remains a God-adjacent object.**
   - Evidence: `src/mindforge_web/services/web_facade.py`, class `WebFacade`, 1487 lines.
   - Why it matters: all routers converge on one object, so feature changes tend to cross unrelated concerns.
   - Severity: P1.
   - Remediation: split facade by route/domain or introduce route-specific dependency providers; keep `WebFacade` only as temporary compatibility shim.
   - Blocks next loop: yes for architecture reset, no for product dogfood.

2. **Service extraction has reverse coupling back into facade.**
   - Evidence: `web_lab_service.py` and `web_recall_service.py` import `_build_graph_builder` and graph helpers from `web_facade.py`.
   - Why it matters: extracted services are not independent boundaries.
   - Severity: P1.
   - Remediation: move graph helper construction to a small graph context module or inject dependencies.
   - Blocks next loop: yes for architecture reset.

3. **Routers are thin but too uniformly dependent on `WebFacade`.**
   - Evidence: every router under `src/mindforge_web/routers/` imports `WebFacade`.
   - Why it matters: thin routers are good, but single dependency hides domain coupling.
   - Severity: P2.
   - Remediation: route groups should depend on focused services.
   - Blocks next loop: no.

4. **Schema modularization is incomplete.**
   - Evidence: `src/mindforge_web/schemas/__init__.py` still defines classes such as provenance, workflow, discovery, path action, API error schemas.
   - Why it matters: `__init__` remains a schema dumping ground and slows ownership clarity.
   - Severity: P2.
   - Remediation: make `__init__.py` re-export only; move remaining classes to domain files.
   - Blocks next loop: no.

5. **Dogfood logic is duplicated/centralized in the facade.**
   - Evidence: `WebFacade.dogfood_report()` remains substantial while `src/mindforge_web/services/dogfood_service.py` exists.
   - Why it matters: internal diagnostics can leak into product-facing service architecture.
   - Severity: P2.
   - Remediation: move dogfood report construction to dogfood service and keep facade delegation only.
   - Blocks next loop: no.

6. **Lab graph imports still sit in main Web service layer.**
   - Evidence: `web_facade.py` imports `mindforge.relations.discovery_context`, `graph_builder`, `graph_models`, `local_graph`, `related_cards`.
   - Why it matters: lab/internal code still shares the main web dependency path.
   - Severity: P2.
   - Remediation: isolate graph/lab dependencies behind lab-only router/service modules.
   - Blocks next loop: no.

7. **Architecture tests currently freeze known violations instead of failing them.**
   - Evidence: `tests/test_architecture_boundaries.py` allows known lab/facade imports.
   - Why it matters: tests prevent regression but do not force target architecture.
   - Severity: P2.
   - Remediation: add separate “target boundary” tests behind a TODO marker or explicit debt ID, then close them slice by slice.
   - Blocks next loop: no.

8. **Config service is also large.**
   - Evidence: `src/mindforge_web/services/web_config_service.py`, about 1017 lines.
   - Why it matters: Setup complexity remains concentrated.
   - Severity: P2.
   - Remediation: split provider readiness, secret operations, and config validation.
   - Blocks next loop: no.

9. **Type/API drift exists in ExportPage.**
   - Evidence: `web/src/pages/ExportPage.tsx` casts tags via `unknown` because frontend card type lacks tags.
   - Why it matters: UI feature works by bypassing type clarity.
   - Severity: P2.
   - Remediation: align `LibraryCard` type with API schema.
   - Blocks next loop: no.

10. **`__pycache__` files appear under `src` and `tests` file inventories.**
    - Evidence: required `find src` and `find tests` outputs include `__pycache__`.
    - Why it matters: repo hygiene and audit signal are noisy; generated files should not be part of tracked source truth if tracked.
    - Severity: P3.
    - Remediation: verify whether tracked; clean only in a separate hygiene loop.
    - Blocks next loop: no.

### Top 5 modules to refactor

1. `src/mindforge_web/services/web_facade.py`
2. `src/mindforge_web/services/web_config_service.py`
3. `src/mindforge_web/services/web_lab_service.py`
4. `src/mindforge_web/services/web_recall_service.py`
5. `src/mindforge_web/schemas/__init__.py`

### Top 5 modules to leave alone

1. `src/mindforge/approver.py` - explicit approval semantics are clear.
2. `src/mindforge/approval_service.py` - approval service boundary is important and currently understandable.
3. `src/mindforge/wiki_service.py` - approved-only synthesis boundary should stay stable.
4. `src/mindforge/recall_service.py` and `src/mindforge/lexical_index.py` - local lexical recall is a core asset.
5. `src/mindforge/export/` and library export API behavior - preserve safe local export semantics.

### Is a v4.8-style global architecture reset still needed?

**Yes, but not as the immediate primary loop.** A targeted architecture quality reset is still needed because the current code did not reach the target architecture described in `docs/design/2026-05-26-100-target-architecture-map.md`. However, the next loop should first dogfood the main product path so architecture work is driven by user-path friction, not aesthetic decomposition.

## D. Web Design & UX Audit

### Scores

- Web design score: 6.2 / 10
- Usability score: 5.4 / 10
- IA/cognitive load score: 5.0 / 10

### Global UX verdict

The visual direction is better than a generic dashboard, but information architecture still mixes user tasks, operator diagnostics, lab concepts, and implementation language. This creates a product that can look refined while still asking users to understand too much.

Fresh Browser/MCP evidence: **Evidence insufficient.** Static code and prior notes only.

### Page-by-page audit

| Page | Evidence | Verdict |
|------|----------|---------|
| Home | `web/src/pages/HomePage.tsx`, prior Stage 5 notes | Likely directionally good, but fresh browser evidence insufficient |
| Setup | `web/src/pages/SetupPage.tsx`, `web_config_service.py` | Necessary but cognitively heavy; provider/secret readiness needs clearer progressive disclosure |
| Sources | `web/src/pages/SourcesPage.tsx` | Improved progressive disclosure, still high-risk due import/watch complexity |
| Review | `web/src/pages/ReviewQueuePage.tsx`, `web_review_service.py` | Should remain product center; approval language is a strength |
| Library | `web/src/pages/LibraryPage.tsx` | Core usable surface; static evidence says filters/sort exist |
| Card Detail / Workspace | `web/src/components/GraphExplorer.tsx`, card components | Related graph preview risks over-explaining internal graph ideas |
| Recall | `web/src/pages/RecallPage.tsx` | BM25 jargon reduced, but explain fields still need user-level language |
| Wiki | `web/src/pages/WikiPage.tsx` | Approved-only boundary is valuable; copy needs to avoid synthesis-as-truth overclaim |
| Export | `web/src/pages/ExportPage.tsx` | Product path closure exists; docs drift makes it under-communicated |
| Health | `web/src/pages/HealthPage.tsx`, health service | Useful support page, should not become main success proof |
| Lab/Internal | `GraphPage.tsx`, `SensemakingPage.tsx`, `DogfoodPage.tsx` | Dogfood is too visible; Graph/Sensemaking should stay clearly lab/internal |

### Top UX blockers

1. **Dogfood in primary navigation.**
   - Evidence: `web/src/components/Sidebar.tsx`.
   - Why it matters: normal users see internal instrumentation as a core product feature.
   - Severity: P1.
   - Remediation: move Dogfood under collapsed internal/lab group or hide behind dev flag.
   - Blocks next loop: yes for Web IA Loop 2.

2. **Export state is not reflected in user docs.**
   - Evidence: `docs/en/user-guide.md`, `docs/zh-CN/user-guide.md`, `web/src/pages/ExportPage.tsx`.
   - Why it matters: the end-to-end path appears incomplete in user docs even though code has an Export page.
   - Severity: P1.
   - Remediation: update user guides and README Web UI table.
   - Blocks next loop: yes for documentation trust.

3. **Internal graph terminology remains visible.**
   - Evidence: `web/src/components/LocalGraphPreview.tsx`, `web/src/pages/GraphPage.tsx`, `web/src/pages/DogfoodPage.tsx`.
   - Why it matters: users can confuse local relatedness with confirmed knowledge or GraphRAG.
   - Severity: P1.
   - Remediation: rewrite labels around “related sources/cards” and hide lab mechanics.
   - Blocks next loop: yes for Web IA Loop 2.

4. **Setup likely remains too technical.**
   - Evidence: `web/src/pages/SetupPage.tsx`, `web_config_service.py`, docs around provider readiness.
   - Why it matters: first-run success depends on setup clarity.
   - Severity: P2.
   - Remediation: test with real first-run flow and collapse advanced diagnostics.
   - Blocks next loop: no.

5. **No current browser QA evidence.**
   - Evidence: gstack browse setup unavailable.
   - Why it matters: static source inspection cannot prove responsive layout, visual hierarchy, or task completion.
   - Severity: P2.
   - Remediation: run browser QA after setup is available, with desktop/mobile screenshots.
   - Blocks next loop: no, but blocks UX readiness claims.

### Top design inconsistencies

- `DogfoodPage.tsx` uses page-specific header structure rather than the standard page-header pattern.
- `LocalGraphPreview.tsx` has English visible copy inside a bilingual/Chinese product context.
- `GraphPage.tsx` still contains explicit Lab/Internal framing in product routes.
- Export uses mostly i18n but has hardcoded Chinese strings and `"..."` loading text.
- Dogfood page exposes local implementation details such as `search_index_path`.

### Is another Web IA loop needed?

**Yes.** But it should be Web IA/UX Loop 2, not generic UI polish. It should specifically reduce cognitive load and hide internal/lab surfaces after Product Main Path Real Dogfood identifies the highest-friction screens.

## E. Documentation Governance Audit

### Scores

- Documentation governance score: 5.6 / 10
- Docs trustworthiness score: 5.2 / 10

### Verdict

The repo now has better governance scaffolding, but current truth is still not consistently separated from historical evidence. The most important problem is no longer “too many docs” in the abstract; it is that some canonical docs and user guides contradict current code.

### Key evidence

- `docs/dev/CURRENT_PROJECT_STATE.md`: strong canonical entry, but baseline HEAD was stale before this audit.
- `docs/dev/progress-ledger.md`: useful loop history, but active workstream still points to Documentation Reset even after Batch 2 became a product decision stop.
- `docs/README.md`: entry point exists, but latest implementation notes list is stale.
- `docs/en/user-guide.md` and `docs/zh-CN/user-guide.md`: stale Export-page statements.
- `docs/dev/documentation-inventory.md`: still contains pre-Batch-1 wording and status that is not fully reconciled.
- `docs/dev/documentation-debt-ledger.md`: still references deleted/stale design docs as if current debt inventory were fully fresh.
- `docs/implementation-notes/2026-05-27-116-docs-cleanup-batch-1.md` and `117`: good evidence for what changed and what remains undecided.

### Should Batch 2 proceed?

**No, not as currently defined.** Batch 2 should not proceed as a broad delete/archive campaign because the rules are not precise enough and some archive candidates may still carry useful historical evidence.

Batch 2 may proceed only under exact rules:

1. The doc is not canonical and not linked as current truth by `docs/README.md`, `CURRENT_PROJECT_STATE.md`, `progress-ledger.md`, or active plans.
2. The doc has a newer replacement that states the replacement path.
3. `rg` shows no live references except historical notes, inventories, or implementation logs.
4. The doc is not an audit, ADR, implementation note, or evidence artifact required to understand why a decision was made.
5. Archive means “mark historical and move only if a docs/archive policy exists”; do not invent mass-move semantics during cleanup.
6. Deletion is allowed only for files that are provably obsolete scaffolding with no evidence value.
7. Every action updates `documentation-inventory.md`, `documentation-reset-plan.md`, and relevant references in the same commit.

### Canonical docs that should remain

- `README.md`
- `docs/README.md`
- `docs/dev/CURRENT_PROJECT_STATE.md`
- `docs/dev/progress-ledger.md`
- `docs/dev/engineering-workflow.md`
- `docs/dev/architecture.md`
- `docs/dev/quality-debt-ledger.md`
- `docs/dev/documentation-reset-plan.md`
- `docs/dev/documentation-inventory.md`
- Current user guides under `docs/en/` and `docs/zh-CN/`
- Recent audits/plans/implementation notes that explain current product/architecture decisions

### Docs that can be archived only under rules

- Superseded RFC/SDD/spec docs that have newer canonical replacements.
- Old design exploration docs once the current design decision and implementation notes remain linked.
- Old roadmap docs not referenced by current state.

### Docs that should not be touched now

- Recent implementation notes `108`-`117`.
- Product capability/benchmark/roadmap evidence docs `092`-`094`.
- Architecture audit/target/roadmap docs `099`-`101`.
- Any audit that explains why Graph/Sensemaking/RAG were downgraded.

## F. /mf-autopilot Governance Audit

### Autopilot governance score: 6.4 / 10

### What works

- `/mf-autopilot` now mandates reading `CURRENT_PROJECT_STATE.md`, `progress-ledger.md`, `HANDOFF.md`, and `engineering-workflow.md`.
- Task-type entrypoints exist, including `audit_only`, `docs_cleanup`, `ui_ux_polish`, `architecture_refactor`, and `dogfood`.
- Active workstream, stale window, old commit reconciliation, and low-context handoff rules exist.
- It explicitly says spec/doc/gate/commit/push are not stop points.

### Top risks

1. **HANDOFF template priority risk.**
   - Evidence: `.claude/commands/mf-autopilot.md` says HANDOFF priority can override current state; `docs/dev/HANDOFF.md` is currently a template.
   - Why it matters: a placeholder can be mistaken for real handoff state.
   - Severity: P1.
   - Remediation: rename template or add machine-readable `status: inactive` semantics.
   - Blocks next loop: yes for overnight loops.

2. **Command complexity is high.**
   - Evidence: `.claude/commands/mf-autopilot.md` now contains many sections and edge-case rules.
   - Why it matters: complex governance docs are harder for agents to apply consistently.
   - Severity: P2.
   - Remediation: keep command concise and push detailed templates into dev docs.
   - Blocks next loop: no.

3. **Hard stop can become path dependence.**
   - Evidence: Batch 2 `HARD_STOP_PRODUCT_DECISION` was correct, but active workstream stayed Documentation Reset.
   - Why it matters: autopilot can keep orbiting the previous workstream instead of selecting the next highest-value loop.
   - Severity: P2.
   - Remediation: when a workstream hard-stops, require explicit “end or re-scope active workstream” update.
   - Blocks next loop: no.

4. **Gate evidence rules are good but need enforcement automation.**
   - Evidence: command says no tail/head/truncated pass claims; current process still relies on human/agent discipline.
   - Why it matters: auditability depends on exact exit codes.
   - Severity: P2.
   - Remediation: add a small gate runner or evidence template.
   - Blocks next loop: no.

5. **Task-type entrypoints are useful but not enough to decide product priority.**
   - Evidence: current docs recommend Batch 2 despite higher-value product dogfood need.
   - Why it matters: mechanism can continue lower-value governance work.
   - Severity: P2.
   - Remediation: add priority rule: after governance loop, run red-team scorecard before continuing docs cleanup.
   - Blocks next loop: no.

### Ready for overnight loops?

**Not yet.** It is ready for bounded single-loop automation with explicit task type. It is not ready for unattended overnight loops until HANDOFF semantics, workstream hard-stop handling, and gate evidence capture are less ambiguous.

### Current active workstream clarity

Before this audit, active workstream was Documentation Reset. After this audit, the recommended active workstream should change to **Product Main Path Real Dogfood**. Documentation Reset Batch 2 should be paused unless exact archive/delete rules are approved.

## G. Test / Gate Reliability Audit

### Scores

- Test quality score: 6.2 / 10
- Gate reliability score: 6.0 / 10

### What tests protect

- Approval boundary: `tests/test_review_approval_boundary.py`.
- API user journey smoke: `tests/test_user_journey_smoke.py`.
- Static web product copy: `tests/test_web_product_copy.py`.
- Architecture dependency boundaries: `tests/test_architecture_boundaries.py`.
- Recall quality lab/golden queries: recall quality tests and scripts in tests/docs history.

### Missing tests

1. Real frontend route/page tests for Home, Setup, Sources, Review, Library, Recall, Wiki, Export.
2. Browser/MCP smoke that records route success, primary CTA presence, and mobile layout.
3. Negative tests that Graph/Sensemaking/Dogfood are not shown as core user features.
4. Export page tests for scope/filter/preview/download logic.
5. Tests proving docs/user guides do not contradict existing routes.
6. Tests proving real provider calls are opt-in and never happen during approval.
7. Tests around secret masking/presence APIs.

### Low-value or risky tests

- `tests/test_web_product_copy.py` is valuable but partly static and can preserve existing English/internal labels if assertions encode them.
- `tests/test_architecture_boundaries.py` is useful but currently allows known violations, so it cannot prove target architecture.
- `tests/test_review_approval_boundary.py` has a broad allowlist for `human_approved` references, which can become noisy and hard to reason about.
- API smoke tests do not prove human UI completion.

### Minimum gate recommendation

For the next product dogfood loop:

1. `git diff --check`
2. `ruff check src tests docs/ .claude/commands/`
3. `python -m pytest tests/test_review_approval_boundary.py tests/test_user_journey_smoke.py tests/test_web_product_copy.py -q --tb=short`
4. `npm --prefix web run build`
5. Browser/MCP or Playwright smoke for `/`, `/setup`, `/sources`, `/review`, `/library`, `/recall`, `/wiki`, `/export`

## H. Safety & Approval Semantics Audit

### Safety verdict: CONDITIONAL

Core approval semantics are strong. The conditional part is about proving external-service, secret, and vault safety with negative tests and user-facing copy, not about a found P0 bypass.

### Evidence

- `src/mindforge/approver.py`: `approve_card()` promotes only `ai_draft` to `human_approved` and rejects non-promotable statuses.
- `src/mindforge/approval_service.py`: approval candidate defaults to `ai_draft`; `approve_explicit_card()` requires a specific card path.
- `src/mindforge_web/services/web_review_service.py`: `approve()` requires `confirm` and `reviewed_source`, then calls explicit approval.
- `src/mindforge/llm/factory.py`: fake provider is supported and real providers are configured explicitly.
- `web/src/pages/ExportPage.tsx`: export is browser download, not vault write.
- `README.md`: documents no auto approve, no default real LLM, no GraphRAG, no Obsidian vault write.

### P0 safety issues

None found under this no-external-service, no-secret-content audit.

### P1 safety issues

1. **Safety claims need stronger negative tests before real-provider dogfood.**
   - Evidence: tests cover approval boundary, but no single required gate proves “approval never calls real LLM,” “export never writes vault,” and “web setup never returns raw secrets.”
   - Why it matters: safety is the core product promise.
   - Severity: P1.
   - Remediation: add explicit negative tests for provider calls, vault writes, and secret masking.
   - Blocks next loop: yes if next loop uses real provider; no for fake/local dogfood.

2. **Web copy around graph/lab can imply more certainty than exists.**
   - Evidence: `GraphPage.tsx`, `LocalGraphPreview.tsx`, `DogfoodPage.tsx`.
   - Why it matters: users may treat heuristic relations as confirmed facts.
   - Severity: P1.
   - Remediation: keep lab pages hidden/collapsed and rewrite graph language as relatedness, not truth.
   - Blocks next loop: yes for Web IA loop.

### Required negative tests

- Real provider client is not instantiated or called during fake/local approval.
- Approval requires explicit user confirmation and source review in Web service.
- Non-`ai_draft` cards cannot be promoted by review APIs.
- Raw secret values are never returned by Web config/status endpoints.
- Export only returns/downloads content and does not write an Obsidian vault.
- Wiki/synthesis only uses `human_approved` cards.
- Graph/Sensemaking outputs are never treated as `human_approved` facts.

## Findings By Severity

### P0

No P0 issue found in this audit.

### P1

#### P1-01 Export page exists, but user docs deny it

- Evidence: `web/src/pages/ExportPage.tsx`, `web/src/App.tsx`, `docs/en/user-guide.md`, `docs/zh-CN/user-guide.md`, `README.md`.
- Why it matters: current truth and user guidance conflict on a core path endpoint.
- Recommended remediation: update user guides and README Web UI table; add doc route consistency check.
- Blocks next loop: yes for docs trust and product dogfood.

#### P1-02 Dogfood is internal but visible as main product navigation

- Evidence: `web/src/components/Sidebar.tsx`, `web/src/pages/DogfoodPage.tsx`, `docs/dev/CURRENT_PROJECT_STATE.md`.
- Why it matters: users see developer diagnostics as a core product task, increasing cognitive load and reducing trust.
- Recommended remediation: move Dogfood to collapsed internal/lab group or dev-only gate.
- Blocks next loop: yes for Web IA Loop 2.

#### P1-03 WebFacade remains the central architecture risk

- Evidence: `src/mindforge_web/services/web_facade.py`, `src/mindforge_web/routers/*.py`.
- Why it matters: broad ownership makes changes harder to reason about and prevents true modularity.
- Recommended remediation: targeted facade breakup after product dogfood identifies most painful domains.
- Blocks next loop: yes for architecture reset; no for fake/local dogfood.

#### P1-04 Extracted lab/recall services depend back on facade helpers

- Evidence: `src/mindforge_web/services/web_lab_service.py`, `src/mindforge_web/services/web_recall_service.py`.
- Why it matters: extraction did not create independent service boundaries.
- Recommended remediation: move graph helper construction into dedicated module or inject dependencies.
- Blocks next loop: yes for architecture reset.

#### P1-05 No current browser evidence for Web usability

- Evidence: gstack browse setup unavailable; no frontend test files under `web/src`.
- Why it matters: static code and API smoke cannot prove page usability, responsive layout, or CTA clarity.
- Recommended remediation: run browser/Playwright smoke in next Web/product loop.
- Blocks next loop: no, but blocks UX readiness claims.

#### P1-06 HANDOFF template can override current state

- Evidence: `docs/dev/HANDOFF.md`, `.claude/commands/mf-autopilot.md`.
- Why it matters: autopilot can treat a placeholder as authoritative low-context handoff.
- Recommended remediation: add inactive status semantics or rename to template.
- Blocks next loop: yes for overnight autopilot.

### P2

#### P2-01 CURRENT_PROJECT_STATE baseline was stale before audit

- Evidence: `docs/dev/CURRENT_PROJECT_STATE.md` listed `ac6aa47`; repo baseline was `7312245`.
- Why it matters: canonical state loses credibility if commit identity drifts.
- Recommended remediation: store audit baseline and avoid pretending state docs can self-reference their final commit hash.
- Blocks next loop: no.

#### P2-02 docs/README latest notes list is stale

- Evidence: `docs/README.md` latest implementation notes list does not include notes `108`-`117`.
- Why it matters: docs entry point does not lead agents to the latest truth.
- Recommended remediation: update in a focused docs sync loop.
- Blocks next loop: no.

#### P2-03 Documentation inventory and debt ledger lag Batch 1

- Evidence: `docs/dev/documentation-inventory.md`, `docs/dev/documentation-debt-ledger.md`, Batch 1 notes.
- Why it matters: cleanup governance relies on stale inventory.
- Recommended remediation: reconcile inventory before any Batch 2 action.
- Blocks next loop: yes for Batch 2.

#### P2-04 Graph/Sensemaking lab language still over-signals capability

- Evidence: `web/src/pages/GraphPage.tsx`, `web/src/pages/SensemakingPage.tsx`, `web/src/components/LocalGraphPreview.tsx`.
- Why it matters: users may infer confirmed reasoning or GraphRAG.
- Recommended remediation: reduce lab surface and rewrite labels.
- Blocks next loop: no.

#### P2-05 Secret presence semantics are stricter in docs than implementation

- Evidence: `src/mindforge/secrets/secret_store.py`, `src/mindforge/config/model_setup_readiness.py`.
- Why it matters: even if raw secrets are not returned, implementation internally reads raw value to check presence.
- Recommended remediation: add metadata-only presence check or revise comment to match behavior.
- Blocks next loop: no, but blocks strong safety claims.

#### P2-06 ExportPage has type/copy drift

- Evidence: `web/src/pages/ExportPage.tsx`.
- Why it matters: tags are accessed via casts; some UI strings bypass i18n.
- Recommended remediation: align API type and centralize strings in i18n.
- Blocks next loop: no.

#### P2-07 Architecture docs contain stale router/module references

- Evidence: `docs/dev/architecture.md` references router modules that are not present, while actual routers differ.
- Why it matters: architecture docs are not fully trustworthy for new agents.
- Recommended remediation: update architecture doc after next architecture slice.
- Blocks next loop: no.

#### P2-08 Test gates do not include npm build or browser smoke by default

- Evidence: current required gates for this audit are docs/static pytest only; frontend tests absent.
- Why it matters: Web regressions can pass current gates.
- Recommended remediation: add npm build and browser smoke to product/UI loops.
- Blocks next loop: no.

### P3

#### P3-01 `__pycache__` files appear in source/test inventories

- Evidence: required `find src` and `find tests` outputs.
- Why it matters: noisy repo audit surface.
- Recommended remediation: verify tracked status and clean in a separate hygiene loop.
- Blocks next loop: no.

#### P3-02 Missing expected design audit docs create evidence gaps

- Evidence: `docs/design/2026-05-26-108-stage-6-design-qa-report.md` and `docs/audits/2026-05-26-111-web-information-architecture-audit.md` are absent.
- Why it matters: later docs reference outcomes whose full reports are not present.
- Recommended remediation: either restore reports if they existed or update references to point at implementation notes.
- Blocks next loop: no.

#### P3-03 Some product copy tests encode current copy rather than ideal copy

- Evidence: `tests/test_web_product_copy.py` includes expectations around `LocalGraphPreview`.
- Why it matters: static tests can preserve internal language instead of flagging it.
- Recommended remediation: rewrite tests around forbidden terms/user-facing principles.
- Blocks next loop: no.

## Feature / Capability Matrix

| Capability | Status | User value | Evidence | Recommended action |
|------------|--------|------------|----------|--------------------|
| Source import/watch | Core | Bring local sources into review flow | `src/mindforge/sources/`, `SourcesPage.tsx` | Keep; dogfood with safe sample data |
| AI draft generation | Core | Convert source into reviewable draft | `src/mindforge/processors/` | Keep fake/local default; real provider opt-in only |
| Review queue | Core | Human judgment before trust | `ReviewQueuePage.tsx`, `web_review_service.py` | Double down |
| Explicit approval | Core | Prevent AI from polluting library | `approval_service.py`, `approver.py` | Protect with negative tests |
| Library | Core | Browse approved knowledge | `LibraryPage.tsx`, library APIs | Keep; validate with dogfood |
| Recall/Search | Core | Retrieve approved cards | `RecallPage.tsx`, recall services | Keep; tune after dogfood evidence |
| Wiki | Support | Synthesize approved knowledge | `WikiPage.tsx`, `wiki_service.py` | Keep approved-only boundary |
| Export | Core | Close the user path with local files | `ExportPage.tsx`, library export API | Keep; fix docs/type/copy drift |
| Health | Support | Diagnose collection quality | `HealthPage.tsx`, health service | Keep as support page |
| Provenance | Support | Source trust and auditability | `provenance/`, web facade provenance methods | Keep; surface carefully |
| Dogfood | Internal | Maintainer diagnostics | `DogfoodPage.tsx`, dogfood services | Hide from main nav |
| Graph page | Lab/Internal | Explore local relatedness | `GraphPage.tsx`, graph services | Keep collapsed/lab; do not expand |
| Sensemaking | Lab | Experimental heuristics | `SensemakingPage.tsx` | Do not promote |
| Entity/community/topic detection | Lab | Experimental structure | relation/discovery modules | Keep internal |
| Obsidian vault write | Cut | Too risky/misleading | README non-goals, Export spec | Do not implement now |
| RAG/vector/embedding | Cut | Not current product | README/current state non-goals | Do not implement |
| Auto approve | Cut | Violates core safety | approval tests/services | Continue forbidding |

## Architecture Risk Map

| Area | Risk | Evidence | Severity | Next action |
|------|------|----------|----------|-------------|
| Web facade | Giant orchestration point | `web_facade.py` 1487 lines | P1 | Targeted breakup after dogfood |
| Router dependencies | All routers import facade | `src/mindforge_web/routers/*.py` | P2 | Introduce focused dependencies |
| Lab isolation | Lab imports depend on facade helpers | `web_lab_service.py` | P1 | Move graph helpers |
| Recall coupling | Recall service imports graph helpers | `web_recall_service.py` | P1 | Separate recall from graph context |
| Schemas | `__init__.py` defines domain schemas | `schemas/__init__.py` | P2 | Re-export only |
| Config | Setup/config service large | `web_config_service.py` | P2 | Split secret/provider/readiness |
| Dogfood | Internal service logic in facade/page | `dogfood_report()`, `DogfoodPage.tsx` | P2 | Hide and isolate |
| Architecture tests | Known violations allowed | `test_architecture_boundaries.py` | P2 | Add target-boundary tests |

## Web UX / IA Risk Map

| Surface | Risk | Evidence | Severity | Next action |
|---------|------|----------|----------|-------------|
| Sidebar | Dogfood in main tools nav | `Sidebar.tsx` | P1 | Move/hide internal |
| Export | Docs contradict route | `ExportPage.tsx`, user guides | P1 | Sync user docs |
| Local graph preview | English/internal labels | `LocalGraphPreview.tsx` | P1 | Rewrite user-facing copy |
| Graph/Sensemaking | Lab may look like product | `GraphPage.tsx`, `SensemakingPage.tsx` | P2 | Stronger lab framing or dev flag |
| Setup | High cognitive load | `SetupPage.tsx`, config service | P2 | Browser dogfood first-run |
| Dogfood | Shows paths/metrics | `DogfoodPage.tsx` | P2 | Dev-only or collapse |
| Export | Partial i18n/type drift | `ExportPage.tsx` | P2 | Type and i18n cleanup |

## Documentation Governance Verdict

MindForge’s documentation governance is better than before but not trustworthy enough to drive more deletion automatically. Canonical entrypoints exist, but they still drift from code truth. The next docs work should be **truth synchronization**, not archive enthusiasm.

Batch 2 should not proceed until exact rules are approved. If it proceeds, it must be rule-based, evidence-preserving, and reversible in intent.

## Autopilot Governance Verdict

`/mf-autopilot` is materially better after the upgrade: it reads state first, uses task-type entrypoints, tracks active workstream, and has stale/handoff/gate rules. The weak point is that the mechanism is now complex and can still orbit a stale workstream. It is not ready for unattended overnight loops until HANDOFF semantics and hard-stop workstream transitions are simplified.

Required changes before next major auto-run:

1. Mark `HANDOFF.md` inactive when it is a template, or rename the template.
2. Add an explicit rule: when a workstream hits hard stop, the next loop must choose a new active workstream or record the exact decision needed.
3. Add a compact gate evidence template with exact command, exit code, and timeout.
4. Keep task-type entrypoints, but move long examples/templates out of the command if possible.

## Recommended Remediation Roadmap

### Candidate directions

#### A. Continue Documentation Reset Batch 2 with exact archive rules

Value: medium.
Risk: high if rules are vague.
Use only if the user wants governance cleanup and accepts the exact rules in this report.

#### B. Web IA/UX Loop 2

Value: high.
Scope: move Dogfood out of main nav, fix Export docs/copy drift, reduce graph/internal language, test key pages with browser, simplify Setup and Export cognitive load.

#### C. v4.8 Global Architecture Quality Reset

Value: high, but should be targeted.
Scope: break facade back-imports, isolate lab/graph, move remaining schemas out of `__init__`, split config service.

#### D. Product Main Path Real Dogfood

Value: highest.
Scope: run Source/Import -> ai_draft -> Review -> explicit approval -> human_approved -> Library -> Recall/Wiki -> Export with safe local sample data first, then optional real-provider opt-in only after negative safety tests.

#### E. Recall/Search Quality Lab

Value: medium.
Scope: tune search only after dogfood reveals real recall failures.

### Recommended primary next loop

**D. Product Main Path Real Dogfood.**

Why: it answers the most important truth question: whether a real person can complete the product’s core promise without being confused, blocked, or misled. It will also provide better evidence for Web IA and architecture priorities than another abstract cleanup loop.

### Secondary next loop

**B. Web IA/UX Loop 2.**

Why: dogfood will likely expose the same issues this audit found statically: Dogfood visibility, Export/doc drift, graph terminology, Setup cognitive load, and missing browser evidence.

### What not to do next

- Do not continue Batch 2 as a broad archive/delete sweep.
- Do not expand Graph/Sensemaking.
- Do not run a large architecture reset before product dogfood clarifies user-path pain.
- Do not do visual polish detached from task completion.
- Do not claim real-user readiness from API smoke tests alone.

## Gate Plan For This Audit

Required gates for this audit:

- `git diff --check`
- `ruff check docs/ .claude/commands/`
- `python -m pytest tests/test_web_product_copy.py -q --tb=short`

Actual gate evidence is recorded in `docs/dev/progress-ledger.md` after execution.
