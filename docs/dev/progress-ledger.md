# Progress Ledger

**MindForge 项目进度跟踪。** 每条记录包含: date, commit, goal, outcome, docs produced, remaining debt.

每个 `/mf-autopilot` loop 结束必须更新此文件。即使小 bug fix 也至少加一条简短记录。

---

## 1. Completed Major Loops

### 2026-05-27: Autopilot Governance — Auto-Continue Policy Hardening

- **Commit**: `3c829da` → (pending)
- **Workstream**: Autopilot Governance
- **Task type**: autopilot_governance
- **Outcome**: 修复 /mf-autopilot auto-continue 治理 bug：新增 §5.7 Auto-Continue Decision Table（12 auto-continue + 10 must-ask 条件）、§5.8 Self-routing after final report（6 步自路由流程）、§5.9 Banned soft-stop phrases（8 个禁止表述）。注册 autopilot_governance task type。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-121-mf-autopilot-auto-continue-policy.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Architecture Quality Reset plan（现在通过 auto-continue 规则可直接进入 plan 编写）
- **Workstream changed**: yes (from Web IA/UX Loop 2 to Autopilot Governance)

### 2026-05-27: Web IA/UX Loop 2 — Post-Dogfood User-Facing Debt Fix

- **Commit**: `97d57fb` → (pending)
- **Workstream**: Web IA/UX Loop 2
- **Task type**: ui_ux_polish
- **Outcome**: 修复 3 个 P1 Web IA/UX 问题: (1) Dogfood nav 从 tools 移至 collapsed lab section, (2) DogfoodPage 添加 LAB/INTERNAL 横幅, (3) LocalGraphPreview 硬编码英文替换为 i18n。ExportPage 和 SetupPage 经审计确认无 drift。
- **Docs/notes**: `docs/audits/2026-05-27-120-web-ia-ux-loop-2-audit.md`, `docs/implementation-notes/2026-05-27-120-web-ia-ux-loop-2.md`
- **Gates**: `git diff --check` (0), `npm --prefix web run build` (0), `pytest tests/test_web_product_copy.py -q --tb=short` (0), `ruff check src/ tests/ docs/` (0)
- **Next**: Architecture Quality Reset (需先写 spec/plan)
- **Workstream changed**: no (Web IA/UX Loop 2 本 loop 完结)

### 2026-05-27: Product Main Path Real Dogfood — FakeProvider Keyword Extraction Improvement

- **Commit**: `20a3038` → (pending)
- **Workstream**: Product Main Path Real Dogfood
- **Task type**: dogfood
- **Outcome**: FakeProvider distill keyword extraction 从 title-only 改进为 title + prompt raw_text（最多 12000 chars 真实原文）。English recall hit rate 从 ~40% 提升到 91.7% (11/12)。Full pipeline (scan→process→approve→library→recall→wiki) 全部通过。Chinese recall 0% 因为 source docs 全是英文 — 这是 source material limitation，非 bug。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-119-fake-provider-keyword-extraction-improvement.md`
- **Gates**: `git diff --check` (0), `ruff check src/ tests/ docs/` (0), `pytest tests/test_web_product_copy.py -q` (0), `pytest tests/ -q` (0), `npm --prefix web run build` (0)
- **Next**: 审计推荐的下一个 loop 是 Web IA/UX Loop 2 或 Architecture Quality Reset；Batch 2 仍暂停（archive/delete rules 不详）
- **Workstream changed**: no (Product Main Path Real Dogfood 本 loop 完结)

### 2026-05-27: Post-Governance Global Red Team Audit

- **Commit**: `7312245` → this audit commit
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

**当前 recommended active workstream: Product Main Path Real Dogfood (2026-05-27)**

- Post-Governance audit 已完成，结论为 Conditional Go
- Batch 1 已完成: 8 个 stale 文件删除 + 残留引用修复（14 个历史文档已标注）
- Batch 2 (Archive Candidates): 暂停自由推进 — 只有 exact archive/delete rules 明确并获批后才执行
- 推荐下一轮验证真实主路径，而不是继续删除文档、扩张 Graph/Sensemaking 或做无路径证据的架构大拆分

---

## 3. Next Recommended Loop

1. **Product Main Path Real Dogfood** — 使用安全、隔离、可复现数据验证 Source/Import → ai_draft → Review → explicit approval → human_approved → Library → Recall/Wiki → Export
2. **Web IA/UX Loop 2** — 修复 Dogfood 主导航、Export 文档/文案漂移、内部术语、Setup cognitive load，并补 fresh browser evidence
3. **Targeted Architecture Quality Reset** — 由 dogfood 证据排序，重点收敛 `web_facade.py`、schema `__init__.py`、facade helper 反向依赖
4. **Documentation Reset Batch 2** — 仅在 exact archive/delete rules 明确后执行

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
