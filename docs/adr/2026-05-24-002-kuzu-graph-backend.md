# ADR-002: Graph Backend — In-Memory vs Kuzu Embedded Graph DB

## 日期
2026-05-24

## 状态
Accepted (v2.3 re-evaluated 2026-05-25 — 触发条件仍不满足，保持 In-Memory)

## 背景

MindForge 当前使用 `DeterministicGraphBuilder`（纯 Python in-memory 实现，参见 `src/mindforge/relations/graph_builder.py`）构建知识图谱。v0.6 引入 `GraphPort` 抽象后，可以评估替换 graph backend。

Kuzu（[kuzudb.com](https://kuzudb.com)）是 embeddable property graph database（C++/Python），支持 Cypher-like 查询、ACID 事务、零外部 server 依赖。

## 评估

### 方案 A: In-Memory DeterministicGraphBuilder（现状）

| 维度 | 评价 |
|------|------|
| 依赖 | 零外部依赖 |
| 性能（100 cards） | 图构建 + 2-hop 查询 ~24.5ms（实测，2026-05-24） |
| 性能（1000 cards） | 图构建 ~50ms，2-hop 查询 ~20ms（估计） |
| 持久化 | 无 — 每次请求重新构建（纯计算，无 IO） |
| 确定性 | 完全确定性，可测试 |
| 查询能力 | 1-hop/2-hop neighbors，source/tag/wiki_section centered graph |
| 维护成本 | 纯 Python，自主可控 |
| 测试覆盖 | 现有 96 tests |

### 方案 B: Kuzu Embedded Graph DB

| 维度 | 评价 |
|------|------|
| 依赖 | **新增编译依赖** — `kuzu` Python package 含 C++ 扩展 |
| 安装复杂度 | `pip install kuzu`，需编译或预编译 wheel（~50MB） |
| 性能 | 原生 C++ 引擎，大规模图遍历有优势 |
| 持久化 | 原生 Kuzu 数据库文件，重启保留 |
| 查询能力 | Cypher-like query language，支持 complex path queries |
| Schema | node tables + edge tables 需定义和管理 |
| 维护成本 | 学习新查询语言、schema migration、调试工具链 |
| 测试覆盖 | 需从头构建 |

## 决策

**暂不引入 Kuzu，保持 In-Memory DeterministicGraphBuilder 为默认。**

### 理由

1. **当前规模不需要** — 个人知识库卡片数在 100-1000 级别，in-memory rebuild 耗时 < 50ms，Kuzu 的性能优势在此规模下不体现
2. **编译依赖代价高** — Kuzu 引入 C++ 编译链，增加安装失败率和维护负担，违反"轻量本地"原则
3. **查询需求简单** — 当前图查询只有 1-hop/2-hop neighbor + path finding，纯 Python 完全胜任
4. **GraphPort 已就绪** — 如果未来需要 Kuzu，只需实现 `GraphPort` 接口即可插拔，没有锁定
5. **不做 premature optimization** — 在性能问题实际出现前，不引入复杂度

### 触发条件（未来重审）

满足以下条件时，重新评估 Kuzu：

1. 卡片数 > 2000 且 2-hop 查询 > 500ms
2. 需要 complex graph queries（community detection、centrality、shortest path）
3. 需要持久化图（跨请求缓存图结构）
4. Kuzu 成熟度提升（稳定 API、纯 Python wheel、文档完善）

### 不做

- 不创建 spike 分支实验 Kuzu（当前没有触发条件，spike 投入产出比低）
- 不替换 DeterministicGraphBuilder
- 不在 v0.9/v1.0 引入 Kuzu

## v1.3 重新评估 (2026-05-24)

### 当前规模

- 测试数据: ~100 张虚拟卡片
- 2-hop 图构建耗时: 24.5ms（100 卡，实测）
- 社区检测耗时: 0.1ms（100 卡，实测）

### 触发条件检查

| 条件 | 阈值 | 当前 | 满足？ |
|------|------|------|--------|
| 卡片数 | > 2000 | < 100（测试） | 否 |
| 2-hop 查询延迟 | > 500ms | ~24.5ms | 否 |
| 需要 complex graph queries | 路径/中心性/社区检测 | 当前仅需 community（已 deterministic 实现） | 否 |
| 需要持久化图 | 跨请求缓存 | 每次重建 24.5ms，不需要缓存 | 否 |

### 决定

**继续使用 In-Memory DeterministicGraphBuilder。** 无触发条件满足。GraphPort 抽象保留，若未来需要 Kuzu 只需实现接口。

## v2.3 重新评估 (2026-05-25)

### v2.1-v2.2 增强后的图查询能力

自 v1.3 评估以来，图查询能力已大幅增强：

| 能力 | v1.3 状态 | v2.3 状态 | 实现方式 |
|------|-----------|-----------|---------|
| 1-hop neighbor | 有 | 有 | BFS |
| 2-hop/3-hop multi-hop | 无 | 有 | BFS + depth 参数 |
| community hierarchy | 单层 | 多层 hierarchy + overlap | deterministic grouping |
| community quality score | 无 | 有 | Jaccard + size + entropy |
| discovery context | 无 | 有 | reasoning + token estimation |
| path finding | 无 | 有 | BFS + max_depth |
| source provenance | 有 | 增强 | source-centered + evidence |
| GraphPort contract | 有 | 增强 | 9 Port contract tests |
| golden tests | 无 | 有 | 31 golden + edge case tests |
| perf baseline | 无 | 有 | 8 perf characterization tests |

### 触发条件重新检查

| 条件 | 阈值 | 当前 | 满足？ |
|------|------|------|--------|
| 卡片数 | > 2000 | < 100（测试） | 否 |
| 2-hop 查询延迟 | > 500ms | ~24.5ms（100 卡）/ ~200ms（500 卡 est.） | 否 |
| 需要 complex graph queries | 模式匹配/centrality | 当前所有查询均 BFS-based + deterministic grouping | 否 |
| 需要持久化图 | 跨请求缓存 | 每次重建 < 50ms，不需要缓存 | 否 |
| 需要图模式匹配 | Cypher-like | 不需要（见 ADR-004 gap analysis） | 否 |

### 决定

**继续使用 In-Memory DeterministicGraphBuilder。** v2.1-v2.2 的 multi-hop、community hierarchy、discovery context 等增强全部通过 BFS + deterministic grouping 实现，未产生对 embedded graph DB 的需求。GraphPort 抽象已通过 9 个 contract tests 守护，未来可安全替换。

### 推荐升级路径（如需）

1. **networkx** — PageRank、betweenness、modularity-based community detection
2. **SQLite-backed graph** — 跨请求持久化
3. **Kuzu** — 仅在前两者均不满足时考虑

## 参考

- Kuzu: https://kuzudb.com
- v0.6 GraphPort: `src/mindforge/relations/graph_port.py`
- v0.6 DeterministicGraphBuilder: `src/mindforge/relations/graph_builder.py`
- v0.7-v1.0 Roadmap (historical, see ADRs for current state)
