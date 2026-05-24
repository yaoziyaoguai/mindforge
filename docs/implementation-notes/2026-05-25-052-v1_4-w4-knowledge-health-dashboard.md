# v1.4 W4: Knowledge Health Dashboard — Implementation Note

**Date:** 2025-05-25
**Status:** Complete

## What was done

创建 `HealthStatusBar` 组件，将健康检查从独立 `/health` 页面"前台化"到 LibraryPage 主工作区，使用户在浏览知识库时就能看到健康状态。

## Changes

### HealthStatusBar.tsx (NEW)
- **三种状态**: loading（旋转图标）、all clear（绿色勾）、有 issue（红色/琥珀色/蓝色严重度分布）
- **严重度分布**: 在摘要行直接显示 critical/warn/info 计数及图标
- **问题预览 chips**: 前 2 个 issue 以彩色圆角标签展示，其余显示 `+N more`
- **"查看详情" 按钮**: 跳转到 `/health` 完整报告页
- **响应式布局**: 移动端垂直排列，桌面端水平排列

### LibraryPage.tsx
- 在 stats cards 和 GraphExplorer 之间插入 `HealthStatusBar`

### i18n
- 新增 `health.checking`, `health.view_details` (zh + en)

## Design rationale

- **Inline over standalone**: HealthPage 已存在，但用户不会主动访问。将健康状态嵌入 LibraryPage 主视图，使问题"被动发现"变为"主动可见"
- **Severity-first**: 严重度分布比 issue 数量更能帮助用户快速判断是否需要立即处理
- **Non-blocking**: 加载失败时静默返回 null，不打断 LibraryPage 主流程

## Non-goals

- 不改动 HealthPage 本身（已功能完整）
- 不做健康历史趋势（无历史数据存储）
- 不做定时健康检查（后台脚本属 v1.5 范围）

## Gates

- npm build: exit 0
- ruff check: All checks passed
- pytest: exit 0, 100% pass
- git diff --check: clean
