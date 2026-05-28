# ADR-007: Graph Backend Decision — v3.7-v4.0 Workload Validation

> **v4.2 truth reset 追记 (2026-05-25)**：本文档记录的"8 种 NodeType 全维度 workload"中，
> community / topic / entity / concept_candidate 4 种 NodeType 当前 backend 并未实现
> （`DeterministicGraphBuilder` 仅支持 card / source / tag / wiki_section）。
> Graph API 对这 4 种类型返回 422。ADR-007 的 In-Memory Graph Backend 决策本身仍然
> 有效，但 workload 验证范围的描述以 v4.2 实现状态为准。
> 以 v4.2 实现状态为准。

## 日期
2026-05-25

## 状态
Accepted — In-Memory Deterministic Graph 持续满足需求

## 前置 ADR

- ADR-002 (2026-05-24): Graph Backend — In-Memory vs Kuzu Embedded Graph DB
- ADR-004 (2026-05-25): Graph Query Capability Gap Analysis
- ADR-006 (2026-05-25): Graph Ontology v1

## 背景

v3.7-v4.1 Graph View Roadmap 中，v4.1 的明确目标是在完成 v3.7 graph ontology、
v3.8 graph view MVP、v3.9 entity resolution、v4.0 sensemaking workspace 之后，
**基于真实 query/view workload 数据**重新评估是否需要图数据库。

v3.7-v4.0 已实现的图查询 workload：

| 能力 | 版本 | 实现方式 | 典型数据量 |
|------|------|---------|-----------|
| 1-hop/2-hop subgraph | v3.7 | BFS + dict/set | ~50 nodes, ~100 edges |
| Multi-NodeType explore | v3.8 | BFS per NodeType (8 types) | ~30 nodes per explore |
| Entity resolution (ConceptCandidate) | v3.9 | regex + set intersection | ~200 candidates from 100 cards |
| Bridge node detection | v4.0 | Community intersection | ~10 bridges from 100 cards |
| Orphan island detection | v4.0 | Connected components (DFS) | ~5 islands from 100 cards |
| Evidence trail | v4.0 | Set intersection per card pair | ~20 trails |
| Source influence path | v4.0 | 2-pass BFS | ~15 influenced cards |
| Community subgraphs | v4.0 | Group-by aggregation | ~10 communities |

## 评估

### 当前方案: In-Memory DeterministicGraphBuilder + GraphRepository

| 维度 | v2.3 评估 | v4.0 评估 | 变化 |
|------|-----------|-----------|------|
| 依赖 | 零外部依赖 | 零外部依赖 | 不变 |
| NodeType 数量 | 5 | 8 (新增 COMMUNITY, TOPIC, ENTITY, CONCEPT_CANDIDATE) | 扩展 |
| EdgeType 数量 | 9 | 14 (新增 HAS_TAG, IN_SECTION 等) | 扩展 |
| 查询复杂度 | BFS-based | BFS + DFS + connected components + community intersection | 增强 |
| 性能（100 cards） | ~24.5ms 图构建 | ~30ms 含 sensemaking 全维度 | 几乎不变 |
| 确定性 | 完全确定性 | 完全确定性 | 不变 |
| 可测试性 | 96 tests | ~3122 tests (含 26 sensemaking + 39 ontology + 25 entity) | 大幅增强 |
| GraphPort 契约 | 9 contract tests | 9 contract tests + GraphRepository wrapper | 增强 |

### 备选方案对比

| 方案 | 适用场景 | 当前是否触发 |
|------|---------|-------------|
| In-Memory (status quo) | < 2000 cards, BFS/DFS queries | 是（当前选择） |
| networkx | PageRank, betweenness, modularity | 否 — 当前社区检测为确定性合并，不需要 centrality |
| SQLite-backed | 跨请求持久化，> 2000 cards | 否 — 每次重建 < 50ms，持久化无收益 |
| Kuzu embedded | Cypher queries, property graph, > 5000 nodes | 否 — 触发条件详见 ADR-002 |

## 决策

**继续使用 In-Memory DeterministicGraphBuilder 作为默认 GraphPort 实现。**

GraphRepository 模式（v4.1）进一步封装了 GraphPort，提供了一致的命名和访问模式，
但没有引入新的后端依赖。

### 理由

1. **v3.7-v4.0 workload 验证了 in-memory 的充分性** — 所有 8 种 NodeType、
   14 种 EdgeType 的图查询、sensemaking analysis（bridge/orphan/evidence trail/
   source influence/card evolution）均通过 BFS + DFS + set operations 实现，
   性能在个人知识库规模（< 2000 cards）下完全可接受

2. **GraphPort + GraphRepository 两层抽象已就绪** — 如果未来触发条件满足，
   只需实现 GraphPort 接口即可替换后端（Kuzu/SQLite/networkx），无架构锁定

3. **编译依赖成本仍高于收益** — Kuzu 的 C++ 依赖链在生产环境安装和调试的
   代价，在当前规模下无法被其性能优势抵消

4. **确定性优先** — in-memory 方案行为完全确定、可复现、可测试，这对个人知识
   图谱的信任建立至关重要

### 触发条件（继承自 ADR-002，v4.0 验证后不变）

满足以下任一条件时，重新评估：

1. 卡片数 > 2000 且 2-hop 查询 > 500ms
2. 需要 complex graph queries（centrality、community detection by modularity、
   subgraph isomorphism）
3. 需要持久化图结构（跨请求缓存，避免每次重建）
4. 需要 Cypher-like property graph queries（pattern matching on node/edge properties）

### 推荐升级路径

如果触发条件满足，按成本和收益递增顺序评估：

1. **SQLite-backed graph**（`nodes` + `edges` 表，JSON 边属性）— 最简单，
   解决持久化和跨请求缓存
2. **networkx** — 提供 PageRank、betweenness、modularity detection 等
   graph algorithms
3. **Kuzu embedded** — 仅在 1 和 2 均不满足时才考虑，适用于复杂 property
   graph queries

## GraphRepository Pattern

v4.1 引入 `GraphRepository` 作为 GraphPort 之上的 Repository 层：

```python
class GraphRepository:
    def __init__(self, backend: GraphPort): ...
    def find_node(node_id, node_type) -> GraphNode | None: ...
    def find_edges(node_id, *, edge_types, direction) -> list[GraphEdge]: ...
    def find_subgraph(center_id, center_type, depth) -> Graph: ...
    def find_path(source_id, target_id, max_depth) -> list[list[GraphEdge]]: ...
    def find_neighbors(node_id, *, direction) -> list[GraphNode]: ...
```

设计意图：
- `GraphPort` 定义底层图查询原语（`get_node`, `get_edges`, `get_graph`, `get_path`）
- `GraphRepository` 提供语义更清晰的命名和便捷方法（`find_*`）
- 两层均可替换，互不耦合

## 不做

- 不直接引入 Kuzu / networkx / SQLite graph 生产依赖
- 不做 Kuzu spike（当前无触发条件）
- 不替换 DeterministicGraphBuilder（作为默认 fallback 保留）
- 不删除 GraphPort 抽象

## 参考

- ADR-002: In-Memory vs Kuzu Embedded Graph DB
- ADR-004: Graph Query Capability Gap Analysis
- ADR-006: Graph Ontology v1
- `src/mindforge/relations/graph_port.py` — GraphPort ABC
- `src/mindforge/relations/graph_repository.py` — GraphRepository
- `src/mindforge/relations/graph_builder.py` — DeterministicGraphBuilder
- v3.7-v4.1 Roadmap (historical, see ADRs for current state)
