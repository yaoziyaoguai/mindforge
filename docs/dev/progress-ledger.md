# Progress Ledger

**MindForge 项目进度跟踪。** 每条记录包含: date, commit, goal, outcome, docs produced, remaining debt.

每个 `/mf-autopilot` loop 结束必须更新此文件。即使小 bug fix 也至少加一条简短记录。

---

## 1. Completed Major Loops

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

**当前 active workstream: Documentation Reset & Project Governance (2026-05-27)**

- Loop 1 (done): canonical state + progress ledger + autopilot upgrade
- Loop 2 (next): docs cleanup batch 1 — 删除 8 个 stale files (per `docs/dev/documentation-reset-plan.md`)

---

## 3. Next Recommended Loop

1. **继续 documentation reset** — 创建 documentation-reset-plan.md + 执行第一批 stale doc cleanup
2. 回到 product work — 参见 `CURRENT_PROJECT_STATE.md` §6

---

## 4. How to Update This Ledger

每个 `/mf-autopilot` loop 结束:
1. 如果是 major loop (新功能/修复/重构): 在 §1 顶部添加记录 (date, commit, goal, outcome, docs, remaining debt)
2. 如果是 minor fix: 在对应 major loop 下追加一行
3. 更新 §2 Active Workstream (如有变化)
4. 更新 §3 Next Recommended Loop

**commit/push 不是间隔点** — 一个 major loop 可能包含多个 commit，合写在一条记录里。
