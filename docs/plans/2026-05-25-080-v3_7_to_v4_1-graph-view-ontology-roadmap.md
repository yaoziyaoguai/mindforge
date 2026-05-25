# v3.7-v4.1 Graph View & Knowledge Ontology Roadmap

> **v4.2 truth reset 追记 (2026-05-25)**：本 roadmap 中规划的 Graph/Sensemaking 全能力已在
> v4.2 red team audit 后降级为 lab/internal。当前仅 card / source / tag / wiki_section 4 种
> NodeType 在 Graph API 中正式暴露，community / topic / entity / concept_candidate 返回 422。
> Sensemaking 已被标记为 LAB/INTERNAL 并从主导航隐藏。本文档保留为 historical planning artifact。
> 当前产品方向见 `docs/plans/2026-05-25-087-post-stabilization-direction.md`。

**日期**: 2026-05-25
**状态**: active (historical — v4.2 truth reset applied)
**上一阶段**: v3.6.1 Audit Remediation (Batch A + B1 + B2 完成)
**产品方向**: 从"本地知识工作台"推进到"可视化、可查询、可解释的个人知识图谱系统"

---

## 0. 前置审计：当前 MindForge 抽象 → 图模型映射

### 现有对象清单

| 现有抽象 | 所在模块 | 当前图角色 | 评估 |
|---------|---------|-----------|------|
| **KnowledgeCard** | `cards.py` (CardSummary) | NodeType.CARD | 核心节点 ✅ |
| **SourceDocument** | `sources/` (13 adapters) | NodeType.SOURCE (仅 source_id 字符串) | 节点，需扩展 ✅ |
| **WikiSection** | `wiki/` | NodeType.WIKI_SECTION | 节点 ✅ |
| **Tag** | CardSummary.tags | NodeType.TAG | 节点 ✅ |
| **Concept** | (占位，未实现) | NodeType.CONCEPT | 需正式定义 ⚡ |
| **KnowledgeCommunity** | `relations/community.py` | 不在 graph_models 中 | 需决定是否入图 ⚡ |
| **KnowledgeTopic** | `relations/topic.py` | 不在 graph_models 中 | 需决定是否入图 ⚡ |
| **ApprovalDecision** | `approval_service.py` | EdgeType.APPROVAL_STATE_OF | 不是节点，只是边 ⚡ |
| **ai_draft / human_approved** | CardSummary.status | 不在图模型中（仅为 card 属性） | 应保持为 card state ❌≠node |
| **RetrievalContext / Query** | `recall_service.py` | 不在图模型中 | 不入图 ❌ |
| **ExportPackage** | `web_facade.py` | 不在图模型中 | 不入图 ❌ |
| **DogfoodRun** | `dogfood/` | 不在图模型中 | 不入图 ❌ |
| **RelatedCardEdge** | `relations/related_cards.py` | 通过 _REASON_TO_EDGE_TYPE 映射到 EdgeType | 边 ✅ |
| **RelationEvidence** | `relations/graph_models.py` | 所有边必须携带 | 基础设施 ✅ |

### 关键判断

#### 哪些是 Node（适合作为图节点）

| 对象 | 判定 | 理由 |
|------|------|------|
| **KnowledgeCard** | ✅ NODE | 有稳定 id、独立生命周期、可被引用和审计 |
| **SourceDocument** | ✅ NODE | 有 path-based identity、与 Card 是 1:N、参与 provenance |
| **WikiSection** | ✅ NODE | 有 stable id（section title/hash）、被 Card 引用 |
| **Tag** | ✅ NODE | 有 stable name identity、跨 card/source 共享 |
| **ConceptCandidate** | ✅ NODE (candidate graph) | 有 normalized label + alias set、需用户确认才能进入 fact graph |
| **Entity** (approved Concept) | ✅ NODE (fact graph) | 用户已确认的语义实体，拥有 stable canonical id |
| **KnowledgeCommunity** | ✅ NODE (computed view) | 确定性分组结果，拥有 evidence trail、可被引用 |
| **KnowledgeTopic** | ✅ NODE (computed view) | 合并重叠社区的结果，可被引用、可 navigation |

#### 哪些是 Edge（适合作为图边）

| 关系 | 判定 | 理由 |
|------|------|------|
| Card → Source (DERIVED_FROM) | ✅ EDGE | 有明确语义、可验证、有 evidence |
| Card → Tag (HAS_TAG) | ✅ EDGE | 显式用户标签关联 |
| Card ↔ Card (SHARES_TAG/SOURCE/WIKI) | ✅ EDGE | 共享实体推断的关系，附带 evidence |
| Card → WikiSection (IN_SECTION) | ✅ EDGE | Wiki 结构语义 |
| Card → ConceptCandidate (MENTIONS) | ✅ EDGE (candidate) | token-based match，需要用户确认 |
| ConceptCandidate → Entity (RESOLVES_TO) | ✅ EDGE (candidate) | 实体解析路径 |
| Community → Card (CONTAINS) | ✅ EDGE | 成员关系 |
| Topic → Community (INCLUDES) | ✅ EDGE | 主题层次 |
| ApprovalDecision → Card (APPROVES) | ❌ NOT EDGE | Approval 是 Card 状态转换，不是独立图关系 |

#### 哪些只是 Property（不应作为独立节点/边）

| 属性 | 判定 | 理由 |
|------|------|------|
| **card.status** (ai_draft / human_approved) | PROPERTY | 纯状态字段，跟随 Card 生命周期 |
| **ApprovalState / ApprovalDecision** | PROPERTY of Card | 状态转换记录，不是独立图实体 |
| **value_score** | PROPERTY of Card | 质量评分，用于 ranking/filtering |
| **created_at / updated_at** | PROPERTY | 时间戳元数据 |
| **source_location_index** | PROPERTY of Card | 文件内位置锚点 |
| **review_batch** | PROPERTY of Card | 批次标识符 |

#### 哪些不入图

| 对象 | 判定 | 理由 |
|------|------|------|
| **RetrievalContext / Query** | ❌ 不入图 | 临时查询上下文，无持久身份 |
| **ExportPackage** | ❌ 不入图 | 导出产物，不是知识结构 |
| **DogfoodRun** | ❌ 不入图 | 临时运行记录，不是知识结构 |
| **ProviderReadiness** | ❌ 不入图 | 基础设施诊断，不是知识 |
| **Run / Step** | ❌ 不入图 | 处理流水线日志，不是知识结构 |

#### Fact Graph vs Candidate Graph

```
Fact Graph (已确认)
├── Card (human_approved only)
├── SourceDocument
├── WikiSection
├── Tag
├── Entity (user-confirmed)
├── KnowledgeCommunity (deterministic, evidence-backed)
├── KnowledgeTopic (deterministic, evidence-backed)
└── Edges: DERIVED_FROM, HAS_TAG, IN_SECTION, MENTIONS(confirmed),
           SHARES_TAG, RELATED_BY_SOURCE, RELATED_BY_WIKI_SECTION,
           CONTAINS, INCLUDES

Candidate Graph (未确认，需显式审批)
├── ConceptCandidate (auto-detected, unconfirmed)
├── ai_draft Card (draft status, 不入 fact graph)
├── Edges: MENTIONS(candidate), RESOLVES_TO, SIMILAR_TO
└── 所有 candidate edge 必须标注 confidence 和 source evidence
```

---

## v3.7: Graph Ontology & Node/Edge Semantics

### Goals
- 正式定义 GraphOntology v1，回答所有 node/edge/property/evidence 分类问题
- 扩展 graph_models.py：新增 NodeType (COMMUNITY, TOPIC, CONCEPT_CANDIDATE, ENTITY)，新增 EdgeType (HAS_TAG, IN_SECTION, CONTAINS, INCLUDES, MENTIONS_CANDIDATE, RESOLVES_TO)
- 输出 ADR-006：MindForge Graph Ontology v1
- 实现 GraphNodeType / GraphEdgeType / GraphEvidence 模型的最小扩展
- 编写 ontology rules 的契约测试

### Non-Goals
- 不实现图可视化 UI
- 不实现 entity resolution 引擎
- 不引入图数据库
- 不调用 LLM / embedding
- 不修改现有 GraphPort / DeterministicGraphBuilder 行为
- 不把 approval 建模为 node

### Key Design Decisions
1. **ai_draft / human_approved 是 Card 的 status property，不是独立的 NodeType**
2. **ConceptCandidate ≠ Entity**：ConceptCandidate 属于 candidate graph，Entity 属于 fact graph
3. **Community / Topic 作为 NodeType 入图**：它们的计算是确定性的，结果可被引用
4. **所有新 Edge 必须附带 RelationEvidence**
5. **Fact graph 只包含 human_approved cards + 已确认 entities**

### Acceptance Criteria
- [ ] ADR-006 完成：包含完整 node/edge classification table
- [ ] graph_models.py NodeType 枚举扩展（+4 类型）
- [ ] graph_models.py EdgeType 枚举扩展（+6 类型）
- [ ] 所有新类型有中文 docstring 解释建模理由
- [ ] 契约测试：验证 ontology rules（fact vs candidate 边界、approval 不入图等）
- [ ] ruff clean
- [ ] pytest 全部通过

### Tests
- `tests/relations/test_graph_ontology.py`：ontology rules 契约测试
  - fact graph 不应包含 ai_draft cards
  - approval 不作为 node type
  - candidate edge 必须有 confidence/source_evidence
  - community 必须是 NodeType

### Implementation Notes Requirement
- `docs/implementation-notes/2026-05-25-081-v3_7-graph-ontology.md`

---

## v3.8: Knowledge Graph View MVP

### Goals
- 基于 v3.7 ontology 实现图视图 MVP
- 后端：扩展 `/api/graph` endpoint，返回 subgraph（按 depth + node_type 过滤）
- 前端：新增 GraphView 页面，展示以 card/source/tag/community 为中心的 subgraph
- 节点支持：Card, Source, Tag, WikiSection, Community, Topic, ConceptCandidate
- 边支持：DERIVED_FROM, HAS_TAG, IN_SECTION, CONTAINS, SHARES_TAG, RELATED_BY_SOURCE, RELATED_BY_WIKI_SECTION
- 点击节点/边展示 reason/evidence/provenance
- 从 Card detail / Wiki / Workbench 提供进入 graph view 的入口
- D3.js 或 vis-network 轻量渲染（不引入 heavy visualization framework 未经 spec 评估）

### Non-Goals
- 不做全量全局大图渲染
- 不做 3D / 炫技可视化
- 不引入 Neo4j / Kuzu 生产依赖
- 不修改现有 knowledge card / wiki 语义
- 不调用 LLM / embedding

### Acceptance Criteria
- [ ] `/api/graph/subgraph?center_id=X&center_type=Y&depth=2` 返回 Graph JSON
- [ ] GraphView 页面在浏览器中可访问（`/graph` 路由）
- [ ] 至少 5 种 node type 可渲染
- [ ] 至少 5 种 edge type 可渲染
- [ ] 点击节点弹出 info panel（label, type, evidence count）
- [ ] 点击边展示 evidence reason + evidence text
- [ ] 从 Card detail 页面可跳转到 graph view
- [ ] npm build 通过
- [ ] product copy tests 通过
- [ ] pytest 全部通过

### Tests
- `tests/test_graph_api.py`：subgraph API 端点测试
- `tests/test_web_product_copy.py`：新增 GraphView i18n keys

### Smoke
- Browser: 打开 /graph，确认 subgraph 渲染
- Browser: 从 card detail → graph view 跳转
- API: `curl /api/graph/subgraph?center_id=...&center_type=card&depth=1`

### Implementation Notes Requirement
- `docs/implementation-notes/2026-05-25-082-v3_8-graph-view-mvp.md`

---

## v3.9: Entity Resolution & Concept Candidate Layer

### Goals
- 实现 ConceptCandidate 的确定性检测：从 card title/tags/wiki_section/body_summary 提取候选实体
- 支持 alias grouping（基于 normalized label + shared context）
- 确定性 confidence scoring（非 LLM，非 embedding）
- ConceptCandidate → Entity 的升级路径（需显式用户确认）
- 区分 Entity (approved) / ConceptCandidate (unconfirmed) / Tag (user-defined) / Topic (computed)

### Non-Goals
- 不调用 LLM 做 entity extraction
- 不使用 embedding / vector DB 做 entity resolution
- 不自动把 ConceptCandidate 升级为 Entity
- 不替换现有 Tag 系统
- 不做 named entity recognition (NER) with external models

### Resolution Rules（确定性）
1. **Exact match**: 相同 normalized title → 同一 candidate
2. **Substring containment**: "Reinforcement Learning" 包含 "Learning" → weak link
3. **Shared tag context**: 两张 card 共享 ≥2 tags → candidate 可能有共同 entity
4. **Wiki section co-occurrence**: 同一 wiki section 下的 card → 共享 topic entity
5. **Source proximity**: 同一 source 相邻位置的 card → 共享 context entity

### Acceptance Criteria
- [ ] `ConceptCandidate` frozen dataclass：label, aliases, source_card_ids, confidence, evidence
- [ ] `detect_concept_candidates()` 函数：输入 cards，返回 list[ConceptCandidate]
- [ ] Entity ≠ ConceptCandidate 的建模边界清晰
- [ ] 测试：确定性规则覆盖（exact match, substring, shared context）
- [ ] 测试：ConceptCandidate 不会自动升级为 Entity
- [ ] ruff clean
- [ ] pytest 全部通过

### Tests
- `tests/relations/test_entity_resolution.py`：candidate detection + boundary tests

### Implementation Notes Requirement
- `docs/implementation-notes/2026-05-25-083-v3_9-entity-resolution.md`

---

## v4.0: Graph-backed Sensemaking Workspace

### Goals
- 不是运维台，是基于图视图和 ontology 的知识理解工作空间
- 支持以下 sensemaking 视图：
  - **主题/社区子图**: 以 Community/Topic 为中心的 subgraph
  - **Source influence path**: 从 Source → Cards → Related Cards 的影响传播
  - **Card evolution path**: 同一 source 下卡片的知识演化
  - **Bridge nodes**: 连接两个社区/主题的关键卡片
  - **Orphan islands**: 与其他卡片无共享关系的孤立卡片群
  - **Evidence trail**: 每条边的完整溯源链
  - **Candidate vs Fact 切换**: 一键切换显示候选关系/已确认关系
- 所有结论必须 evidence-backed
- 不做 RAG answering / LLM summary

### Non-Goals
- 不替换 Library / Wiki / Recall 页面
- 不做 health dashboard
- 不调用 LLM
- 不做 RAG answering
- 不自动生成结论

### Acceptance Criteria
- [ ] SensemakingView 页面：包含至少 4 种视图模式
- [ ] Bridge node detection：识别连接不同 community 的卡片
- [ ] Orphan island detection：识别无共享关系的卡片群
- [ ] Evidence trail panel：展示选中边的完整溯源
- [ ] Candidate/Fact toggle：一键切换
- [ ] npm build 通过
- [ ] product copy tests 通过
- [ ] pytest 全部通过

### Tests
- `tests/test_sensemaking.py`：bridge/orphan/evidence trail 检测

### Smoke
- Browser: 打开 sensemaking 页面，切换 4 种视图模式
- Browser: 验证 evidence trail panel 可交互

### Implementation Notes Requirement
- `docs/implementation-notes/2026-05-25-084-v4_0-sensemaking-workspace.md`

---

## v4.1: Local Graph Backend Decision

### Goals
- 基于 v3.7-v4.0 的真实 query/view workload 数据，评估是否需要图数据库
- 对比方案：
  1. **Current in-memory**: DeterministicGraphBuilder + dict/set 索引
  2. **SQLite-backed**: 将 graph 结构持久化到 SQLite（nodes/edges 表）
  3. **Kuzu embedded**: 嵌入式 property graph DB（spike-only，默认关闭）
- 设计 GraphBackendPort / GraphRepository boundary
- 输出 ADR-007：什么时候需要 embedded graph database

### Non-Goals
- 不直接引入 Kuzu 生产依赖
- 不做性能 benchmark 造假
- 不替换现有 DeterministicGraphBuilder（作为 fallback 保留）

### Acceptance Criteria
- [ ] GraphBackendPort ABC：定义 graph 查询边界
- [ ] GraphRepository：基于 GraphBackendPort 的 repository pattern
- [ ] ADR-007：graph backend decision with evidence from v3.7-v4.0 workload
- [ ] 如果做 Kuzu spike：默认关闭、可删除、无真实数据、无 secrets
- [ ] 测试：repository 契约测试（可替换性验证）

### Tests
- `tests/relations/test_graph_backend.py`：GraphBackendPort 契约测试

### Implementation Notes Requirement
- `docs/implementation-notes/2026-05-25-085-v4_1-graph-backend-decision.md`

---

## Graph Modeling Principles（全局约束）

### 1. Node 原则
- 有稳定身份的对象才适合作为 node
- 有生命周期、可被引用、可被审计、可被用户理解的对象优先作为 node
- 纯状态字段不要轻易作为 node
- UI-only grouping 不要轻易作为 node
- 计算中间结果默认不是 node，除非需要被复用/审计/引用

### 2. Edge 原则
- Edge 必须表达真实语义，不能只有 RELATED_TO
- Edge 必须有 type
- Edge 必须有 direction，除非明确是 symmetric
- Edge 必须有 evidence/reason/provenance
- Candidate edge 和 fact edge 必须区分
- 没有 evidence 的关系不能进入 fact graph

### 3. Entity 原则
- Entity 不等于 Card
- Card 是知识工作流对象
- Entity 是被多个 card/source/wiki mention 的语义对象
- ConceptCandidate 是未确认实体候选
- 多个 Card 可以 mention 同一个 Entity/ConceptCandidate
- 一个 Entity/ConceptCandidate 可以属于多个 Topic/Community

### 4. Approval 原则
- AI 只能生成 ai_draft
- human_approved 必须 explicit approval
- ConceptCandidate 不能自动升级为 approved Entity
- Candidate graph 不能冒充 fact graph
- Graph view 不能暗示 AI 自动确认了事实关系

### 5. Deterministic / Local / Safe 原则
- 所有图关系由确定性规则计算，不使用 embedding/vector DB
- 不调用 LLM 生成关系或结论
- Fact graph 只包含已确认（human_approved）的知识
- 所有 candidate 标注为 candidate，视觉上与 fact 明确区分
- 不依赖外部服务

---

## Self-Review

### 是否真正解决"点、边、实体"的核心问题？
**是**。v3.7 直接给出 node/edge/property 的明确分类表，v3.9 解决 entity ≠ card 的区分问题，v4.0 基于这些抽象做有意义的知识理解。

### 是否只是把已有 Card 关系 UI 换皮？
**否**。当前 graph_models.py 已有 NodeType/EdgeType 但缺少 CONCEPT_CANDIDATE、ENTITY、COMMUNITY、TOPIC 等关键类型，且 EdgeType 缺少 HAS_TAG、IN_SECTION、CONTAINS 等基本语义边。v3.7 填补了这些空白。

### 是否能支撑后续图视图？
**是**。v3.7 定义 ontology，v3.8 基于 ontology 做 view，v3.9 增强 entity resolution，v4.0 基于完整 ontology 做 sensemaking，v4.1 评估是否需要图数据库。每一层都建立在上一层的基础上。

### 是否过度抽象？
**否**。ontology 只新增真正有语义差异的类型，不引入通用 KnowledgeNode/KnowledgeEdge 基类的继承层次。NodeType 和 EdgeType 使用 enum，简单直接。

### 是否把状态字段错误建成 node？
**否**。已明确 ai_draft/human_approved 是 card property，ApprovalDecision 不是独立 node。

### 是否把没有 evidence 的关系放进 fact graph？
**否**。fact graph 只包含有 evidence 的关系，candidate graph 明确标注为 candidate，两者视觉可区分。

### 安全红线检查
- ✅ 不做 RAG answering
- ✅ 不做 embedding / vector DB
- ✅ 不调用真实 LLM / Cubox / Upstage
- ✅ 不处理真实私人资料
- ✅ 不写真实 Obsidian vault
- ✅ 不破坏 explicit approval / human_approved 语义
- ✅ 不引入大型依赖（v4.1 Kuzu 仅 spike，默认关闭）
- ✅ 不自动 approve
- ✅ Fact graph 与 candidate graph 严格区分

---

## Next Stage Transition

v3.7 完成后 → v3.8（Graph View MVP）
v3.7 完成条件：ADR-006 已写、graph_models.py 已扩展、契约测试通过

v3.8 完成后 → v3.9（Entity Resolution）
v3.8 完成条件：GraphView 页面可访问、subgraph API 可用、npm build + pytest 通过

v3.9 完成后 → v4.0（Sensemaking Workspace）
v3.9 完成条件：ConceptCandidate 检测可用、entity ≠ card 边界清晰

v4.0 完成后 → v4.1（Graph Backend Decision）
v4.0 完成条件：SensemakingView 4+ 视图模式、bridge/orphan 检测可用

v4.1 完成后 → v4.2+（后续 roadmap TBD，基于 v4.1 ADR 决定）
