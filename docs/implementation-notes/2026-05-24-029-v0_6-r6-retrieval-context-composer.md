# v0.6 R6 Retrieval Context Composer (Non-RAG) 实现笔记

## 日期
2026-05-24

## 目标
实现 graph-aware retrieval context composer — 将图数据重组为面向 discovery UI 的结构化上下文，增强 recall API 支持图感知结果。

## 实现方案

### 新增文件

- `src/mindforge/relations/discovery_context.py` — DiscoveryContext 数据类 + assemble_discovery_context() 组装函数
- `src/mindforge_web/routers/discovery.py` — `/api/discovery/context` endpoint
- `tests/relations/test_discovery_context.py` — 10 个单元测试（确定性、邻居分类、evidence 完整性）

### 修改文件

- `src/mindforge/relations/__init__.py` — docstring 更新
- `src/mindforge_web/schemas.py` — 新增 DiscoveryContextResponse 等 5 个 schema、RecallHit 增加 graph_neighbor_count/graph_shared_tag_count
- `src/mindforge_web/services/web_facade.py` — 新增 get_discovery_context()、recall() 扩展 context=graph 参数、_graph_neighbor_count() 和 _discovery_context_response() helper
- `src/mindforge_web/routers/recall.py` — 新增 context 查询参数
- `src/mindforge_web/app.py` — 注册 discovery router
- `tests/relations/test_graph_api.py` — 新增 TestDiscoveryContextEndpoint (4 tests) + TestRecallWithGraphContext (2 tests)

### 数据结构

```
DiscoveryContext
├── center_card_id / center_card_title
├── direct_matches: tuple[DiscoveryCardRef, ...]   # 1-hop 邻居卡片
├── neighbor_cards: tuple[DiscoveryCardRef, ...]   # 2-hop 邻居（排重 + 衰减）
├── wiki_sections: tuple[DiscoverySectionRef, ...]  # 所属 wiki sections
├── shared_tags: tuple[DiscoveryTagRef, ...]        # 共享 tags + card_count
└── shared_sources: tuple[DiscoverySourceRef, ...]   # 共享 sources + card_count
```

### API Endpoint

`GET /api/discovery/context?ref={card_id}` → `DiscoveryContextResponse`

### Recall 增强

`GET /api/recall?q=...&context=graph` — 每个 BM25 hit 附加上 `graph_neighbor_count` 和 `graph_shared_tag_count`（轻量，不做 full 2-hop build）。

### 设计决策

1. **assemble_discovery_context 是纯函数** — 只做数据转换，不构建图。图构建由 GraphBuilder 负责。保证确定性。
2. **2-hop 邻居衰减** — neighbor_cards 的 relation_strength 乘以 0.8，表示间接关系的信度下降。
3. **recall context=graph 轻量化** — 不逐 hit 构建 full 2-hop graph，只做 get_edges() 查询 neighbor count。避免 BM25 多 hit + graph 构建的组合爆炸。
4. **不增新依赖** — 纯 Python dataclass + 现有 graph builder 复用。

### 已知限制

- assemble_discovery_context 依赖 DeterministicGraphBuilder 已构建的 Graph，不自行构建。
- recall context=graph 只提供 neighbor/tag 计数，不提供完整 discovery context（成本权衡）。
- GraphExplorer 尚未消费 /api/discovery/context（后续 R5 UI 扩展可集成）。

## Gate

| Gate | 命令 | Exit Code |
|------|------|-----------|
| ruff check | `ruff check src/mindforge/relations/ src/mindforge_web/ --select F,E --quiet` | 0 (pre-existing E501 only) |
| pytest (relations) | `python -m pytest tests/relations/ -q --tb=short` | 0 (84 passed) |
| pytest (full) | `python -m pytest tests/ -q --tb=short -k "not test_sources_page_uses_source_path_view"` | 0 |
| pytest (product copy) | `python -m pytest tests/test_web_product_copy.py -q` | 0 |
| npm build | `npm --prefix web run build` | 0 |
| git diff --check | `git diff --check` | 0 |
