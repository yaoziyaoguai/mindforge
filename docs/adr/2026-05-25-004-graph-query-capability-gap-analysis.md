---
title: "ADR-004: Graph Query Capability Gap Analysis — v2.3"
date: 2026-05-25
status: active
---

# ADR-004: Graph Query Capability Gap Analysis — v2.3

## Context

v2.3 要求盘点当前 In-Memory DeterministicGraphBuilder 支持的图查询类型，识别无法高效支持的查询类型。这是决定是否需要 Kuzu-like embedded graph DB 的关键输入。

## Current Graph Architecture

```
APIs / CLI / Web
    |
    v
GraphPort (ABC) ← 抽象边界
    |
    v
DeterministicGraphBuilder (default implementation)
    |
    v
In-Memory (Python dicts of nodes/edges, rebuilt per-request)
```

## 当前支持的图查询类型

| 查询类型 | 实现 | 复杂度 | 备注 |
|---------|------|--------|------|
| get_node (single lookup) | O(1) hash | 即时 | id → node 字典查找 |
| get_edges (node-centered) | O(E) | 线性扫描 | 遍历所有边，按 source/target 过滤 |
| get_graph (1-hop/2-hop) | O(V+E) | 图遍历 | BFS neighbor expansion |
| get_path (source→target) | O(V+E) | BFS | max_depth 参数控制 |
| multi-hop related cards | O(V+E×D) | BFS | 可配置 depth(1-3)，path 可见 |
| community detection | O(V×G) | 分组扫描 | source/tag/wiki_section 分组 |
| discovery context | O(V+E) | 图重组 | reasoning + token estimation |
| source provenance | O(E) | 线性扫描 | source-centered neighbors |

## 当前 In-Memory 方案的限制

### 1. 图不持久化（Minor）

每次请求重建整个图。对于 <2000 张卡片的规模，重建耗时 <50ms，不是瓶颈。

**是否需要 Kuzu？** 不需要。50ms 完全可接受。

### 2. No complex graph algorithms（Not yet needed）

不支持 PageRank、centrality、community detection via modularity、shortest weighted path 算法。

**是否需要 Kuzu？** 不需要。当前 community detection 使用 deterministic grouping（source/tag/wiki_section），不需要图算法。如需这些算法，networkx 是比 Kuzu 更轻量的选择。

### 3. No persistent graph queries（Future）

不支持跨请求的图查询缓存、增量图更新。

**是否需要 Kuzu？** 当前不需要。但如果未来需要"图变更通知"或"实时图查询"，Kuzu 的事务支持可能有用。

### 4. No complex Cypher-like queries（Not needed）

不支持图模式匹配、递归路径查询、聚合。

**是否需要 Kuzu？** 当前不需要。所有查询都是简单的 neighbor/path expansion，BFS 完全胜任。

## Gap Analysis Summary

| 能力 | Supported? | In-Memory 有问题？ | 需要 Kuzu？ |
|------|-----------|-------------------|-------------|
| 1-hop neighbor | Yes | No | No |
| 2-hop/3-hop traversal | Yes | No | No |
| Path finding | Yes | No | No |
| Community grouping | Yes | No | No |
| Multi-reason edges | Yes | No | No |
| Source provenance | Yes | No | No |
| Persistence | No | Minor (rebuild ~50ms) | No |
| Centrality/PageRank | No | — | No (use networkx) |
| Pattern matching | No | — | No |
| Graph update events | No | — | Future |
| Cross-request cache | No | — | Future |

## 决策

**不需要引入 Kuzu 或任何 embedded graph DB。** 当前 In-Memory 方案满足所有实际查询需求。触发条件（ADR-002）无一满足：

- 卡片数 > 2000? No (<100 test, est. <500 real)
- 2-hop query > 500ms? No (~24.5ms for 100 cards)
- 需要 complex graph queries? No (all current queries are BFS-based)
- 需要 persistence? No (rebuild is fast enough)

### 如果未来需要增强图查询能力

推荐的升级路径（优先级降序）：

1. **networkx** — 如果需要 PageRank、betweenness、community detection via modularity。纯 Python、零编译依赖、现有测试工具链兼容。
2. **SQLite-backed graph** — 如果需要跨请求持久化。与 BM25 索引共用 SQLite 基础设施。
3. **Kuzu** — 仅在 networkx 和 SQLite 均不满足需求时考虑。

## Consequences

- GraphPort 抽象保留，确保未来可替换
- v2.3 不做 Kuzu spike（无触发条件）
- DeterministicGraphBuilder 继续是默认实现
- 新增 `tests/relations/test_graph_port.py` — 9 个 Port contract tests
