---
title: v1.0 Knowledge Workbench Experience — Next-Phase Planning Review
type: planning-review
status: draft
date: 2026-05-24
parent: 2026-05-24-026-v0_7-v1_0-multi-stage-roadmap.md
supersedes: v0.9 Kuzu ADR (deferred)
---

# v1.0: 从 Graph Foundation 到 Knowledge Workbench

## 0. 已完成能力盘点（v0.1–v0.9）

### 已交付的核心能力

| 能力 | 版本 | 形式 |
|------|------|------|
| Source Ingestion (Markdown/TXT/HTML/PDF/DOCX) | v0.1-v0.2 | CLI + Web Sources |
| AI Draft → Explicit Approve → human_approved | v0.1-v0.2 | CLI + Web Review |
| Library (已审批卡片浏览/编辑) | v0.2 | Web Library |
| Wiki (LLM synthesis + deterministic fallback) | v0.2 | Web Wiki |
| BM25 Lexical Recall | v0.3 | CLI + Web Search |
| Card Quality (score + warnings + type classification) | v0.3 M1 | Web Card Detail |
| Wiki Quality (coverage/staleness/faithfulness) | v0.3 M2 | Web Wiki |
| Related Cards (6 种确定性关系类型) | v0.3 M3 | Web Card Detail |
| Source Location / Provenance (5 source_type formats) | v0.3 M4 | Web Card Detail |
| Knowledge Health (maintenance report) | v0.3 M5 | Web Health Report |
| Local Graph Preview (1-hop card-centered) | v0.3 M6 | Web Card Detail |
| Web UX Polish (i18n, setup, dashboard guidance) | v0.3 H | Web UI |
| Knowledge Relationship Experience (wiki sections, panel, provenance) | v0.4 U1-U6 | Web UI |
| Dogfood Readiness (runbook + fake dogfood + safety hardening) | v0.5 U1-U6 | Scripts + Web UI |
| Knowledge Graph & Retrieval Foundation (GraphPort + Builder + API) | v0.6 R1-R6 | Backend + Web API |
| Graph Quality & Evidence Hardening (evidence text + i18n + tests) | v0.7 U1-U5 | Backend + Web UI |
| RetrievalPort Abstraction + ADR | v0.8 U1+U3 | Backend + Docs |
| Graph Backend ADR (Kuzu deferred) | v0.9 U2 | Docs |

### 当前架构

```
Web UI (React + Vite + Tailwind)
  ├── Library (卡片浏览/详情/关系/图谱)
  ├── Wiki (章节阅读/引用导航)
  ├── Search (BM25 Recall)
  ├── Health Report (知识体检)
  ├── Setup (模型配置)
  ├── Sources (数据源管理)
  ├── Review (审批 ai_draft)
  └── Trash (回收站)
       │
       ▼
  FastAPI Web Server (mindforge_web)
       │
       ▼
  Service Layer
  ├── recall_service (BM25 via RetrievalPort)
  ├── relations/ (GraphPort → GraphBuilder → Graph API)
  ├── health/ (Knowledge Health)
  ├── quality/ (Card + Wiki Quality)
  └── wiki_service (Wiki synthesis + related sections)
```

## 1. v1.0 设计问题

v1.0 的定位是"Knowledge Workbench Experience"，但已有功能已经覆盖了 roadmap §4.5 的大部分 W1-W7 单元。核心问题是：**v1.0 真正要交付的是什么？**

### 1.1 不是继续堆功能

v0.1-v0.9 已经交付了完整的功能链：ingestion → processing → approve → library → wiki → search → graph → health。再加新功能边际收益递减。

### 1.2 v1.0 的真正价值

v1.0 应该做的是**体验整合和打磨**，让已存在的功能成为一个连贯的知识工作台：

1. **导航连贯性** — 用户能在 Card → Related Cards → Wiki Section → Source → Card 之间无缝导航，不迷路
2. **空状态引导** — 每个页面在无数据时有清晰的引导文案和下一步行动
3. **状态可见性** — ai_draft → human_approved 的生命周期对用户可见
4. **知识全景** — 用户能一眼看到知识库的整体状态（多少个 cards、覆盖哪些 topic、哪些需要关注）
5. **工作流导向** — 从 "我该做什么" 出发组织 UI，而不是从 "系统有什么功能" 出发

## 2. 推荐 v1.0 Scope

### P0: 导航连贯性 & 工作台首页

**现状**: Home 页面是 NextAction 列表，功能导向但不连贯。

**改动**:
- Home 页升级为真正的 Workbench Dashboard — 展示知识全景（卡片数、Wiki sections、待审核、健康状态）
- 统一导航面包屑 — 从任意页面能追溯到 Home
- Card → Related → Wiki → Source 的导航链路可逆（backlinks everywhere）

**涉及文件**: `web/src/pages/HomePage.tsx`, `web/src/components/`, `web/src/lib/i18n.ts`

### P1: 审核-批准可视化时间线

**现状**: ai_draft → human_approved 状态转换在 card detail 中展示，但没有时间线视图。

**改动**:
- Card detail 新增 Approval Timeline 组件 — 展示创建时间、审批时间、修改历史
- Review 页面新增批量浏览视图 — 一次看多张 ai_draft 的摘要，快速决定 approve/reject

**涉及文件**: `web/src/pages/ReviewPage.tsx`, `web/src/components/`, `src/mindforge_web/routers/approval.py`

### P1: 知识质量仪表盘

**现状**: Card Quality 和 Wiki Quality 在 card/wiki detail 中展示，Health Report 是独立页面。

**改动**:
- Home Dashboard 集成 quality overview（低质量卡片数、stale wiki sections、未关联卡片）
- 从 dashboard 一键跳转到需要关注的卡片/wiki

**涉及文件**: `web/src/pages/HomePage.tsx`, `web/src/pages/HealthReportPage.tsx`

### P2: 安全导出

**现状**: 无导出功能。

**改动**:
- Library 页面新增 Export 按钮 — 导出选中卡片为 Markdown
- 导出内容不含 API key、secrets、source raw_text、Human Note（安全白名单）

**涉及文件**: `src/mindforge_web/routers/library.py` (或新增 export router), `web/src/pages/LibraryPage.tsx`

### P2: Dogfood Workspace 一键启动

**现状**: `scripts/fake_dogfood.sh` 可用但需要手动执行。

**改动**:
- 新增 `just dogfood` 或 `make dogfood` 一键命令
- Web Setup 页面新增 "Try with Sample Data" 按钮（可选）

**涉及文件**: `scripts/`, `web/src/pages/SetupPage.tsx`

### Non-Goals

- 不做 force-directed graph canvas (d3/cytoscape)
- 不做 RAG/embedding/vector DB
- 不做自动审批
- 不做移动端
- 不做实时协作
- 不做新依赖引入

## 3. 推荐实施策略

### 按价值依次交付（2-3 个 iteration）

| Iteration | Units | 价值 |
|-----------|-------|------|
| I1: Workbench Dashboard | P0 导航连贯性 + P1 质量仪表盘 | 用户打开 MindForge 就看到知识全景 |
| I2: Approval Visibility | P1 审批时间线 | 知识生命周期可视化 |
| I3: Export + Dogfood | P2 导出 + P2 一键 dogfood | 知识可带走，新人可试用 |

### 每个 iteration 自包含

每个 iteration 独立可测试、可 dogfood、可 merge。不搞大爆炸式 v1.0 release。

## 4. 推荐下一步

编写 v1.0 I1 Workbench Dashboard 详细 SPEC → 自审 → 实现。

I1 是 v1.0 的锚点改动：把 Home 页从 NextAction 列表升级为知识全景仪表盘。
这不涉及新后端能力，主要是前端整合和 UX 优化。
