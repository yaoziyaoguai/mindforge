# v0.6 R3 Deterministic Graph Builder 实现笔记

## 日期
2026-05-24

## 目标
将现有关系计算引擎统一为 GraphPort + GraphBuilder abstraction，支持 2-hop graph 和带 evidence 的可解释边。

## 实现方案

### 新增文件

**`src/mindforge/relations/graph_models.py`** — 统一图数据模型
- `NodeType`: CARD / SOURCE / WIKI_SECTION / TAG / CONCEPT
- `EdgeType`: 9 种边类型（DERIVED_FROM, SHARES_TAG, RELATED_BY_SOURCE, 等）
- `RelationEvidence`: frozen dataclass (reason, evidence, strength, detail) — 每条边可解释
- `GraphNode`, `GraphEdge`, `Graph` — frozen dataclass，不可变

**`src/mindforge/relations/graph_port.py`** — 抽象接口
- `GraphPort` ABC: get_node(), get_edges(), get_graph(), get_path()
- 实现方: DeterministicGraphBuilder (default), 未来 Kuzu/SQLite backend

**`src/mindforge/relations/graph_builder.py`** — 确定性图构建器
- `DeterministicGraphBuilder(GraphPort)` — 默认实现
- `get_graph(center_id, center_type, depth=1|2)` — 从任意 NodeType 构建图
- 复用 `compute_related_cards()` + `build_card_centered_graph()` + `build_wiki_section_centered_graph()`
- 2-hop graph: 对每个 1-hop 邻居卡片展开其关系并 merge
- `RelationReason → EdgeType` 映射: SAME_SOURCE→RELATED_BY_SOURCE, SAME_TAG→SHARES_TAG, 等
- `get_path(source, target, max_depth)` — BFS 最短路径查找
- 预建索引: source_index, tag_index, section_index (与 compute_related_cards 共享逻辑)

### 设计决策

1. **不替换现有引擎** — `compute_related_cards()` 和 `build_card_centered_graph()` 保持不变。GraphBuilder 是上层封装，复用而非替换。
2. **GraphNode/GraphEdge 是新的 frozen dataclass** — 不修改现有 `local_graph.GraphNode`/`local_graph.GraphEdge`，保持向后兼容。
3. **RelationEvidence 必须携带 reason + evidence** — 每个 edge 都可解释为什么两节点相关。
4. **CONCEPT NodeType 预留但未实现** — get_node(CONCEPT) 返回 None，待后续 unit 实现确定性术语提取。

### 已知限制

- 2-hop graph 的边合并逻辑较简单（直接 append），可能产生重复边。后续可优化去重。
- get_path() 只返回最短路径（BFS first-match），不返回所有路径。
- Concept 节点类型尚未实现确定性术语提取（可能是 R6 或后续 unit 的工作）。
- 性能：100-card 2-hop graph 构建 < 1s，1000-card 场景待验证。

## Gate

| Gate | 命令 | Exit Code |
|------|------|-----------|
| ruff check (new files) | `ruff check src/mindforge/relations/graph_*.py tests/relations/test_graph_*.py --select F,E --quiet` | 0 |
| pytest (all relations) | `python -m pytest tests/relations/ -q --tb=short` | 0 (64 passed) |
| pytest (full excl pre-existing) | `python -m pytest tests/ -q --tb=short -k "not test_sources_page_uses_source_path_view"` | 0 |
| npm build | `npm --prefix web run build` | 0 |
| git diff --check | `git diff --check` | 0 |
