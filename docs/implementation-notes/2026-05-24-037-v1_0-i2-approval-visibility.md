# v1.0 I2 Approval Visibility — Implementation Notes

## 变更概要

实现知识生命周期可视化：Approval Timeline 组件、Draft Quick Preview、Lifecycle Status Badge 增强。

## 实现决策

### U1: Approval Timeline
- 新建 `ApprovalTimeline.tsx`，垂直时间线展示 created → approved → modified 三个节点
- 未审批卡片在"审批"节点显示虚线 + Clock 图标（待定状态）
- 相对时间通过 i18n key 展示（`timeline.relative_*`），使用 `{n}` 占位符替换数值
- 集成到 CardWorkspace 的"来源与历史"区域，位于 path action 消息和 metadata dl 之间
- 仅当 `updated_at !== created_at` 时才显示"已修改"节点

### U2: Draft Quick Preview
- DraftList 每条草稿底部新增展开/收起按钮
- 展开时通过 `getDraftDetail(id)` 获取 body（使用已有 API，无新增后端）
- 展示 body 前 300 字符 + value_score + tags
- 使用 `ChevronDown`/`ChevronUp` 图标指示展开状态
- 展开/收起通过 `expandedId` state 管理，同一时间仅展开一个预览

### U3: Lifecycle Status Badge
- 新增 `cardStatusBadgeClass()` 函数：`human_approved` → 绿色调，`ai_draft` → 橙色调
- DraftList 状态徽章从硬编码 `text-warn` 改为使用 `cardStatusBadgeClass` + `statusIcon`
- CardWorkspace 已有正确差异化，未改动

### i18n
- 新增 10 个 key：timeline.* (8) + drafts.preview_* (2)
- 相对时间使用 `{n}` 占位符 + `.replace("{n}", String(n))` 模式

## Gate 结果

| Gate | Exit Code | 备注 |
|------|-----------|------|
| `npm --prefix web run build` | 0 | |
| `python -m pytest tests/test_web_product_copy.py -q` | 0 | 新增 5 个测试 |
| `python -m pytest tests/ -q` | 1 (1 pre-existing) | `test_sources_page_uses_source_path_view` 已知失败 |
| `git diff --check` | 0 | |

## Browser Smoke

- App shell + sidebar + breadcrumb 正常渲染
- 无前端 JS console error（仅 API 404/500 — 后端未运行）
- 时间线和草稿预览在无后端数据的情况下无法完整验证，但组件结构和 i18n 集成已由 product copy tests 覆盖

## 已知限制

- 时间线在 draft 和 library 两种模式下均使用相同字段名（`created_at`/`approved_at`/`updated_at`），但通过 `"approved_at" in card` 做类型收窄
- Draft Quick Preview 每次展开都会重新 fetch body（不缓存），后续可考虑缓存策略
- 无后端运行时无法完整验证时间线和预览的渲染效果
