# v1.4 W3: Source Provenance Trail UX — Implementation Note

**Date:** 2025-05-25
**Status:** Complete

## What was done

将 ProvenanceTrail 从 CardWorkspace.tsx 的内联函数提取为独立组件 `web/src/components/ProvenanceTrail.tsx`，并重新设计为垂直时间线（timeline）视觉模式。

## Changes

### ProvenanceTrail.tsx (NEW)
- **独立组件**: 从 CardWorkspace 提取，使用 `useLocale()` hook，接口简化为 `{ trail, onSelectCard }`
- **垂直时间线设计**: 每个溯源步骤用圆形图标节点 + 连接线展示，清晰表达 "来源 → 同源卡片 → Wiki章节 → 关联来源" 的知识流
- **TrailStep 子组件**: 统一的时间线节点样式，可配置图标、标签、内容，支持 `muted` 模式（非活跃步骤）
- **交互式导航**: 同源卡片可点击跳转（带 `ArrowRight` 图标提示）
- **关联来源富展示**: shared_tags（`#tag` 格式）和 shared_wiki_sections
- **Panel 设计**: 与 W1 的 GraphNavigationPanel 保持一致的独立 panel 视觉（rounded border + header bar）
- **空状态处理**: 无溯源数据时返回 null（不渲染）

### CardWorkspace.tsx
- 移除内联 `ProvenanceTrail` 函数（-86 行）
- 导入新的独立 `ProvenanceTrail` 组件
- 简化调用：`<ProvenanceTrail trail={trail} onSelectCard={onSelectCard} />`（移除 `t` prop 和重复的条件判断）

### i18n.ts
- 新增 `card.provenance_trail_desc` (zh + en)

## Design rationale

- **Timeline over flat pills**: 旧版用 `→` 连接的横向 pill 难以区分步骤层级，垂直时间线更直观地展示溯源链路的层次结构
- **独立组件**: 内联 86 行函数在 CardWorkspace 中增加认知负担，独立组件更易于维护和测试
- **Consistent panel style**: 与 GraphNavigationPanel 使用相同的 `border rounded-lg bg-panel` + `bg-stone-50/50 header` 视觉语言

## Non-goals

- 不做 source document 点击跳转（当前无 source detail 页面）
- 不做 wiki section 点击过滤

## Gates

- npm build: exit 0
- ruff check: All checks passed
- pytest: exit 0, 100% pass
- git diff --check: clean
