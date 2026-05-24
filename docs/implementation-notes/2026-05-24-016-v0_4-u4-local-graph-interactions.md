# v0.4 U4 Local Graph Lite 交互增强 实现笔记

## 日期
2026-05-24

## 目标
增强 LocalGraphPreview 组件的节点交互：hover tooltip、section 节点卡片数 badge、客户端导航。

## 实现方案

### Backend（轻量扩展）

**Schema**（`schemas.py`）：
- `LocalGraphNodeResponse` 新增 `card_count: int | None = None` 字段
- 仅 wiki_section 类型节点返回 card_count

**Service**（`web_facade.py`）：
- `_local_graph_response()` 中从 edges 计算 section 的 card_count
- `same_wiki_section` edge target_id = section node id → 计数即引用卡片数
- 需要导入 `NodeType` 枚举

### Frontend

**TypeScript 类型**（`types.ts`）：
- `LocalGraphNodeResponse.card_count?: number | null`

**i18n**：
- `wiki.local_graph_section_cards`: "{count} 张卡片" / "{count} cards"

**LocalGraphPreview 组件**：
- 接受 `onSelectCard?: (ref: string) => void` prop
- 所有节点添加 `title={node.label}` hover tooltip
- Related card 节点添加 `title` + `cursor-pointer` + onClick（阻止默认导航，调用 onSelectCard）
- 所有 graph 节点添加 `title` + `cursor-pointer`
- Card 类型节点点击时调用 `onSelectCard(node.id)`（SPA 导航）
- Section 类型节点保留 `<a href>` 导航至 Wiki 页面
- Section 节点显示 `card_count` badge（`bg-primary/10` 圆角标签）
- 保持纯 CSS/HTML 渲染，不引入 canvas/d3/cytoscape/vis-network

**CardWorkspace**：
- 传递 `onSelectCard` prop 至 `LocalGraphPreview`

## 关键设计决策

1. **card_count 后端计算**：从 edge 数据派生而非额外查询，保持 O(1) 复杂度
2. **客户端导航**：Card 节点 onClick 使用 SPA 导航（防止整页刷新），Section 节点保留原 href 行为
3. **不引入任何 graph 库**：坚持纯 CSS/HTML 1-hop 约束

## 已知限制

- card_count 仅在 `wiki_section` 类型节点有意义，其他类型返回 null
- hover tooltip 仅显示 label，不包含 quality/status 信息（保持轻量）

## 测试覆盖

- `tests/test_web_product_copy.py`: `test_local_graph_views_are_visible_list_fallbacks_without_graph_libraries` 通过
- 该测试验证：无 canvas/d3/cytoscape/vis-network/networkx 依赖
- Browser smoke: Local Graph Preview 正常渲染，节点有 title 属性，无 console error
