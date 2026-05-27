# Progress Ledger

**MindForge 项目进度跟踪。** 每条记录包含: date, commit, goal, outcome, docs produced, remaining debt.

每个 `/mf-autopilot` loop 结束必须更新此文件。即使小 bug fix 也至少加一条简短记录。

---

## 1. Completed Major Loops

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

**当前 active workstream: Documentation Reset (2026-05-27)**

- Batch 1 已完成: 8 个 stale 文件删除 + 引用更新
- Batch 2: 待处理残留引用（历史 RFC/SDD/spec/implementation-notes 中的 stale references）
- 不涉及产品功能、UI、backend

---

## 3. Next Recommended Loop

1. **继续 documentation reset** — 创建 documentation-reset-plan.md + 执行第一批 stale doc cleanup
2. 回到 product work — 参见 `CURRENT_PROJECT_STATE.md` §6

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
