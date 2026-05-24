---
title: v1.0 I2 Approval Visibility SPEC
type: spec
status: draft
date: 2026-05-24
parent: 2026-05-24-005-v1_0-next-phase-planning-review.md
---

# v1.0 I2: Approval Visibility — 知识生命周期可视化

## 0. 目标

让用户看到每张知识卡片从 ai_draft 到 human_approved 的生命历程，并在审阅页面支持快速浏览和决策。

## 1. Problem Frame

**现状**: 
- Card detail 展示 `created_at`、`approved_at` 等时间戳，但分散在"来源与历史"折叠区
- Review 页面一次只能展开一张 draft 详情，无法快速浏览多张草稿

**用户痛点**:
- 不知道卡片什么时候创建的、什么时候审批的、有没有被修改过
- 审阅多张草稿时需要在卡片之间反复切换，效率低
- 知识溯源时缺少时间维度的上下文

**目标**: 
- Card/Draft detail 页面新增可视化审批时间线
- Review 页面支持列表内快速预览草稿内容，加速审批决策

## 2. Scope

### U1: Approval Timeline 组件

**Goal**: Card detail 和 Draft detail 页面展示卡片生命周期时间线。

**时间线节点**（按时间顺序）:
1. 创建 (created_at) — 草稿生成时间
2. 审批 (approved_at) — 人工确认时间（仅 human_approved 卡片有）
3. 修改 (updated_at) — 最近一次修改时间（如果有修改）

**UI 要求**:
- 垂直时间线，每个节点以圆点 + 竖线连接
- 节点显示：图标 + 事件描述 + 时间戳（相对时间 + 绝对时间）
- 放置在 CardWorkspace 的"来源与历史"折叠区中，取代原有的裸时间戳展示
- Draft 未审批时时间线在"审批"节点处显示虚线（待定状态）

**涉及文件**: `web/src/components/CardWorkspace.tsx`（新增内联 Timeline），或新建 `ApprovalTimeline.tsx`

### U2: Draft Quick Preview（Review 列表增强）

**Goal**: Review 页面在 draft 列表中展示每条 draft 的内容摘要，无需点开详情即可快速判断。

**改动**:
- DraftList 每条草稿新增"展开预览"按钮
- 展开后内联显示：body 前 300 字摘要 + 价值评分 + 标签信息
- 展开/收起动画平滑过渡
- 不替换现有的 DraftViewer 详情视图（详情仍通过点击卡片进入）

**涉及文件**: `web/src/components/DraftList.tsx`

### U3: Lifecycle Status Badge 增强

**Goal**: 统一卡片和草稿的状态徽章设计，视觉上区分生命周期阶段。

**改动**:
- `ai_draft` 徽章增加"待确认"图标 + 橙色色调
- `human_approved` 徽章增加"已确认"图标 + 绿色色调
- 所有状态徽章统一使用相同的视觉语言（已在 StatusCard 中使用）

**涉及文件**: `web/src/lib/utils.ts`（friendlyStatus 增强）, `web/src/components/StatusCard.tsx`

## 3. Non-Goals

- 不新增后端 API（所有数据来自已有 endpoint 的已有字段）
- 不做审批历史版本对比
- 不做撤销审批功能
- 不修改审批安全语义
- 不新增依赖

## 4. Implementation Units 汇总

| Unit | 描述 | 文件 | 新增/修改 |
|------|------|------|----------|
| U1 | Approval Timeline | `ApprovalTimeline.tsx` (NEW) + CardWorkspace | 新增组件 |
| U2 | Draft Quick Preview | `DraftList.tsx` | 修改现有组件 |
| U3 | Lifecycle Status Badge | `utils.ts` + StatusCard | 增强现有函数 |

## 5. Test Plan

| 测试类型 | 用例 |
|----------|------|
| `npm run build` | TypeScript 编译通过 |
| `test_web_product_copy.py` | 新 i18n key 有 zh/en 双值 |
| Browser smoke | Timeline 在 draft/library 详情中正确展示，Quick preview 展开/收起正常 |

## 6. i18n Keys（预计 ≤ 10 个）

- `timeline.created` — "创建" / "Created"
- `timeline.approved` — "已确认" / "Approved"
- `timeline.pending_approval` — "等待确认" / "Awaiting Approval"
- `timeline.modified` — "已修改" / "Modified"
- `timeline.relative_just_now` — "刚刚" / "just now"
- `drafts.preview_expand` — "展开预览" / "Expand Preview"
- `drafts.preview_collapse` — "收起预览" / "Collapse Preview"

## 7. 依赖

- v1.0 I1 Workbench Dashboard (done)
- 现有 CardWorkspace + DraftList 组件
- 无新后端依赖

## 8. Self-Review Checklist

- [ ] 是否退化成普通搜索页？— 否。Timeline 是生命周期可视化
- [ ] 是否偷偷变成 RAG answering？— 否
- [ ] 是否需要新依赖？— 否
- [ ] 是否破坏 ai_draft / human_approved 语义？— 否。仅展示已有状态
- [ ] 是否改动后端？— 否。所有数据来自已有字段
- [ ] 是否符合 plan 中的 I2 方向？— 是。Approval Timeline + Batch Review
