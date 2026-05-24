# v1.4 W1: Relationship Map UX 升级 — Implementation Note

**Date:** 2025-05-25
**Status:** Complete

## What was done

将 `GraphNavigationPanel` 从 CardWorkspace 底部的辅助区域提升为主导航位置，并重新设计 UI 以达到 "primary navigation" 的视觉层级。

## Changes

### GraphNavigationPanel.tsx — 全面视觉升级
- **独立 panel 设计**: 不在嵌入 `border-t` 内联 section，改为独立的 `rounded-lg border` panel，视觉上与其他内容区区分
- **Header 摘要栏**: 浅灰背景 header 区域，显示关系图标徽章、相邻卡片数量、关系连线总数
- **类型分布 chips**: 在 header 展示前 3 种关系类型的分布（如 `同源·3 同标签·2 同 Wiki 章节·1`）及 `+N` 溢出提示
- **2 列网格布局**: 相关卡片从水平滚动改为 `grid sm:grid-cols-2`，每条 evidence 文本行高限制为 2 行
- **左侧 accent 色条**: 每种关系类型使用独特的左边框颜色（绿色=同源、蓝色=Wiki章节、琥珀色=同标签 等）
- **Strength 指示**: 每条卡片底部显示颜色圆点 + 百分比强度
- **自动展开前 4 组**（从 3 提升）
- **深度切换按钮**: 增加 `Layers` 图标，使用 outline 样式

### CardWorkspace.tsx — 位置提升
- `GraphNavigationPanel` 从 `ProvenanceTrail → LocalGraphPreview → GraphNavigationPanel` 的最后一位置
- 移至 `SummaryPanel` 之后、`QualityPanel` 之前的第一探索位置
- 包裹在 `px-5 pt-5` 中以匹配 CardWorkspace 内边距

## Design rationale

- **Graph-first navigation**: 用户打开卡片后，关系地图应排在质量面板之前 — 浏览关联知识比检查质量分数更日常
- **视觉层级**: 独立的 rounded panel + header bar 使关系地图看起来像一个"功能模块"而非一个"附加 section"
- **Grid over scroll**: 2 列网格更适合阅读，水平滚动适合移动端但桌面端网格更高效

## Non-goals

- 不做 force-directed graph canvas（roadmap 明确排除）
- 不做 real-time graph updates
- 不改动 API 层

## Gates

- npm build: exit 0
- ruff check: All checks passed
- pytest: exit 0, 100% pass
- git diff --check: clean
