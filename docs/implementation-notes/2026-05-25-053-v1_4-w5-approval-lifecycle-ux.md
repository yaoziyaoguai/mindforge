# v1.4 W5: Approval Lifecycle UX 增强 — Implementation Note

**Date:** 2025-05-25
**Status:** Complete

## What was done

增强 `ApprovalTimeline` 组件，添加审批状态面板、阶段耗时标签和面板式视觉设计。

## Changes

### ApprovalTimeline.tsx — 全面增强
- **Panel 设计**: 统一使用 W1 建立的 `rounded-lg border` + `bg-stone-50/50 header` 视觉风格
- **状态徽章**: Header 右侧显示审批状态 badge（绿色已确认 / 琥珀色等待中）
- **状态描述**: 中文 "此卡片已通过人工审批" / "此卡片等待人工审批确认"
- **阶段耗时**: 创建→审批和审批→修改之间显示耗时（如 "耗时: 3天 12小时"）
- **`durationBetween()`**: 计算两个 ISO 时间戳之间的时间差，输出人次可读的格式
- **`GitCommit` 图标**: Header 使用版本控制图标暗示审批记录的可追溯性

### i18n
- 新增 9 个 zh + 9 个 en keys:
  - `timeline.title`, `timeline.approved_status`, `timeline.pending_status`
  - `timeline.took`
  - `timeline.duration_days_hours`, `timeline.duration_days`, `timeline.duration_hours`, `timeline.duration_minutes`

## Design rationale

- **Duration visibility**: 用户能直观看到卡片从创建到审批花费了多长时间，帮助评估审批流程效率
- **Panel consistency**: 与 GraphNavigationPanel (W1)、ProvenanceTrail (W3) 使用相同的视觉语言
- **No diff view**: 当前未存储 body 修改历史，不做 diff 视图（roadmap 提及但数据结构不支持）

## Non-goals

- 不做 body diff 视图（需要修改历史存储 — 超出范围）
- 不做审批者信息（不记录谁审批的）
- 不做审批评论

## Gates

- npm build: exit 0
- ruff check: All checks passed
- pytest: exit 0, 100% pass
- git diff --check: clean
