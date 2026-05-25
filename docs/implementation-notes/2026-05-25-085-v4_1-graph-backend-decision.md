# v4.1 Local Graph Backend Decision — Implementation Notes

**日期**: 2026-05-25
**状态**: complete
**基于**: [v3.7-v4.1 Graph View Roadmap](../plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md)
**ADR**: [ADR-007 Graph Backend Decision](../adr/2026-05-25-007-graph-backend-decision.md)

---

## 实现范围

v4.1 基于 v3.7-v4.0 的真实 workload 数据，对图后端方案做出正式决策。

### 1. GraphRepository — GraphPort 之上的 Repository Pattern

**`src/mindforge/relations/graph_repository.py`** — Repository 模式封装：

```python
class GraphRepository:
    def __init__(self, backend: GraphPort): ...
    # Node queries
    def find_node(node_id, node_type) -> GraphNode | None: ...
    def node_exists(node_id, node_type) -> bool: ...
    # Edge queries
    def find_edges(node_id, *, edge_types, direction) -> list[GraphEdge]: ...
    def find_edges_between(source_id, target_id) -> list[GraphEdge]: ...
    # Subgraph queries
    def find_subgraph(center_id, center_type, depth) -> Graph: ...
    def find_card_subgraph(card_id, depth) -> Graph: ...
    def find_source_subgraph(source_id, depth) -> Graph: ...
    def find_tag_subgraph(tag, depth) -> Graph: ...
    # Path queries
    def find_path(source_id, target_id, max_depth) -> list[list[GraphEdge]]: ...
    # Neighbor queries
    def find_neighbors(node_id, *, direction) -> list[GraphNode]: ...
```

设计意图：
- `GraphPort` (已有，v0.6) — 底层图查询原语 ABC
- `GraphRepository` (新增，v4.1) — 语义清晰的 `find_*` 命名 + 便捷方法
- 两层均可替换，互不耦合

### 2. ADR-007: Graph Backend Decision

**决定**: 继续使用 In-Memory DeterministicGraphBuilder 作为默认实现。

核心依据（基于 v3.7-v4.0 workload 验证）:
- v4.1 当时记录的“8 种 NodeType 全维度查询”已被 v4.2 truth reset 修正；
  当前正式支持并暴露的是 card/source/tag/wiki_section 4 种 NodeType
- ontology 中的 community/topic/entity/concept_candidate 仍未进入生产级 Graph API/UI 能力
- Bridge node detection, orphan island detection, evidence trail, source influence,
  card evolution, community subgraphs — 全部 deterministic, < 50ms @ 100 cards
- GraphPort + GraphRepository 两层抽象已就绪，可安全替换后端

触发条件（继承自 ADR-002）:
1. 卡片数 > 2000 且 2-hop 查询 > 500ms
2. 需要 complex graph queries (centrality, modularity)
3. 需要持久化图结构
4. 需要 Cypher-like property graph queries

推荐升级路径: SQLite-backed → networkx → Kuzu

### 3. Contract Tests

**`tests/relations/test_graph_backend.py`** — 19 tests, 3 classes:
- `TestGraphRepositoryContract` (15 tests): find_node, node_exists, find_edges,
  find_edges_between, find_subgraph, find_card_subgraph, find_source_subgraph,
  find_tag_subgraph, find_path, find_neighbors
- `TestGraphRepositoryBackendSubstitutability` (3 tests): 可替换性验证，
  只读保证，backend 属性访问
- `TestGraphRepositoryBoundary` (1 test): 抽象验证，外部依赖检查

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/mindforge/relations/graph_repository.py` | NEW | GraphRepository — GraphPort 之上的 Repository 层 |
| `docs/adr/2026-05-25-007-graph-backend-decision.md` | NEW | ADR-007 |
| `docs/implementation-notes/2026-05-25-085-v4_1-graph-backend-decision.md` | NEW | v4.1 实现笔记 |
| `tests/relations/test_graph_backend.py` | NEW | 19 GraphRepository 契约测试 |

---

## Gate 结果

| Gate | 命令 | Timeout | Exit Code | 备注 |
|------|------|---------|-----------|------|
| ruff check | `ruff check src/ tests/ docs/` | no | 0 | clean |
| pytest full | `python -m pytest tests/ -q --tb=short` | no | 0 | ~3141 tests passed |
| npm build | `npm --prefix web run build` | no | 0 | build succeeded |

---

## 安全性审计

- [x] 不引入 Kuzu / networkx / SQLite 生产依赖
- [x] 不读取 .env 或 secrets
- [x] 不调用 LLM / embedding / vector DB
- [x] 不处理真实私人资料
- [x] 不写真实 Obsidian vault
- [x] 不破坏 explicit approval / human_approved 语义
- [x] GraphRepository 是纯只读封装
- [x] 不做 Kuzu spike（当前触发条件不满足）

---

## v4.2 Truth Reset（追记）

**日期**: 2026-05-25（同 v4.1 日，红队审计后追记）

红队审计结论（Overall 5.1/10, No-Go for feature expansion）后执行 truth reset：
- Graph API 暴露范围从声称的 8 种 NodeType 收缩到实际支持的 4 种（card/source/tag/wiki_section）
- community/topic/entity/concept_candidate 从 API/docs/UI 明确标记为 unsupported
- Sensemaking 降级为 lab/internal，从主导航隐藏
- BridgeNode/CardEvolutionPath/SourceInfluencePath 标记为 deterministic heuristics
- 修复 3 个 no-op/tatutological tests，新增 unsupported node type 测试
- pyproject.toml 排除 .mindforge/** 防止 wheel 打包泄露 secrets
- README 新增 Lab/Internal 功能章节，收缩 Graph/Sensemaking 声明
- GraphPage/SensemakingPage 从 Sidebar 主导航移除，保留 Library GraphExplorer 入口

## 总结: v3.7-v4.1 全量交付

| 版本 | 内容 | Commits | Tests |
|------|------|---------|-------|
| v3.7 | Graph Ontology v1 + ADR-006 | 8b92a49 | +39 |
| v3.8 | Knowledge Graph View MVP (vis-network) | a0d0eb9 | ~3070 |
| v3.9 | Entity Resolution & ConceptCandidate | c974566 | +25 |
| v4.0 | Sensemaking Workspace (6 views) | 0a10e27 | +26 |
| v4.1 | Graph Backend Decision + ADR-007 | (current) | +19 |

全量 gate 基线: ruff clean, ~3141 tests passed, npm build succeeded.
