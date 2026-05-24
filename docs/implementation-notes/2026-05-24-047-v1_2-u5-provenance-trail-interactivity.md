# v1.2 U5 Provenance Trail Interactivity — Implementation Notes

## 决策

### 双向探索：related_sources

在 provenance trail 中新增 `related_sources` 字段，实现 card → source → related sources 的双向导航链。

计算方式：收集当前 source 的所有 tags 和 wiki_sections，然后遍历所有其他 source，统计共享的 tags 和 sections 数量。按共享实体总数降序排列，取前 5。

### 后端变化

- `ProvenanceTrailRelatedSource`: 新增 schema，包含 source_id、source_title、card_count、shared_tags、shared_wiki_sections
- `ProvenanceTrailResponse.related_sources`: 新增字段（list）
- `_compute_related_sources()`: 纯函数，计算关联来源

### 前端变化

- `ProvenanceTrail` 组件新增 Step 4: Related Sources section
- 每个 related source 显示：来源名、卡片数、共享的 tags 和 wiki_sections
- 新增 4 个 i18n label（中/英）

### 交互设计

- 点击 source title：暂无跳转（source 详情页尚未实现），但数据已就绪
- 点击 sibling card：已有跳转支持（`onSelectCard` 回调）

## 边界权衡

- **共享计数简单化**: 目前仅计算 tag + section 数量之和，不做加权。未来可引入 Jaccard 相似度或加权计数。
- **最多 5 个 related sources**: 与 sibling_cards 限制对齐，避免过量信息。
- **仅限 approved cards**: 不包含 ai_draft。

## 已知限制

- 不计算 transitive relations（source A → source B → source C）
- 不做 source co-occurrence matrix（无 embedding/matrix factorization）
- 前端 source title 不可点击（source 详情页尚未实现）
