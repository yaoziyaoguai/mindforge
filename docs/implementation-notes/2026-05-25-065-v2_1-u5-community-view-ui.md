---
title: "v2.1 U5 Community View UI Enhancement — Implementation Note"
date: 2026-05-25
status: Complete
version: v2.1
---

# v2.1 U5 Community View UI Enhancement — Implementation Note

## What was done

v2.1 U5 增强了 KnowledgeCommunityPanel 和 GraphNavigationPanel 的社区可视化能力。

### KnowledgeCommunityPanel 增强

1. **子社区展开/折叠** — 每个带有 `sub_communities` 的社区条目显示展开箭头，展开后显示嵌套的子社区列表（可点击导航）
2. **社区重叠可视化** — `overlap_with` 数据在展开面板中以"交叉"标签展示，显示共享成员数
3. **质量评分指示器** — 每个社区条目旁显示彩色圆点：emerald ≥0.7 / amber 0.4-0.7 / gray <0.4
4. **展开全部/收起** — "更多"按钮变为 toggle，支持展开/收起超过 5 条的内容

### GraphNavigationPanel 增强

1. **社区分组模式** — 新增切换按钮：按关系类型分组 / 按社区分组
2. **社区颜色编码** — 按社区类型使用不同颜色：
   - 来源社区: emerald
   - 标签社区: amber
   - Wiki 章节社区: violet
3. **社区卡片展示** — 社区组显示共享实体名、匹配数/总成员数、质量评分
4. **并行数据加载** — `Promise.all` 同时加载图数据和社区数据
5. **NeighborCardButton 复用** — 提取公共卡片按钮组件

### i18n

新增 6 个社区相关 locale key（中/英）：
sub_communities, overlap_with, quality_score, expand_all, collapse_all, shared_members

## Changes

- `web/src/components/KnowledgeCommunityPanel.tsx` — 重写：子社区展开、重叠可视化、质量评分
- `web/src/components/GraphNavigationPanel.tsx` — 重写：社区分组模式、颜色编码、组件提取
- `web/src/lib/i18n.ts` — +12 locale keys (6 zh + 6 en)

## Design Rationale

- **纯确定性数据展示**：所有社区信息来自 deterministic community detection，不调用 LLM
- **渐进增强**：默认视图保持简洁，详细信息通过展开/折叠按需展示
- **颜色编码一致**：GraphNavigationPanel 和 KnowledgeCommunityPanel 使用相同的社区类型颜色映射
- **组件复用**：NeighborCardButton 提取为独立组件，减少重复

## Non-goals

- 不做社区实时编辑
- 不做 LLM 生成的社区描述
- 不做社区成员列表的完整分页
- 不做社区搜索/过滤

## Gates

- ruff check: exit 0
- pytest full (~420+): exit 0, 100% pass
- npm build: exit 0
- product copy: exit 0
- git diff --check: exit 0
