---
title: "ADR-006: Graph Ontology v1 — Node/Edge/Entity Semantics for v3.7"
date: 2026-05-25
status: partial — ontology definition valid, but only 4/8 NodeType (card/source/tag/wiki_section) implemented as of v4.2; remaining 4 (community/topic/entity/concept_candidate) are lab/internal
---

> **v4.2 truth reset 追记 (2026-05-25)**：本文档定义的 8 种 NodeType（含 COMMUNITY、TOPIC、
> ENTITY、CONCEPT_CANDIDATE）和 14 种 EdgeType 是 ontology 完整定义。当前 backend
> (`DeterministicGraphBuilder`) 仅实现其中 4 种 NodeType：card / source / tag / wiki_section。
> 其余 4 种 NodeType 的 API 端点返回 422。本文档的 ontology 定义仍然有效，但实现状态
> 以 v4.2 为准。
> 详见 `docs/implementation-notes/2026-05-25-086-v4_2-red-team-stabilization.md`。

# ADR-006: Graph Ontology v1 — Node/Edge/Entity Semantics for v3.7

## Context

v3.7 是 MindForge 从"本地知识工作台"向"可视化、可查询、可解释的个人知识图谱系统"演进的起点。当前 graph_models.py 已定义了基础的 NodeType (CARD, SOURCE, WIKI_SECTION, TAG, CONCEPT) 和 EdgeType (9 种)，但存在以下问题：

1. **CONCEPT NodeType 是占位符**：存在于 enum 但无实现、无定义、无区分
2. **Community/Topic 不在图模型中**：KnowledgeCommunity 和 KnowledgeTopic 是独立 dataclass，但无法作为图节点被 GraphPort 访问
3. **Entity 与 Card 未区分**：没有 Entity 作为独立图节点类型
4. **Fact/Candidate 无区分**：所有边和节点同质化，无法区分已确认关系与候选关系
5. **Approval 语义模糊**：APPROVAL_STATE_OF 作为 EdgeType，但 Approval 是否应为节点？
6. **缺少基础语义边**：HAS_TAG（Card→Tag）、IN_SECTION（Card→WikiSection）、CONTAINS（Community→Card）等

## Decision

### 1. NodeType 扩展

新增 4 个 NodeType，从 5 个扩展到 9 个：

| NodeType | 含义 | 稳定性 | 图归属 | 示例 |
|----------|------|--------|--------|------|
| CARD | 知识卡片（human_approved） | 稳定 | fact graph | `card-abc123` |
| SOURCE | 源文档 | 稳定 | fact graph | `path/to/note.md` |
| WIKI_SECTION | Wiki 章节 | 稳定 | fact graph | `§1.1 定义` |
| TAG | 用户标签 | 稳定 | fact graph | `#machine-learning` |
| **COMMUNITY** | **确定性知识社区** | **稳定** | **fact graph** | `[source: shared_doc]` |
| **TOPIC** | **合并重叠社区的主题** | **稳定** | **fact graph** | `[topic: ML基础]` |
| **ENTITY** | **用户确认的语义实体** | **稳定** | **fact graph** | `Transformer架构` |
| **CONCEPT_CANDIDATE** | **自动检测的候选实体** | **不稳定** | **candidate graph** | `可能是"梯度下降"` |
| ~~CONCEPT~~ | ~~原占位符~~ | — | — | **重命名为 CONCEPT_CANDIDATE** |

**关键决策**：
- **CONCEPT 重命名为 CONCEPT_CANDIDATE**：避免与"confirmed concept"混淆
- **ENTITY 是 fact graph node**：需用户显式确认后从 CONCEPT_CANDIDATE 升级
- **COMMUNITY / TOPIC 入图**：确定性计算结果，有稳定 identity 和 evidence trail
- **ai_draft Card 仍使用 CARD NodeType**：status 是 property，不是独立 NodeType

### 2. EdgeType 扩展

新增 7 个 EdgeType（保留 9 个旧类型，淘汰 1 个，重命名 1 个），从 9 种扩展到 15 种：

| EdgeType | 方向 | 语义 | 图归属 | Evidence |
|----------|------|------|--------|----------|
| DERIVED_FROM | Card → Source | 卡片从来源派生 | fact | source_id |
| **HAS_TAG** | **Card → Tag** | **卡片被标签标记** | **fact** | **card.tags** |
| **IN_SECTION** | **Card → WikiSection** | **卡片属于 Wiki 章节** | **fact** | **card.wiki_sections** |
| SHARES_TAG | Card ↔ Card | 共享标签 | fact | shared tag names |
| RELATED_BY_SOURCE | Card ↔ Card | 同一来源 | fact | shared source_id |
| RELATED_BY_WIKI_SECTION | Card ↔ Card | 同一 Wiki 章节 | fact | shared wiki_section |
| SIMILAR_TITLE_OR_TERM | Card ↔ Card | 标题/术语相似 | fact | token overlap evidence |
| **CONTAINS** | **Community → Card** | **社区包含卡片** | **fact** | **community membership** |
| **INCLUDES** | **Topic → Community** | **主题包含社区** | **fact** | **overlap evidence** |
| LINKS_TO | Card → Card | 人工链接 | fact | user action |
| WIKI_SECTION_REFERENCE | Card → WikiSection | Wiki 章节引用 | fact | section title |
| **MENTIONS_CANDIDATE** | **Card → ConceptCandidate** | **卡片可能提及候选实体** | **candidate** | **token match** |
| **RESOLVES_TO** | **ConceptCandidate → Entity** | **候选解析为实体** | **candidate→fact** | **user confirmation** |
| **BELONGS_TO_TOPIC** | **Card → Topic** | **卡片属于主题** | **fact** | **community overlap** |
| ~~APPROVAL_STATE_OF~~ | — | **移除**：Approval 不是边关系 | — | — |

**关键决策**：
- **APPROVAL_STATE_OF 移除**：已是 card status property，不是独立的图关系
- **HAS_TAG 替代 SHARES_TAG 的 Card→Tag 方向**：SHARES_TAG 保留为 Card↔Card 对称边
- **CONTAINS / INCLUDES 引入层次关系**：Community→Card 和 Topic→Community
- **MENTIONS_CANDIDATE 属于 candidate graph**：自动检测的关系，需用户确认

### 3. Fact Graph vs Candidate Graph

```
┌─────────────────────────────────────────────┐
│              FACT GRAPH                      │
│  (所有 node 和 edge 有确定性 evidence)        │
│                                              │
│  Nodes: CARD (human_approved only),          │
│         SOURCE, WIKI_SECTION, TAG,           │
│         COMMUNITY, TOPIC, ENTITY             │
│                                              │
│  Edges: DERIVED_FROM, HAS_TAG, IN_SECTION,   │
│         SHARES_TAG, RELATED_BY_SOURCE,       │
│         RELATED_BY_WIKI_SECTION,             │
│         SIMILAR_TITLE_OR_TERM, CONTAINS,     │
│         INCLUDES, LINKS_TO,                  │
│         WIKI_SECTION_REFERENCE,              │
│         BELONGS_TO_TOPIC, RESOLVES_TO        │
└─────────────────────────────────────────────┘
                      ▲
                      │ 用户显式确认
                      │
┌─────────────────────────────────────────────┐
│           CANDIDATE GRAPH                    │
│  (所有 node 和 edge 待确认)                   │
│                                              │
│  Nodes: CONCEPT_CANDIDATE,                   │
│         CARD (ai_draft — 不入 fact graph)     │
│                                              │
│  Edges: MENTIONS_CANDIDATE (Card→Candidate)  │
└─────────────────────────────────────────────┘
```

### 4. 明确非节点对象

以下对象明确**不作为图节点**：

| 对象 | 理由 | 替代方案 |
|------|------|---------|
| ApprovalDecision | 状态转换记录，不是独立实体 | Card 的 approval_history property |
| ai_draft (as separate type) | 是 Card 的生命周期阶段 | Card 的 status property |
| RetrievalContext/Query | 临时查询上下文 | 不入图 |
| ExportPackage | 导出产物 | 不入图 |
| DogfoodRun | 临时运行记录 | 不入图 |
| ProviderReadiness | 基础设施诊断 | 不入图 |
| Run/Step | 流水线执行日志 | 不入图 |
| value_score | 评分 | Card 的 property |
| source_location_index | 位置锚点 | Card 的 property |

### 5. Entity 独立于 Card

```
Card (知识工作流对象)          Entity (语义对象)
┌──────────────────┐          ┌──────────────────┐
│ id: "card-123"   │          │ id: "ent-001"    │
│ title: "..."     │ MENTIONS │ label: "Transformer"
│ status: approved │────────→│ aliases: [...]   │
│ tags: [...]      │          │ source_cards: [..]│
│ body: "..."      │          │ confidence: 0.85  │
└──────────────────┘          └──────────────────┘

一张 Card 可以 MENTIONS 多个 Entity
一个 Entity 可以被多张 Card MENTIONS
Entity 有独立的 canonical label + alias set
Entity 可属于多个 Topic/Community
```

## Consequences

### Positive
- 图模型语义完整：node/edge/property 分类明确，不再有"这个东西该不该入图"的模糊
- Fact/Candidate 分离：用户可信任 fact graph，同时探索 candidate 可能性
- Entity ≠ Card：为未来的跨卡片实体查询和概念发现奠定基础
- Community/Topic 入图：社区发现结果可被引用、可导航、可审计

### Negative
- EdgeType 从 9 扩展到 15：需要更新 graph_builder.py 的映射逻辑
- CONCEPT → CONCEPT_CANDIDATE 重命名：如有关联代码引用旧名需更新
- APPROVAL_STATE_OF 移除：如有关联代码依赖需迁移

### Risks
- **Medium**: 移除 APPROVAL_STATE_OF 可能影响现有 approval 流程的图查询（如已使用）
- **Low**: 现有代码几乎不引用 CONCEPT NodeType（仅为占位符）
- **Low**: 新 NodeType 不会破坏现有 DeterministicGraphBuilder（仅扩展 switch/case）

### Migration
1. 新增 NodeType/EdgeType（向后兼容，不破坏现有 enum）
2. 重命名 CONCEPT → CONCEPT_CANDIDATE（更新所有引用）
3. 移除 APPROVAL_STATE_OF（更新所有引用，可能涉及 graph_builder.py 和 local_graph.py）
4. graph_builder.py 的 `_REASON_TO_EDGE_TYPE` 映射表无需更新（现有 6 种 reason 已全部映射）
5. Community/Topic 图的构建逻辑保留在 community.py/topic.py，GraphPort 扩展时再集成

## Related
- ADR-002: Kuzu Graph Backend (spike-only)
- ADR-004: Graph Query Capability Gap Analysis
- `docs/plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md`
- `src/mindforge/relations/graph_models.py` — 被本 ADR 直接修改
