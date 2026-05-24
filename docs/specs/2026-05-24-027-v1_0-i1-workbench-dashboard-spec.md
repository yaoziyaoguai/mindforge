---
title: v1.0 I1 Workbench Dashboard SPEC
type: spec
status: draft
date: 2026-05-24
parent: 2026-05-24-005-v1_0-next-phase-planning-review.md
---

# v1.0 I1: Workbench Dashboard — 从功能列表到知识全景

## 0. 目标

把 Home 页从 NextAction 列表升级为知识工作台仪表盘，让用户打开 MindForge 就能看到知识库的全景状态和需要关注的事项。

## 1. Problem Frame

**现状**: Home 页（`HomePage.tsx`）主要是 NextAction 列表（"Search knowledge"、"Check Setup"），功能导向但缺乏知识全景感知。

**用户痛点**:
- 打开 MindForge 不知道知识库"现在什么样"
- 不知道有多少卡片、覆盖哪些主题、有什么需要关注
- 各页面之间导航断裂，没有统一的面包屑

**目标**: Home 页升级为 Dashboard，一眼看到知识全景，一键跳到需要关注的地方。

## 2. Scope

### U1: Knowledge Overview Cards

**Goal**: Dashboard 顶部展示 4 张概览卡片，每张显示关键数字和状态。

**卡片**:

| 卡片 | 数据来源 | 点击跳转 |
|------|---------|---------|
| Approved Knowledge | approved cards 数量 + 环比变化 | Library |
| Wiki Sections | wiki section 数量 + stale 标记 | Wiki |
| Pending Review | ai_draft 数量 | Review Drafts |
| Health Status | health score/level + 需要关注项数 | Health Report |

**状态指示**:
- OK (绿色) — 一切正常
- Warning (黄色) — 有需要注意的项目
- Action Needed (红色) — 有阻塞性问题

**UI 要求**:
- 4 张卡片水平排列（移动端垂直堆叠）
- 每张卡片显示：图标 + 数字 + 标签 + 状态指示器
- 整张卡片可点击，跳转到对应页面

### U2: Attention Feed

**Goal**: Dashboard 中部展示"需要关注"的动态列表。

**内容**（按优先级排列）:
1. 待审批卡片 > 3 天未处理 — 高优先级
2. Stale wiki sections — 中优先级
3. 低质量卡片（quality_score < 50）— 中优先级
4. 未关联卡片（无 related cards + 无 wiki reference）— 低优先级
5. 索引需要重建 — 信息提示

**UI 要求**:
- 按优先级分组（High / Medium / Low / Info）
- 每项显示：问题描述 + 受影响数量 + "查看"按钮
- 空状态："知识库状态良好，暂无需要关注的事项。"

### U3: Quick Actions Bar

**Goal**: Dashboard 底部保留关键操作的快捷入口。

**按钮**:
- "浏览知识库" → Library
- "导入新资料" → Sources
- "搜索知识" → Search

比现状的 NextAction 列表更紧凑，作为辅助入口而非主视觉焦点。

### U4: Unified Breadcrumb

**Goal**: 所有页面添加面包屑导航，从任意页面能追溯回 Home。

**面包屑示例**:
- `Home > Library > Card Title`
- `Home > Wiki > Section Name`
- `Home > Search > Results`

**技术方案**:
- 新增 `<Breadcrumb>` 组件
- 使用 React Router 的 `useLocation` 自动生成面包屑
- 面包屑配置集中在 `breadcrumb.ts` 映射表

## 3. Non-Goals

- 不修改后端 API（所有数据来自已有 endpoint）
- 不新增图表库（纯 Tailwind 样式卡片）
- 不新增 i18n key 超过 15 个
- 不改变现有页面的主要布局
- 不做实时数据推送（数据在页面加载时获取）

## 4. Implementation Units 汇总

| Unit | 描述 | 文件 | 测试 |
|------|------|------|------|
| U1 | Knowledge Overview Cards | `HomePage.tsx` 重构 | product copy test |
| U2 | Attention Feed | `HomePage.tsx` 重构 | product copy test |
| U3 | Quick Actions Bar | `HomePage.tsx` 重构 | product copy test |
| U4 | Unified Breadcrumb | `Breadcrumb.tsx` (NEW) + 各页面 | product copy test |

## 5. Test Plan

| 测试类型 | 用例 |
|----------|------|
| `npm run build` | TypeScript 编译通过 |
| `test_web_product_copy.py` | 新 i18n key 有 zh/en 双值，无硬编码文案 |
| Browser smoke | Dashboard 正确显示卡片数量/状态，点击跳转正确，面包屑导航正确 |

## 6. API 依赖

所有数据来自已有 endpoint，不需要新 API：

| 数据 | Endpoint | 现状 |
|------|---------|------|
| Approved cards | `/api/library/cards` | 已有 |
| Pending drafts | `/api/workflow/summary` | 已有 |
| Wiki sections | `/api/wiki/page` | 已有 |
| Health status | `/api/health/report` | 已有 |
| Home status | `/api/home/status` | 已有（当前 HomePage 已使用） |

## 7. 依赖

- v0.7 graph quality hardening (done)
- v0.8 retrieval port (done)
- 无新后端依赖

## 8. Self-Review Checklist

- [ ] 是否退化成普通搜索页？ — 否。Dashboard 是知识全景，不是搜索框
- [ ] 是否偷偷变成 RAG answering？ — 否。纯数据展示
- [ ] 是否需要新依赖？ — 否。纯 Tailwind 样式
- [ ] 是否破坏 ai_draft / human_approved 语义？ — 否
- [ ] 是否需要真实 LLM？ — 否
- [ ] 是否改动后端？ — 否
