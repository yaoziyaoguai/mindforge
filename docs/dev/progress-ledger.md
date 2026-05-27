# Progress Ledger

**MindForge 项目进度跟踪。** 每条记录包含: date, commit, goal, outcome, docs produced, remaining debt.

每个 `/mf-autopilot` loop 结束必须更新此文件。即使小 bug fix 也至少加一条简短记录。

---

## 1. Completed Major Loops

### 2026-05-27: Autopilot Governance Upgrade — Recursive Remediation + Mandatory Skill Gates + Skill Framework Routing

- **Commit**: `e6f6d09` → `<pending>`
- **Workstream**: Autopilot Governance Upgrade (Round 1 + 2)
- **Task type**: autopilot_governance
- **Outcome**: `/mf-autopilot` 从 workflow router + skill router 升级为 recursive remediation loop controller。新增 §11 recursive remediation loop (4-tier precedence)、§12 failure classification table (9 类)、§13 retry/escalation policy、§14 mandatory skill gates (5 类)、§15 skill framework discovery (Compound Engineering/G-stack/Superpowers)、§16 skill routing decision block、§17 review node rules、§18 post-loop self-routing block、§19-§21 schema 升级 (CPS AUTOPILOT-QUEUE、progress-ledger、HANDOFF.md)。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-138-mf-autopilot-recursive-remediation-and-mandatory-skills.md`, `docs/implementation-notes/2026-05-27-139-mf-autopilot-skill-framework-routing.md`
- **Gates**: `git diff --check` (0), `ruff check .claude/commands/ docs/` (0), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0, 100%)
- **Review result**: PASS
- **Gate result**: PASS
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: G-stack (design-shotgun, design-consultation loaded; Compound Engineering available via ce-work; Superpowers available)
- **Required skill invoked**: yes (ce-work for implementation; mf-autopilot for governance rules; design-shotgun/design-consultation pre-loaded)
- **Next ACTION token**: CONTINUE_NEXT_LOOP
- **Next**: AUTOPILOT-QUEUE-ITEM-2 (Web Product UX Deepening P3)
- **Workstream changed**: yes (Governance ITEM-3 → Autopilot Governance Upgrade)

### 2026-05-27: Dogfood v3 Light Smoke — 验证 P2 UX 修复 + 治理 ITEM-3 完成

- **Commit**: `9be6e5c` → `f5a1136`
- **Workstream**: Dogfood v3 + Governance Truth Drift Fix
- **Task type**: dogfood + docs_cleanup
- **Outcome**: Chrome DevTools MCP 浏览器 smoke 验证 SafetyBar "模型配置：本地模拟" (绿色, P2 fix ✅) + Library breadcrumb "首页 > 知识库" (正确中文 ✅)。Export 页面 library 为空时正确重定向至 setup。治理 ITEM-3: HANDOFF.md status → historical, CPS AUTOPILOT-QUEUE 重置, HEAD refs 校正, quality-debt-ledger 日期更新。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-137-web-product-ux-deepening-loop-1.md`
- **Gates**: `git diff --check` (0), `pytest tests/` (0, 100%), `npm run build` (0), browser MCP smoke (passed)
- **Next**: AUTOPILOT-QUEUE-ITEM-2 (Web Product UX Deepening P3) 或 next-phase planning review
- **Workstream changed**: yes (Web UX Deepening → Governance → Dogfood v3)

### 2026-05-27: Web Product UX Deepening — Loop 1 (P2 Export breadcrumb + SafetyBar demo status)

- **Commit**: `3c214f6` → `9be6e5c`
- **Workstream**: Web Product UX Deepening
- **Task type**: ui_ux_polish
- **Outcome**: 修复 2 项 Dogfood v2 发现的 P2 UX 摩擦 — Export breadcrumb "export" → "导出知识" (Breadcrumb.tsx + routeLabels)，SafetyBar 模型状态 "待检查" → "本地模拟" (model_setup_readiness.py demo mode + SafetyBar.tsx "demo" handling + i18n keys)。同时修复 ruff F541 (test_watch_schedule_baseline.py)。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-137-web-product-ux-deepening-loop-1.md`
- **Gates**: `git diff --check` (0), `npm run build` (0), `npx vitest run` (0, 50 passed/6 files), `pytest tests/` (0, 100%), `pytest tests/test_web_product_copy.py` (0, 100%), `ruff check` (0)
- **Next**: 继续 AUTOPILOT-QUEUE ITEM-1 (Web Product UX Deepening) 剩馀 P3 项，或 ADVANCE to ITEM-2 (Targeted Architecture Quality Reset)
- **Workstream changed**: no

### 2026-05-27: P1 管道阻塞修复 — demo/fake 模式自动回退

- **Commit**: `256f5be` → `87453f0`
- **Workstream**: Product Main Path Real Dogfood v2 (P1 fix)
- **Task type**: bug_fix
- **Outcome**: 修复 P1 管道阻塞 — CLI import/process/watch 和 Web import/scan 在无模型配置时自动注入 fake profile。`apply_provider_selection()` (CLI) 和 `_ensure_processing_model_configured()` (Web) 两处注入点。9 个测试从期望 error 改为期望 auto-fallback success。fake models 仅在内存注入，不写 YAML，不污染 Setup UI。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-136-p1-pipeline-blocker-auto-fallback-fake.md`
- **Gates**: `ruff check` (0), `pytest tests/` (0, 100%), `npm run build` (0), `pytest tests/test_web_product_copy.py` (0, 80 passed), `git diff --check` (0)
- **Next**: Web Product UX Deepening (Codex audit §10.B 推荐次优先)
- **Workstream changed**: yes (Dogfood v2 → Web Product UX Deepening)

### 2026-05-27: Product Main Path Real Dogfood v2

- **Commit**: `4ef9ed2` → `256f5be`
- **Workstream**: Product Main Path Real Dogfood v2
- **Task type**: dogfood
- **Outcome**: 完成 Chrome DevTools MCP 浏览器级别完整主路径 walkthrough — Source→Draft→Review→Approval→Library→Recall→Wiki→Export 全部通过。记录 8 项 UX 摩擦发现 (P1×1, P2×2, P3×5)。P1 发现: demo/fake 模式并非真正零配置，import 管道在无模型时报错。Governance truth sync 完成 CPS/ledger 状态更新。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-135-product-main-path-real-dogfood-v2.md`
- **Gates**: `ruff check` (0), `pytest tests/` (0, 100%), `npm run build` (0), `pytest tests/test_web_product_copy.py` (0), MCP smoke 8 页全部通过
- **Next**: 修复 P1 管道阻塞 (demo/fake 模式零配置) → 然后进入 Web Product UX Deepening
- **Workstream changed**: yes (Dogfood v2 → P1 Fix)

### 2026-05-27: Codex Independent Strategic Red Team Audit

- **Commit**: `4ef9ed2`
- **Workstream**: Independent Strategic Red Team Audit
- **Task type**: audit_only
- **Outcome**: 完成一次独立、只读、战略红队审计。结论为 Conditional Go，总分 6.4/10。最强资产仍是 approval-first personal knowledge compiler；主要风险是产品习惯未验证、Web 仍有工程控制台味、治理 truth drift、Export 契约不一致、WebFacade/配置服务仍偏巨石。未修改产品代码、Web 代码、测试代码、`/mf-autopilot`，未切换 active workstream。
- **Docs/notes**: `docs/audits/2026-05-27-133-codex-independent-strategic-red-team-audit.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0; warning: no Python files found), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Primary recommendation: Product Main Path Real Dogfood v2. Secondary recommendation: Web Product UX Deepening. Do not resume Graph/Sensemaking/Entity/Community expansion, RAG/vector/embedding, broad architecture reset, or real LLM runs without explicit user decision and negative safety tests.
- **Workstream changed**: no

### 2026-05-27: AUDIT-118 P1 Product Debt Closure

- **Commit**: `e6dbe9b`
- **Workstream**: AUDIT-118 P1 Product Debt Closure
- **Task type**: ui_ux_polish + docs_cleanup + smoke_evidence
- **Outcome**: 关闭全部 4 项剩余 AUDIT-118 P1 产品债。AUDIT-118-01: user guides + README 更新 Export 文档，标注 browser-local download；AUDIT-118-02: Dogfood i18n label 加 (Internal) 标记，user guides 重写为内部工具；AUDIT-118-04: Chrome DevTools MCP smoke 验证主路径全部页面正常；AUDIT-118-05: HANDOFF.md 新增 status 字段体系 (active/completed/resolved/historical)，CPS §8 更新读取规则。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-132-audit-118-product-debt-closure.md`
- **Gates**: `git diff --check` (0), `npm run build` (0), `npm run test` (0, 50 passed/6 files), `pytest tests/test_web_product_copy.py` (0)
- **Next**: 按 CPS §6 AUTOPILOT-QUEUE 继续 frontend test coverage expansion 或 Documentation Reset Batch 2
- **Workstream changed**: yes (AUDIT-118 → Quality Platform)

### 2026-05-27: Breadcrumb / SafetyBar Component Tests

- **Commit**: `7acb47e`
- **Workstream**: Quality Platform / Frontend Test Coverage
- **Task type**: feature_implementation
- **Outcome**: Breadcrumb (9 tests) + SafetyBar (16 tests) 组件测试。解决了 useLocale() i18n context provider 问题 — 使用 LocaleProvider 包裹被测组件。SafetyBar 的 split text node 问题用正则匹配修复。测试文件 4→6，测试用例 25→50。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-131-breadcrumb-safetybar-tests.md`
- **Gates**: `git diff --check` (0), `npm run build` (0), `npm run test` (0, 50 passed/6 files), `pytest tests/test_web_product_copy.py` (0, 84 passed)
- **Next**: 剩余低风险测试项已全部覆盖（6/41 组件已测试）。AUDIT-118 产品债（Export docs、Dogfood nav）需产品决策，非测试补强范围。
- **Workstream changed**: no

### 2026-05-27: Architecture Doc Audit Fix

- **Commit**: `7223203` → `140a472`
- **Workstream**: Quality Platform
- **Task type**: audit_only
- **Outcome**: 修复 architecture.md 两处不一致 — 补充 `mindforge_web/presenters/` 目录、更新 web_facade.py 行数 1487 (-31.3%) → 922 (-57.4%)
- **Gates**: `git diff --check` (0)

### 2026-05-27: Web Frontend Test Coverage Expansion

- **Commit**: `91f5ec7` → `7223203`
- **Workstream**: Frontend Quality
- **Task type**: feature_implementation
- **Outcome**: 前端组件测试从 1 文件/2 测试扩展到 4 文件/25 测试。新增 LoadingSkeleton (2 tests, 10 variants)、EmptyState (6 tests)、StatusCard (6 tests) 的测试文件。全部 25 个测试通过。
- **Docs/notes**: `docs/plans/2026-05-27-129-web-frontend-test-expansion.md`, `docs/implementation-notes/2026-05-27-130-web-frontend-test-expansion.md`
- **Gates**: `ruff check` (0), `git diff --check` (0), `npm run build` (0), `npm run test` (0, 25 passed/4 files), `pytest tests/test_web_product_copy.py` (0, 84 passed)
- **Next**: 继续扩展 Breadcrumb/SafetyBar（需 i18n context）或 page-level smoke tests
- **Workstream changed**: no

### 2026-05-27: Documentation Reset Batch 2

- **Commit**: `fb98003` → `91f5ec7`
- **Workstream**: Documentation Reset
- **Task type**: docs_cleanup
- **Outcome**: DOC-01: 创建 docs/README-en.md 英文版文档入口。DOC-02: ADR-006 frontmatter status 从 active → partial (4/8 NodeType)。DOC-03: docs/design/README.md 新增 historical/reference 状态说明，obsidian-binding-design.md 标记 deferred。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-128-docs-reset-batch-2.md`
- **Gates**: `git diff --check` (0)
- **Next**: Web frontend test coverage expansion（vitest + happy-dom 基础设施已就绪）
- **Workstream changed**: no

### 2026-05-27: v3.7 Quality Platform

- **Commit**: `e159e29` → `fb98003`
- **Workstream**: v3.7 Quality Platform
- **Task type**: feature_implementation
- **Outcome**: P2-05 (vitest + happy-dom + @testing-library/react 前端测试基础设施) + P2-06 ([tool.coverage] 配置, pytest --cov 可用, 88% baseline) + web_config_service.py env detection 提取至 web_config_env.py。ErrorState 组件测试示范通过。
- **Docs/notes**: `docs/plans/2026-05-27-127-v3.7-quality-platform.md`, `docs/implementation-notes/2026-05-27-127-v3.7-quality-platform.md`
- **Gates**: `ruff check` (0), `git diff --check` (0), `npm run build` (0), `npm run test` (0, 2 passed), `pytest tests/` (0, ~3030 passed/1 skip), `pytest --cov` (0, 88%), `pytest tests/test_web_product_copy.py` (0)
- **Next**: Documentation Reset Batch 2（archive/delete 规则已明确）
- **Workstream changed**: yes (from Autopilot Governance to v3.7 Quality Platform)

- **Commit**: `e159e29`
- **Workstream**: Autopilot Governance
- **Task type**: autopilot_governance
- **Outcome**: 修复 /mf-autopilot 在 workstream 完成→新 workstream spec/plan 时误判停止的 bug。§5.3 rule 5 workstream 切换优先级明确化（完成→自动切换）。§5.7 新增跨 workstream spec/plan auto-continue 条目。§5.8 强制 ACTION token 输出（CONTINUE_NEXT_LOOP / HANDOFF_AND_STOP / HARD_STOP_<CODE>）。§5.9 新增 5 个软停禁令表述。CPS §6 新增 machine-readable AUTOPILOT-QUEUE 注释。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-126-mf-autopilot-cross-workstream-fix.md`
- **Gates**: (pending run)
- **Next**: v3.7 Quality Platform spec/plan 编写（现在 auto-continue allowed）
- **Workstream changed**: yes (from Architecture Quality Reset to Autopilot Governance)

### 2026-05-27: Architecture Quality Reset — Slice 2 (Extract web_facade.py Private Helpers to Presenters)

- **Commit**: `9c598a4` → `70a1475`
- **Workstream**: Architecture Quality Reset
- **Task type**: architecture_refactor
- **Outcome**: 将 web_facade.py 中 ~540 行私有 helper 函数提取到 5 个 presenter 子模块（shared/graph/library/discovery/provenance）。web_facade.py 从 1487 行降至 922 行 (-38.0%)，累计从 2163 行减少 57.4%。所有命名 `_xxx` → `build_xxx`/`get_xxx`。3 个 service 文件 + 2 个测试文件导入更新。零行为变更，零循环导入。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-125-architecture-quality-reset-slice-2.md`
- **Gates**: `ruff check src/ tests/` (0), `pytest tests/ -q --tb=short` (0, 545 passed/1 skipped), `git diff --check` (0), `npm --prefix web run build` (0), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Architecture Quality Reset Slice 1+2 完成，workstream 完结。剩余 debt (P2-05/P2-06/web_config_service split) deferred to v3.7。
- **Workstream changed**: no

### 2026-05-27: Architecture Quality Reset — Slice 1 (Fix Core→Web Layer Violation)

- **Commit**: `c4f5c25` → `2cba857`
- **Workstream**: Architecture Quality Reset
- **Task type**: architecture_refactor
- **Outcome**: 将 processing run 持久化/查询/worker 逻辑从 web 层迁移到 `src/mindforge/processing/run_store.py`（core 层）。5 个 core 模块的 import 路径更新。2 个 private symbol import（`_run_worker`、`_save_record`）消除。边界测试已知违规条目从 7 减至 2。层依赖方向修复：web → core。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-124-architecture-quality-reset-slice-1.md`
- **Gates**: `ruff check src/ tests/` (0), `pytest tests/test_architecture_boundaries.py -q --tb=short` (0, 14 passed), `pytest tests/ -q --tb=short` (0, 100%), `pytest tests/test_web_product_copy.py -q --tb=short` (0), `npm --prefix web run build` (0), `git diff --check` (0)
- **Next**: Slice 2 — 提取 web_facade.py 私有 helper 到 presenters
- **Workstream changed**: no

### 2026-05-27: Architecture Quality Reset — Plan + Slice 0 Boundary Tests

- **Commit**: `1b39edb` → `8eb3fd4`
- **Workstream**: Architecture Quality Reset
- **Task type**: architecture_refactor (plan/spec + boundary tests)
- **Outcome**: 完成 architecture evidence audit + targeted reset plan（7 个 core→web 反向依赖、3 个 implementation slices）。Slice 0 在 test_architecture_boundaries.py 中新增 6 个架构边界测试（3 个 test class），全部 14 个测试通过。plan 明确 Slice 1 修复 core→web 层反向依赖、Slice 2 提取 presenter、Slice 3+ deferred。
- **Docs/notes**: `docs/plans/2026-05-27-122-targeted-architecture-quality-reset.md`, `docs/implementation-notes/2026-05-27-123-architecture-quality-reset-plan-slice-0.md`
- **Gates**: `git diff --check` (0), `ruff check src/ tests/ docs/` (0), `pytest tests/test_architecture_boundaries.py -q --tb=short` (0, 14 passed), `pytest tests/test_web_product_copy.py -q --tb=short` (0, 9 passed), `npm --prefix web run build` (0)
- **Next**: Slice 1 — 修复 core→web 反向依赖（需 plan 批准后执行）
- **Workstream changed**: yes (from Autopilot Governance)

### 2026-05-27: Autopilot Governance — Auto-Continue Policy Hardening

- **Commit**: `3c829da` → `56b3d23`
- **Workstream**: Autopilot Governance
- **Task type**: autopilot_governance
- **Outcome**: 修复 /mf-autopilot auto-continue 治理 bug：新增 §5.7 Auto-Continue Decision Table（12 auto-continue + 10 must-ask 条件）、§5.8 Self-routing after final report（6 步自路由流程）、§5.9 Banned soft-stop phrases（8 个禁止表述）。注册 autopilot_governance task type。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-121-mf-autopilot-auto-continue-policy.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Architecture Quality Reset plan（现在通过 auto-continue 规则可直接进入 plan 编写）
- **Workstream changed**: yes (from Web IA/UX Loop 2 to Autopilot Governance)

### 2026-05-27: Web IA/UX Loop 2 — Post-Dogfood User-Facing Debt Fix

- **Commit**: `6145b72`
- **Workstream**: Web IA/UX Loop 2
- **Task type**: ui_ux_polish
- **Outcome**: 修复 3 个 P1 Web IA/UX 问题: (1) Dogfood nav 从 tools 移至 collapsed lab section, (2) DogfoodPage 添加 LAB/INTERNAL 横幅, (3) LocalGraphPreview 硬编码英文替换为 i18n。ExportPage 和 SetupPage 经审计确认无 drift。
- **Docs/notes**: `docs/audits/2026-05-27-120-web-ia-ux-loop-2-audit.md`, `docs/implementation-notes/2026-05-27-120-web-ia-ux-loop-2.md`
- **Gates**: `git diff --check` (0), `npm --prefix web run build` (0), `pytest tests/test_web_product_copy.py -q --tb=short` (0), `ruff check src/ tests/ docs/` (0)
- **Next**: Architecture Quality Reset (需先写 spec/plan)
- **Workstream changed**: no (Web IA/UX Loop 2 本 loop 完结)

### 2026-05-27: Product Main Path Real Dogfood — FakeProvider Keyword Extraction Improvement

- **Commit**: `97d57fb`
- **Workstream**: Product Main Path Real Dogfood
- **Task type**: dogfood
- **Outcome**: FakeProvider distill keyword extraction 从 title-only 改进为 title + prompt raw_text（最多 12000 chars 真实原文）。English recall hit rate 从 ~40% 提升到 91.7% (11/12)。Full pipeline (scan→process→approve→library→recall→wiki) 全部通过。Chinese recall 0% 因为 source docs 全是英文 — 这是 source material limitation，非 bug。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-119-fake-provider-keyword-extraction-improvement.md`
- **Gates**: `git diff --check` (0), `ruff check src/ tests/ docs/` (0), `pytest tests/test_web_product_copy.py -q` (0), `pytest tests/ -q` (0), `npm --prefix web run build` (0)
- **Next**: 审计推荐的下一个 loop 是 Web IA/UX Loop 2 或 Architecture Quality Reset；Batch 2 仍暂停（archive/delete rules 不详）
- **Workstream changed**: no (Product Main Path Real Dogfood 本 loop 完结)

### 2026-05-27: Post-Governance Global Red Team Audit

- **Commit**: `20a3038`
- **Workstream**: Post-Governance Global Red Team Audit
- **Task type**: audit_only
- **Outcome**: 完成一次只读全局红队审计；结论为 Conditional Go，总分 6.1/10。主路径和 approval-first 安全语义是最强资产；下一步不建议自由推进 Batch 2，而应优先做 Product Main Path Real Dogfood。
- **Docs/notes**: `docs/audits/2026-05-27-118-post-governance-global-red-team-audit.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0; warning: no Python files found), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Product Main Path Real Dogfood；secondary: Web IA/UX Loop 2；Batch 2 暂停，除非 exact archive/delete rules 获批
- **Workstream changed**: yes (from Documentation Reset to Product Main Path Real Dogfood recommendation)

### 2026-05-27: Docs Cleanup — Batch 1 Residual References Cleaned

- **Commit**: `ac6aa47`
- **Workstream**: Documentation Reset
- **Task type**: docs_cleanup
- **Outcome**: 修复 Batch 1 删除 8 个 stale files 后的 ~15 个跨文档残留引用；14 个历史文档标注 "(removed 2026-05-27)"；3 个 management docs 更新引用状态
- **Docs/notes**: `docs/implementation-notes/2026-05-27-117-docs-cleanup-residual-references.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q` (0)
- **Next**: 评估 Batch 2 (Archive Candidates) 是否已明确
- **Workstream changed**: no

### 2026-05-27: Docs Cleanup Batch 1 — 8 stale files removed

- **Commit**: `fcb96c7`
- **Workstream**: Documentation Reset
- **Task type**: docs_cleanup
- **Outcome**: 删除 8 个明显过时文档（v0.2/v0.3 roadmap、TDD/SDD、v0.2/v0.3 dev rules、早期 dogfood plans）；更新 documentation-reset-plan、documentation-inventory、docs-reset-index 中的引用
- **Docs/notes**: `docs/implementation-notes/2026-05-27-116-docs-cleanup-batch-1.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q` (0)
- **Next**: batch 2（处理历史 RFC/SDD/spec/implementation-notes 中的残留引用）
- **Workstream changed**: yes (from mf-autopilot reliability upgrade)

### 2026-05-27: mf-autopilot Reliability Upgrade

- **Commit**: `64d7a52`
- **Workstream**: mf-autopilot Reliability Upgrade
- **Task type**: docs_cleanup
- **Outcome**: 补齐 4 类治理规则 — active workstream rules、stale window rules、progress template、handoff protocol
- **Docs/notes**: `docs/implementation-notes/2026-05-27-115-mf-autopilot-reliability-upgrade.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Documentation cleanup batch 1
- **Workstream changed**: no (continuing governance work)

### 2026-05-27: Docs Reset & Governance — Loop 1 (canonical state + progress ledger)

- **Commit**: `0248755`
- **Workstream**: Documentation Reset & Project Governance
- **Task type**: docs_cleanup
- **Outcome**: 创建 CURRENT_PROJECT_STATE.md, progress-ledger.md, documentation-reset-plan.md；升级 mf-autopilot 为 task-type-aware；更新 docs/README.md
- **Docs/notes**: `docs/implementation-notes/2026-05-27-114-docs-reset-governance-loop-1.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q` (0)
- **Next**: mf-autopilot reliability upgrade (active workstream / stale window / progress template / handoff)
- **Workstream changed**: no (continuing governance work)

### 2026-05-27: Export Page MVP

- **Commit**: `fb87ce0` → `6f5db2c`
- **Goal**: 实现独立的 `/export` 页面（之前 fallthrough 到 Home）
- **Outcome**: 完成。14 种 UX states 覆盖，MCP 浏览器验证通过
- **Docs**: `docs/plans/2026-05-27-112-export-page-product-spec.md`, `docs/implementation-notes/2026-05-27-113-export-page-mvp.md`
- **Remaining debt**: 无

### 2026-05-27: Backend Copy & ID Sanitization

- **Commit**: `7bb4a76` → `9eb4108`
- **Goal**: 修复后端生成的英文用户可见文案（Health / Wiki 标签 → 中文）
- **Outcome**: 完成。health_service.py 8 项检查消息 + wiki_service.py 标签全部中文化
- **Docs**: `docs/implementation-notes/2026-05-27-112-backend-copy-and-id-sanitization.md`
- **Remaining debt**: `__model_routing__` 出现在卡片内容中（pre-existing，非本次修）

### 2026-05-27: Web IA Simplification

- **Commit**: `54110d4` → `a1556f9`
- **Goal**: 前端 IA 精简——隐藏内部标签、格式化时间戳、替换 BM25 术语
- **Outcome**: 完成。Sidebar 重组，SourcesPage 渐进展示，Recall 页面术语替换
- **Docs**: `docs/implementation-notes/2026-05-27-111-web-ia-simplification.md`
- **Remaining debt**: 少量 Web IA 碎片待后续清理

### 2026-05-26: Design QA — Stage 1–6

- **Commits**: `a138177` → `07bd8a0`
- **Goal**: Web 视觉设计系统落地（CSS tokens → AppShell → Review → Library → Home → 一致性 pass）
- **Outcome**: 完成 6 个 Stage
- **Docs**: `docs/implementation-notes/2026-05-26-110-stage-6-design-qa.md`
- **Remaining debt**: 无

### 2026-05-26: v4.4 Product Main Path UX Deepening

- **Commits**: within `docs/implementation-notes/2026-05-26-095-v4_4-product-main-path-ux-deepening.md`
- **Goal**: FirstRunGuide、ImportPathCard、安全说明、导出安全通知
- **Outcome**: 完成 A1–A6
- **Docs**: `docs/implementation-notes/2026-05-26-095-v4_4-product-main-path-ux-deepening.md`
- **Remaining debt**: 无

### 2026-05-25: Product Main Path Dogfood

- **Goal**: fake sampler 跑完整 product main path
- **Outcome**: 42/42 样本通过。Recall 10/10。Wiki rebuild 通过
- **Docs**: `docs/implementation-notes/2026-05-25-090-product-main-path-dogfood-execution.md`, `docs/implementation-notes/2026-05-25-091-product-main-path-hardening.md`
- **Remaining debt**: P3-04 (BM25 body 字段增量贡献有限)

### 2026-05-25: v4.2 Red Team Stabilization

- **Goal**: 收缩 Graph/Sensemaking 暴露面、package safety、docs truth reset
- **Outcome**: P1–P4 全部关闭
- **Docs**: `docs/implementation-notes/2026-05-25-086-v4_2-red-team-stabilization.md`
- **Remaining debt**: 无

### 2026-05-25: v3.6.1 Remediation Batch A

- **Goal**: 修复 v2.0-v3.6 独立审计的 P0/P1 issues
- **Outcome**: A1 (docx importorskip) + A2 (flaky perf test) + A3 (gate baseline) + A4 (architecture.md 引用) + B1 (zh-CN user-guide sync) + B2 (recall_service → RetrievalPort)
- **Docs**: `docs/implementation-notes/2026-05-25-079-v3_6_1-remediation-batch-a.md`
- **Remaining debt**: P2-05 (前端测试), P2-06 (覆盖率)

### 2026-05-24/25: v3.7–v4.1 Graph/Sensemaking 全链路

- **Goal**: Graph Ontology → Graph View → Entity Resolution → Sensemaking → GraphRepository
- **Outcome**: 完成但后续被 v4.2 red team 收缩
- **Remaining debt**: 已由 v4.2 truth reset 处理

---

## 2. Active Workstream

**当前 active workstream: Product Main Path Real Dogfood v2 (2026-05-27)**

- 由 Codex 独立红队审计 (commit `4ef9ed2`, §10.A) 推荐为 primary next loop
- 目标: 完整主路径 browser-level dogfood — Source→Draft→Review→Approval→Library→Recall→Wiki→Export
- 记录 UX 摩擦，验证 acceptance criteria，不调用真实 LLM/API/Obsidian vault

---

## 3. Next Recommended Loop

按 Codex 审计推荐顺序:

1. **Product Main Path Real Dogfood v2** — 当前 active workstream。完整 main path browser/API dogfood，记录 UX 摩擦，验证 acceptance criteria。
2. **Web Product UX Deepening** — 待 dogfood v2 完成后，基于真实摩擦修复 Library IA、Export contract、Setup clarity。
3. **Targeted Architecture Quality Reset** — 仅在 dogfood/UX 暴露真实架构痛点后执行。

---

## 4. How to Update This Ledger

每个 `/mf-autopilot` loop 结束，按以下模板在 §1 顶部添加记录:

```markdown
### YYYY-MM-DD: <简短标题>

- **Commit**: `<hash>` 或 `<start-hash>` → `<end-hash>`
- **Workstream**: <active workstream name>
- **Task type**: <bug_fix | docs_cleanup | ui_ux_polish | architecture_refactor | feature_implementation | audit_only | dogfood | design_review>
- **Outcome**: <1-2 句话描述结果>
- **Docs/notes**: <新建的 docs/implementation-notes 路径>
- **Gates**: <gate 命令 + exit codes>
- **Next**: <推荐的 next loop>
- **Workstream changed**: yes / no
```

Minor bug fix 至少追加一行:
```markdown
- YYYY-MM-DD: <描述> (`<hash>`)
```

**commit/push 不是间隔点** — 一个 major loop 可能包含多个 commit，合写在一条记录里。
