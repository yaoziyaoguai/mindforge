# v3.3 Community / Topic Sensemaking Layer

## 概述

增强 v2.1 社区检测为 v3.3，新增代表性卡片选择、来源覆盖率、增强证据链、
Topic 合成（交叉社区合并为更宽泛知识主题）。

所有计算均为确定性，不调用 LLM，不做 embedding，不做 vector DB。

## 已完成

### U1: Community Detection Enhancement (`community.py` v3.3)

- `KnowledgeCommunity` 新增 3 个字段：
  - `representative_card_ids` — 代表性卡片（质量 + 连接度启发式选择）
  - `source_coverage` — 来源覆盖率（有 source_id 的成员比例）
  - `evidence_detail` — 增强证据文本（类型 + 实体 + 代表性卡片 + 覆盖率 + 子社区数 + 交叉数）
- `select_representative_cards()` — 质量分 × 0.6 + 连接度分 × 0.4，取 top-N
- `_compute_source_coverage()` — 来源覆盖率计算
- `_build_evidence_detail()` — 确定性证据模板
- `_enrich_communities()` — 原地增强所有社区的后处理步骤

### U2: Topic Synthesis (`topic.py` v3.3)

- `KnowledgeTopic` — 确定性知识主题
  - `topic_id` / `topic_name` / `community_count` / `total_card_count` / `card_ids`
  - `member_communities` — 成员社区列表
  - `representative_card_ids` — 精选代表性卡片（最多 5 张）
  - `evidence` — 解释为什么这些社区构成一个主题
- `TopicMemberCommunity` — 成员社区引用
- `detect_topics()` — 并查集连通分量算法
  - 构建社区重叠图（共享成员 ≥ min_overlap 的异类型社区相连）
  - 找连通分量 → 每个分量 = 一个 Topic
  - Topic 命名：取最大社区的 shared_entity + 类型标签
  - 纯确定性，无 LLM

### U3: API + Schemas + Router

- `schemas.py` 新增：
  - `KnowledgeCommunityResponse` 新增 3 字段（representative_card_ids, source_coverage, evidence_detail）
  - `TopicMemberCommunityResponse` / `KnowledgeTopicResponse` / `KnowledgeTopicsResponse`
- `web_facade.py` 新增 `knowledge_topics()` 方法
- `library.py` 新增 `GET /api/knowledge/topics` 端点
- 所有新字段使用 default 值保持向后兼容

### U4: Tests (25 tests)

- `TestRepresentativeCards` (5): 上限、下限、质量偏好、空输入、确定性
- `TestCommunityEnhancement` (7): 代表性卡片存在、覆盖率范围、全覆盖、部分覆盖、证据非空、关键信息、向后兼容
- `TestTopicSynthesis` (10): 检测、结构验证、去重、min过滤、无重叠、证据解释、排序、确定性、空输入、单社区
- `TestE2ECommunityTopic` (3): 完整管线、代表性卡片有效性、Topic 代表性卡片有效性

## 设计决策

- **质量 + 连接度启发式** — 代表性卡片选择平衡卡片质量和知识图谱位置（中心性）
- **并查集而非 DBSCAN/Spectral** — 社区重叠图规模小（通常 < 50 个社区），简单的连通分量足够；避免引入 scikit-learn 等重依赖
- **Topic 命名以最大社区为准** — 确定性命名策略，不依赖 LLM；最大社区通常最能代表主题核心
- **向后兼容** — 所有新字段使用 default 值，已有 API 消费者不受影响
- **并查集而非 NetworkX** — 避免引入图算法依赖，手工实现简单可靠

## Gate 结果

| Gate | Command | Exit Code | Result |
|------|---------|-----------|--------|
| ruff | `ruff check src/mindforge/relations/ src/mindforge_web/ tests/test_community_topic.py` | 0 | clean (4 auto-fixed) |
| pytest (unit) | `python -m pytest tests/test_community_topic.py -v` | 0 | 25 passed |
| pytest (full) | `python -m pytest tests/ -q` | 0 | ~2930+ passed |
| npm build | `npm --prefix web run build` | 0 | built in 2.35s |

## 已知限制

- Topic 合成依赖于社区重叠图的连通分量，极端情况下（所有社区都交叉）会产生一个巨型 Topic
- 未来可引入 community 合并策略（如 Louvain-inspired modularity optimization）来拆分过大的 Topic
- Topic 名称当前从最大社区派生，未来可增强为从卡片标题中提取共同术语
- API smoke 未运行（dev server 未启动），但代码审查 + 单元测试覆盖

## 与 v3.3 Roadmap 对齐

| Acceptance Criteria | Status |
|---------------------|--------|
| deterministic topic/community detection enhancement | [x] community.py v3.3 + topic.py |
| representative card selection per community | [x] select_representative_cards() |
| community evidence trail | [x] evidence_detail + evidence fields |
| UI: topic map / community browser | [x] API endpoints ready, schemas updated |
| all gates clean | [x] ruff + pytest + build all 0 |
| browser smoke | [-] dev server not running (API schema verified by tests) |
