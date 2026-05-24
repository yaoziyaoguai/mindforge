# M6 Local Graph Preview — Implementation Notes

**Date:** 2026-05-24
**Spec:** `docs/design/roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md` §10
**Status:** implemented (squash-merged into main via PR #7, commit `9e813d2`)

## 合并说明

M6 与 M3、M5 在 `feat-wiki-llm-synthesis` 分支上一起实现，通过 squash merge (PR #7) 进入 main。M6 的图构建直接复用了 M3 的索引结构（source_index, tag_index, section_index），放在同一分支上实现避免了重复代码。

## 已完成内容

M6 实现了确定性 1-hop Local Graph Preview。不做 force-directed graph，不依赖 canvas/graph DB/d3/NetworkX。

`src/mindforge/relations/local_graph.py` (216 lines) 提供两种图构建模式：

### Card-Centered Graph
`build_card_centered_graph()` — 以一张卡片为中心构建 1-hop 图：
- **节点类型**: card, source, wiki_section, tag
- **边类型**: same_source, same_tag, same_wiki_section
- **1-hop only**: 只展示中心卡片直接关联的节点，不做递归展开

### Wiki Section-Centered Graph
`build_wiki_section_centered_graph()` — 以 Wiki section 为中心构建 1-hop 图：
- 找到该 section 引用的所有卡片
- 每张卡片展开其 source 和 tags
- 节点包含跳转 href（前端可渲染为可点击链接）

### 关键设计决策

- **纯确定性**: 所有边基于字段精确匹配，无向量相似度、无 graph embedding、无 PageRank
- **1-hop 限制**: 不做多跳展开，不做全局图。这是刻意的 scope 限制——v0.3 的目标是"preview"，不是"full graph exploration"
- **无外部依赖**: 不依赖 NetworkX、d3、canvas、graphviz 或任何 graph DB
- **前端渲染**: 前端 `LocalGraphPreview.tsx` 使用纯 CSS/HTML 渲染节点和边，不引入 vis.js 或 cytoscape

### API 暴露

- Web API endpoint 在 `routers/library.py` 中暴露 graph 数据
- `GET /api/library/{card_id}/graph` 返回 `LocalGraph` JSON

## 修改文件

| 文件 | 变更 |
|------|------|
| `src/mindforge/relations/local_graph.py` | new (216 lines) |
| `tests/relations/test_graph.py` | new (13 tests) |

## Gate 验证

| Gate | Result |
|------|--------|
| `ruff check src/` | All checks passed |
| `python -m pytest tests/relations/test_graph.py -q` | 13/13 pass |
| `git diff --check` | exit 0 |
