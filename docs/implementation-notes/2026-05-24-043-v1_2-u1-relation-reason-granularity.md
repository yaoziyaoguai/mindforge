# v1.2 U1 Relation Reason Granularity — Implementation Notes

## 变更概要

增强图 relation evidence detail，使 SAME_SOURCE / SOURCE_LOCATION_NEIGHBOR / SAME_REVIEW_BATCH 等细分 reason 在 evidence.detail 中可区分。

## 实现决策

### detail dict 扩展

原有 `evidence.detail` 仅包含 `{"relation_reason": "same_source"}`。v1.2 扩展为：

```python
{
    "relation_reason": "same_source",        # 保留向后兼容
    "original_reason": "same_source",         # 同 relation_reason（显式命名）
    "shared_entity_type": "source_document",  # 实体类型标签
    "shared_entity_name": "src_a",            # 具体共享实体名称
}
```

### 新增映射

- `_REASON_ENTITY_TYPE`: RelationReason → 实体类型标签（source_document / tag / wiki_section / review_batch / source_location_neighbor）
- `_extract_shared_entity()`: 从 reason_detail 文本中提取共享实体名称
- `_local_reason_entity_type()`: local_graph 字符串 reason 的实体类型映射

### 影响范围

- `graph_builder.py`: `get_edges()`, `_card_centered_graph()` (2-hop), `_local_graph_edge_to_graph_edge()` 三处 detail 生成统一更新
- `tests/relations/test_graph_builder.py`: 新增 2 个 granularity 测试

### 兼容性

- `relation_reason` key 保留，现有 API 消费者无影响
- 新增 `original_reason` / `shared_entity_type` / `shared_entity_name` 为增量字段

## Gate 结果

| Gate | Exit Code |
|------|-----------|
| `npm --prefix web run build` | 0 |
| `python -m pytest tests/ -q` | 0 (374 passed, 1 skipped) |
| `ruff check src tests` | 0 |
| `git diff --check` | 0 |

## 已知限制

- `_local_graph_edge_to_graph_edge` 的 detail 不包含 `shared_entity_name`（local_graph edge 缺少该信息）
- SOURCE_LOCATION_NEIGHBOR 和 SAME_SOURCE 仍映射到同一 EdgeType (RELATED_BY_SOURCE)，仅在 detail.original_reason 中可区分
