# v0.6 R4 Explainable Relationship API 实现笔记

## 日期
2026-05-24

## 目标
暴露 3 个 REST API 端点，使前端能够消费 DeterministicGraphBuilder 构建的可解释知识图谱。

## 实现方案

### API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/graph/node?ref=...&depth=2` | GET | 以卡片为中心的 1-hop/2-hop 图 |
| `/api/graph/explore?node_type=...&node_id=...` | GET | 以任意节点类型（source/tag/wiki_section/card）为中心的图 |
| `/api/graph/edge?source=...&target=...` | GET | 两节点间的所有边及其可解释证据 |

### 新增/修改文件

- `src/mindforge_web/services/web_facade.py` — 新增 3 个 facade 方法 + 4 个 helper 函数
- `src/mindforge_web/routers/graph.py` — 新 router，3 个 GET 端点
- `src/mindforge_web/app.py` — 注册 graph router
- `tests/relations/test_graph_api.py` — 10 个集成测试（API + schema 验证）

### 设计决策

1. **Facade 模式** — Graph API 方法通过 WebFacade 编排，不直接在 router 中访问 relations engine。
2. **_build_graph_builder() 共享 helper** — 所有 graph facade 方法共享同一个 builder 构建逻辑：从 vault 中扫描 approved cards → 转 records → 构建 DeterministicGraphBuilder。
3. **Response 转换层** — `_graph_response()`, `_graph_node_response()`, `_graph_edge_response()` 将内部 frozen dataclass 转换为 Pydantic response model。
4. **每条边都携带 evidence** — 前端不需要额外请求即可获得完整可解释性。

### 已知限制

- CONCEPT node 类型尚未实现，`get_graph_node("x", NodeType.CONCEPT)` 返回 None。
- 不支持分页 — 当前图规模适合 100-200 card vault。
- depth 上限为 3（Query 参数约束），防止图爆炸。

## Gate

| Gate | 命令 | Exit Code |
|------|------|-----------|
| ruff check (changed files) | `ruff check src/mindforge_web/services/web_facade.py src/mindforge_web/routers/graph.py src/mindforge_web/app.py tests/relations/test_graph_api.py --select F,E --quiet` | 0 (pre-existing E501 only) |
| pytest (all relations) | `python -m pytest tests/relations/ -q --tb=short` | 0 (74 passed) |
| pytest (full excl pre-existing) | `python -m pytest tests/ -q --tb=short -k "not test_sources_page_uses_source_path_view"` | 0 |
| npm build | `npm --prefix web run build` | 0 |
| git diff --check | `git diff --check` | 0 |
