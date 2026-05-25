# v3.5 Workbench UX Integration

## 概述

补齐 v3.3 Topic Synthesis 的前端类型、API 调用和 i18n 文案，增强 product copy 一致性。

不做前端框架迁移，不引入新 UI 库，不做重大 redesign。

## 已完成

### U1: TypeScript Topic Types
- `web/src/api/types.ts` 新增：
  - `TopicMemberCommunityResponse` — 成员社区引用
  - `KnowledgeTopicResponse` — 知识主题（topic_id, topic_name, community_count, card_ids, evidence 等）
  - `KnowledgeTopicsResponse` — 主题列表包装
- `KnowledgeCommunityResponse` 新增 v3.3 字段：
  - `representative_card_ids: string[]`
  - `source_coverage: number`
  - `evidence_detail: string`

### U2: Topic API 函数
- `web/src/api/library.ts` 新增 `getKnowledgeTopics()` — 调用 `GET /api/knowledge/topics`

### U3: Topic i18n 文案
- 中文 `topic.*` 键 (9 个): title, communities_count, total_cards, representative_cards, member_communities, evidence, loading, load_error, empty
- 英文对应翻译
- 使用知识工作台语言，不含 RAG/embedding/LLM/vector 等技术术语

### U4: Product Copy Tests (4 new)
- `test_i18n_topic_keys_complete` — 所有 topic 键中英文存在且非空
- `test_topic_terms_use_knowledge_language` — 不含技术术语和自动审批暗示
- `test_topic_api_types_exist` — TypeScript 类型存在
- `test_topic_api_function_exists` — API 函数存在

## 设计决策

- **TypeScript 类型名称与 Python schema 保持一致** — `KnowledgeTopicResponse` 对应 `KnowledgeTopicResponse(BaseModel)`
- **所有 v3.3 新字段使用默认值** — Python 端 `Field(default_factory=list)` 确保前端向后兼容
- **不做 Topic 页面** — 当前导航结构已完整，主题页面留待产品需求明确后再设计

## Gate 结果

| Gate | Command | Exit Code | Result |
|------|---------|-----------|--------|
| product copy tests | `python -m pytest tests/test_web_product_copy.py -v` | 0 | 76 passed |
| npm build | `npm --prefix web run build` | 0 | built in 2.37s |
| ruff | `ruff check tests/test_web_product_copy.py` | 0 | clean |
| pytest full | `python -m pytest tests/ -q` | 0 | ~2990+ passed |
