# v3.0-v3.6 Long-horizon Auto-run Roadmap

基于 v2.0-v2.5 independent delivery audit (score 93/100) 制定。
审计发现: 1 P1 (SearchIndexPort 代码缺失)、3 P2 (路径不一致/web_facade巨石/navigation割裂)、2 P3。

---

## Design Inspirations (借鉴但不引入外部依赖)

### GraphRAG
- 借鉴: graph extraction、community hierarchy、community summaries、local/global search
- MindForge 吸收: deterministic community/topic layer、explainable context composer、retrieval quality evaluation
- 硬线: 不做 RAG answering、不调用 LLM、不做 embedding/vector DB

### SQLite FTS5 / Local Lexical Search
- 借鉴: 本地全文检索绕开 embedding
- MindForge 吸收: local deterministic lexical search、port boundary、eval framework
- 硬线: 不盲目引入新生产依赖

### Kuzu / Embedded Graph DB
- 借鉴: embedded property graph database 查询能力
- MindForge 吸收: isolated spike、ADR、optional backend boundary
- 硬线: 不直接变成 production dependency

### Local-first Software
- 借鉴: 用户拥有数据、离线可用、隐私、长期保存、可迁移
- MindForge 吸收: local-first workspace、migration、exportability、auditability

---

## v3.0 — Independent Delivery Audit & Quality Debt Burn-down

### Goals
- 修复 v2.0-v2.5 审计 P1/P2 质量债（P1-01 SearchIndexPort 缺失、P2-01 路径不一致）
- 建立 quality debt ledger / delivery truth dashboard
- 建立 gate evidence baseline（完整输出，不允许 tail/head/truncated）
- 处理 P3-02 skipped test
- 最小化变更，不新增大功能

### Non-goals
- 不新增 API endpoint
- 不新增前端页面
- 不修改审批/安全语义
- 不拆分 web_facade.py（留给 v3.1）

### Acceptance Criteria
- [ ] changelog SearchIndexPort 措辞修正 (planned → 准确描述)
- [ ] v2.4 changelog 路径引用更新
- [ ] P3-02 skipped test 确认理由并记录
- [ ] quality debt ledger 文档存在
- [ ] 全部 gate clean (npm build + pytest + ruff + product copy + git diff)
- [ ] implementation notes 完成

### Test Plan
- `git diff --check` (docs-only 改动)
- `npm --prefix web run build` (如涉及前端路径引用)
- `python -m pytest tests/ -q` (如涉及 test skip 修复)

### Smoke Plan
- 如仅 docs 改动: 不 smoke
- 如涉及代码: browser smoke (Home/Library/Setup 关键页面)

### Implementation Notes
`docs/implementation-notes/2026-05-25-072-v3_0-quality-debt-burn-down.md`

### Stop Conditions
- HARD_STOP_P0_P1_RETRY_EXCEEDED
- HARD_STOP_GIT_UNSAFE_STATE

### Next-stage Transition
v3.0 完成 → v3.1 (Local-first Workspace Persistence)

---

## v3.1 — Local-first Workspace Persistence & Migration

### Goals
- 明确 workspace 数据布局、schema/version、migration、sample workspace
- 建立 local-first data ownership / exportability / migration readiness
- 拆分 web_facade.py 按 domain (import/export/lifecycle/dogfood 各自 service facade)
- 做 fake/sample workspace migration smoke

### Non-goals
- 不处理真实私人资料
- 不写真实 Obsidian vault
- 不做破坏性数据迁移
- 不新增外部数据库依赖

### Acceptance Criteria
- [ ] workspace schema version 定义
- [ ] sample workspace fixture (fake 数据)
- [ ] migration 路径（version n → n+1）定义并有 test
- [ ] web_facade.py domain 拆分 (或同等重构)
- [ ] 全部 gate clean
- [ ] 全部 test clean (包括 migration tests)

### Test Plan
- workspace migration contract tests
- fake/sample workspace fixture validation
- pytest full suite
- ruff + git diff --check

### Smoke Plan
- npm build
- product copy tests
- browser smoke (Home/Library/Setup)
- API smoke (lifecycle endpoint)

### Implementation Notes
`docs/implementation-notes/2026-05-25-073-v3_1-local-first-workspace.md`

### Stop Conditions
- HARD_STOP_P0_P1_RETRY_EXCEEDED
- HARD_STOP_LARGE_DEPENDENCY (如意外引入新数据库框架)
- HARD_STOP_PRIVATE_DATA (如需处理真实数据)
- HARD_STOP_GIT_UNSAFE_STATE

---

## v3.2 — Deep Retrieval Quality Evaluation

### Goals
- 给 graph/search/retrieval/context composer 建 eval framework
- 设计 deterministic benchmark fixtures
- 指标: precision-like checks、explainability coverage、provenance coverage、duplicate/contradiction behavior、no hallucinated relation

### Non-goals
- 不做 LLM judge
- 不做 embedding
- 不做 vector DB
- 不做 RAG answering
- 不调用真实 provider

### Acceptance Criteria
- [ ] deterministic benchmark fixtures (synthetic knowledge cards + ground truth relations)
- [ ] eval metrics: precision/recall-like, explainability coverage, provenance coverage
- [ ] retrieval quality report 可生成
- [ ] 全部 gate clean
- [ ] benchmark 可重复运行 (deterministic)

### Test Plan
- eval framework tests
- benchmark runner tests
- pytest full suite

### Smoke Plan
- API smoke (retrieval/recall endpoint)
- benchmark CLI run

### Implementation Notes
`docs/implementation-notes/2026-05-25-074-v3_2-retrieval-quality-eval.md`

---

## v3.3 — Community / Topic Sensemaking Layer

### Goals
- 借鉴 GraphRAG community hierarchy / topic summaries，但 deterministic/local/fake-safe
- topic/community grouping、community evidence、representative cards、source coverage
- 每个 community/topic 必须有 reason/evidence
- UI: community browser / topic map

### Non-goals
- 不做 LLM summary
- 不做 RAG answering
- 不做 embedding-based clustering
- 不调用外部 API

### Acceptance Criteria
- [ ] deterministic topic/community detection enhancement
- [ ] representative card selection per community
- [ ] community evidence trail (why these cards belong together)
- [ ] UI: topic map / community browser enhancement
- [ ] 全部 gate clean + browser smoke

### Test Plan
- community detection accuracy tests (synthetic benchmark)
- evidence completeness tests
- UI component tests (product copy)

### Smoke Plan
- npm build + product copy tests
- browser smoke (Library community view, topic map)

---

## v3.4 — Dogfood Scenario Automation

### Goals
- 把 import → ai_draft → review → approve → graph/search → export/report fake/local dogfood 做成自动场景
- 产出 dogfood report artifact
- 覆盖 CLI/API/Web smoke

### Non-goals
- 不调用真实 LLM/Cubox/Upstage
- 不处理真实私人资料
- 不自动 approve human_approved (fake fixture 明确模拟用户动作)

### Acceptance Criteria
- [ ] automated dogfood scenario runner (import + review + approve + search + export)
- [ ] dogfood report artifact (JSON/Markdown)
- [ ] CLI command: `mindforge dogfood run`
- [ ] 全部 gate clean + browser smoke

### Test Plan
- dogfood scenario runner tests
- report artifact format validation
- CLI integration tests

---

## v3.5 — Workbench UX Integration

### Goals
- 统一 Workspace Home / Library / Wiki / Graph / Search / Review / Import / Export / Dogfood / Provider Readiness 产品入口
- 减少割裂页面
- 优化 user journey 和 product copy
- 处理 P2-03 (Import/Export 独立导航)

### Non-goals
- 不做前端框架迁移
- 不引入新 UI 库
- 不做重大 redesign

### Acceptance Criteria
- [ ] 统一导航结构 (Import/Export 独立入口)
- [ ] user journey 优化 (主要路径 ≤2 次点击)
- [ ] product copy 一致性审查
- [ ] 全部 gate clean + full browser smoke

---

## v3.6 — Safe Extensibility & Plugin Boundary

### Goals
- 沉淀 SourceAdapter / ExportAdapter / Provider / GraphBackend / SearchBackend 插件边界
- 明确 extension manifest / capability / risk / approval policy
- fake/local/sample adapter 实现
- architecture decision 文档

### Non-goals
- 不实现真实外部服务
- 不读取 .env/secrets
- 不调用真实 provider
- 不实现动态插件加载 (仅定义边界)

### Acceptance Criteria
- [ ] extension manifest schema 定义
- [ ] capability/risk/approval policy 文档
- [ ] sample adapter (fake source adapter)
- [ ] architecture decision 记录
- [ ] 全部 gate clean

---

## Self-review

### 是否足够支撑长时间 auto-run?
是。6 个阶段从质量债清偿 (v3.0) → 架构加固 (v3.1) → 质量评估 (v3.2) → 功能深化 (v3.3) → 场景自动化 (v3.4) → 产品化 (v3.5) → 可扩展性 (v3.6) 形成完整链路。

### 每个阶段是否有明确 goals/non-goals/tests/smoke?
是。每个阶段定义了 goals、non-goals、acceptance criteria、test plan、smoke plan、implementation notes、stop conditions。

### 是否先处理了质量而不是堆功能?
是。v3.0 专门处理 v2.0-v2.5 审计发现的质量债，v3.1 处理架构组织债，然后才进入新功能。

### 红线检查
- ❌ RAG answering? 否 — 全程不做
- ❌ Embedding/vector DB? 否 — 全程不做
- ❌ 真实 LLM/Cubox/Upstage? 否 — 全程不调用
- ❌ 真实私人资料? 否 — 全程 fake/sample
- ❌ 真实 Obsidian write? 否 — 全程不做
- ❌ 破坏审批语义? 否 — 全程保持 ai_draft → explicit approval → human_approved
- ❌ 大型依赖? 否 — 不引入
- ❌ 每步都停下来问? 否 — auto-continue contract 全程生效
