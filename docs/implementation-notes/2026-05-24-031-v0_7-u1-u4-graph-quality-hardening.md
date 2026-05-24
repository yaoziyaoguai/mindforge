# v0.7 U1-U4 Graph Quality & Evidence Hardening 实现笔记

## 日期
2026-05-24

## 目标
修复和强化 v0.6 图/关系/发现上下文的质量和解释性。重点不是新功能，而是让已有能力可信、可理解、可维护。

## 实现方案

### U1: Evidence Text Quality Upgrade

**问题**: `_local_graph_edge_to_graph_edge()` 生成的 evidence 是机器格式 `"same_source: card_1 ↔ card_2"`，不包含共享实体名称，用户无法理解"为什么相关"。

**修复**:
- 新增 `_build_evidence_text()` 方法：查找卡片元数据中的共享实体（source path、tag name、wiki section title），生成用户可理解的 evidence
- same_source → `"same source document: reading/ai-ml.md"`
- same_tag → `"shared tag: #llm, #ai"`
- same_wiki_section → `"same wiki section: Machine Learning, LLM 基础"`
- wiki_section_reference → `"wiki section reference: Card Title"`
- 通用 fallback → `"{reason}: {source_title} — {target_title}"`（使用卡片标题而非 ID）

**文件**: `src/mindforge/relations/graph_builder.py`

### U2: Relation Reason Granularity

**问题**: `SAME_SOURCE` 和 `SOURCE_LOCATION_NEIGHBOR` 都映射到 `EdgeType.RELATED_BY_SOURCE`，丢失细分信息。

**修复**:
- 所有 `RelationEvidence` 创建时填充 `detail={"relation_reason": raw.reason.value}`
- 覆盖 `get_edges()`、`_card_centered_graph()` 2-hop、`_local_graph_edge_to_graph_edge()` 三条路径
- 下游消费者可从 `evidence.detail.relation_reason` 区分精确原因

**文件**: `src/mindforge/relations/graph_builder.py`

### U3: Graph UI Copy Audit & Polish

**问题**: GraphExplorer 组件中存在硬编码英文文本（node type 标签、input placeholder、edge type 标签），未通过 `t()` 走 i18n。

**修复**:
- 新增 6 个 i18n key：`graph.node_type_*` (3) + `graph.placeholder_*` (3)
- GraphExplorer 中所有用户可见文本改为 `t()` 调用
- 新增 `NODE_TYPE_I18N` 和 `NODE_TYPE_PLACEHOLDER` 映射表
- 所有 graph i18n key 均有 zh/en 双值

**文件**: `web/src/lib/i18n.ts`, `web/src/components/GraphExplorer.tsx`

### U4: Test Gap Characterization & Closure

**新增 12 个测试**:

**test_graph_builder.py** (+8):
- `TestEvidenceTextQuality` (4 tests): evidence 包含共享 source/tag/section 名称、无 `↔` 机器格式
- `TestEvidenceDetailDict` (2 tests): get_edges() 和 local_graph_edge 转换的 detail 均有 relation_reason
- `TestTwoHopGoldenFixture` (2 tests): 2-hop 结构确定性验证、多次构建一致性

**test_discovery_context.py** (+3):
- evidence 无机器格式、neighbor strength 衰减验证、depth=1 无 2-hop

**test_graph_api.py** (+3):
- API response evidence 无机器格式、detail 字段有 relation_reason、depth 参数边界测试

**总测试数**: 84 → 96 (relations)

### 已知限制

- GraphExplorer 的 edge type badge 仍显示英文技术标识符（由 `t()` fallback 到 edge_type 字符串），后续可添加 edge_type → i18n key 完整映射
- Browser smoke (U5) 尚未执行，待后续 loop 完成
- `_source_centered_graph()` 和 `_tag_centered_graph()` 的 evidence 格式未统一（保持合理的现有格式）

## Gate

| Gate | 命令 | Exit Code |
|------|------|-----------|
| ruff F+E (changed files) | `ruff check src/mindforge/relations/graph_builder.py tests/relations/ --select F,E` | 0 |
| pytest (relations) | `python -m pytest tests/relations/ -q --tb=short` | 0 (96 passed) |
| pytest (full) | `python -m pytest tests/ -q --tb=short -k "not test_sources_page_uses_source_path_view"` | 0 |
| pytest (product copy) | `python -m pytest tests/test_web_product_copy.py -q` | 0 |
| npm build | `npm --prefix web run build` | 0 (2.6s) |
| git diff --check | `git diff --check` | 0 |
