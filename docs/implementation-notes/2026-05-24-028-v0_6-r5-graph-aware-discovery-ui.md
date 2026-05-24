# v0.6 R5 Graph-aware Discovery UI 实现笔记

## 日期
2026-05-24

## 目标
前端从 card-first 升级为 graph-first discovery。新增 GraphNavigationPanel、GraphExplorer 组件，集成到 Library 和 CardWorkspace。

## 实现方案

### 新增文件

- `web/src/api/graph.ts` — Graph API 客户端（fetchGraphNode, fetchGraphExplore, fetchGraphEdge）
- `web/src/components/GraphNavigationPanel.tsx` — 图导航面板，替代/增强 RelatedCardsPanel
- `web/src/components/GraphExplorer.tsx` — 图浏览器入口组件

### 修改文件

- `web/src/api/types.ts` — 新增 GraphNodeType, GraphEdgeType, RelationEvidenceResponse, GraphNodeResponse, GraphEdgeResponse, GraphResponse, GraphEdgeDetailResponse 类型
- `web/src/lib/i18n.ts` — 新增 20 个 graph 相关 i18n key（zh/en 双语）
- `web/src/components/CardWorkspace.tsx` — 引入 GraphNavigationPanel，在卡片详情中展示图关系
- `web/src/pages/LibraryPage.tsx` — 引入 GraphExplorer，在卡片列表上方提供图浏览入口

### 组件设计

**GraphNavigationPanel**
- 调用 `/api/graph/node` 获取图数据
- 按 EdgeType 分组展示关系（related_by_source → shares_tag → related_by_wiki_section → ...）
- 每组可折叠，显示关系卡片和 evidence
- 每条关系显示 evidence text + strength indicator（颜色编码：≥0.8 绿色，≥0.5 黄色，<0.5 灰色）
- 支持 1-hop / 2-hop 切换按钮
- Loading/error/empty 状态完整覆盖
- 保持现有 LocalGraphPreview 和 RelatedCardsPanel 不变（向后兼容）

**GraphExplorer**
- Library 页面顶部的图浏览入口
- 支持 source / tag / wiki_section 三种节点类型的图探索
- 搜索式输入 + 结果展示
- 结果以卡片列表 + 边标签形式展示

### 设计决策

1. **不删除旧组件** — LocalGraphPreview 和 RelatedCardsPanel 保留，GraphNavigationPanel 作为新增的增强视图。避免破坏现有用户流程。
2. **GraphNavigationPanel 独立加载** — 不依赖 LibraryCardDetail 的 inline 数据，自行调用 `/api/graph/node`。这允许更丰富的 2-hop 图数据和 evidence 展示。
3. **i18n 覆盖** — 所有 graph UI 文案均 zh/en 双语。

### 已知限制

- GraphNavigationPanel 和旧的 RelatedCardsPanel 同时显示可能导致信息重复。后续可择一保留。
- 2-hop 展开在卡片数较多时可能产生大量 DOM 节点，后续可考虑虚拟滚动。
- GraphExplorer 需要用户手动输入 node_id，尚未提供自动补全。

## Gate

| Gate | 命令 | Exit Code |
|------|------|-----------|
| ruff check | `ruff check src/mindforge_web/ tests/relations/ --select F,E --quiet` | 0 (pre-existing E501 only) |
| pytest (relations) | `python -m pytest tests/relations/ -q --tb=short` | 0 (74 passed) |
| pytest (full) | `python -m pytest tests/ -q --tb=short -k "not test_sources_page_uses_source_path_view"` | 0 |
| pytest (product copy) | `python -m pytest tests/test_web_product_copy.py -q` | 0 |
| npm build | `npm --prefix web run build` | 0 |
| git diff --check | `git diff --check` | 0 |
