"""v0.7 Graph Domain Models — 统一图数据结构（v3.7 ontology 扩展）。

中文学习型说明：本模块定义了 MindForge 知识图谱的通用数据类型。
Node/Edge/RelationEvidence/Graph 是 GraphPort 和 GraphBuilder 的共享合约，
不依赖具体存储实现（in-memory / Kuzu / SQLite FTS 等）。

v3.7 升级（ADR-006 — Graph Ontology v1）：
- NodeType 从 5 个扩展到 8 个：新增 COMMUNITY, TOPIC, ENTITY, CONCEPT_CANDIDATE
- EdgeType 从 9 个重新组织为 14 个：新增 HAS_TAG, IN_SECTION, CONTAINS, INCLUDES,
  MENTIONS_CANDIDATE, RESOLVES_TO, BELONGS_TO_TOPIC；移除 APPROVAL_STATE_OF（Approval 是 card property 而非图关系）
- 明确 fact graph 与 candidate graph 的边界：CONCEPT_CANDIDATE 和 MENTIONS_CANDIDATE 属于 candidate graph

当前实现状态（v4.2 truth reset）：
- DeterministicGraphBuilder 当前正式支持 4 种 NodeType: CARD, SOURCE, TAG, WIKI_SECTION
- COMMUNITY, TOPIC, ENTITY, CONCEPT_CANDIDATE 是 ontology 定义，但 backend 尚未实现；
  对不支持的 NodeType，get_node() 返回 None，get_graph() 返回空图
- GraphRepository 是 lab/internal 层，当前仅在测试中使用

图建模原则（详见 ADR-006）：
- ai_draft / human_approved 是 Card 的 status property，不是独立 NodeType
- ApprovalDecision 是 card 状态转换记录，不是独立图节点
- Entity 独立于 Card：一张 Card 可 mention 多个 Entity，一个 Entity 可被多张 Card mention
- 所有 edge 必须有 evidence/reason/provenance
- Candidate edge 和 fact edge 必须区分
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class NodeType(str, enum.Enum):
    """图节点类型 — v3.7 ontology v1（ADR-006）。

    中文学习型说明：只有具备稳定身份（stable identity）、可被引用、
    可被用户理解的对象才适合作为 node。纯状态字段（如 card.status）、
    临时计算中间结果（如单次 query）、UI-only grouping 不应该是节点。

    当前正式支持（backend 已实现）:
      CARD, SOURCE, WIKI_SECTION, TAG

    Ontology 定义但 backend 尚未实现（lab/planned）:
      COMMUNITY, TOPIC, ENTITY, CONCEPT_CANDIDATE
    """

    # ── Fact Graph Nodes ──────────────────────────
    CARD = "card"
    """知识卡片（human_approved 状态）。ai_draft 卡片仍使用 CARD 类型，
    但不出现在 fact graph 中 — status 是 card 的 property，不是独立 NodeType。"""

    SOURCE = "source"
    """源文档节点。有 path-based identity，与 Card 是 1:N 的 DERIVED_FROM 关系。"""

    WIKI_SECTION = "wiki_section"
    """Wiki 章节。有 stable id（section title/hash），被 Card 通过 IN_SECTION 引用。"""

    TAG = "tag"
    """用户标签。有 stable name identity，跨 card/source 共享，通过 HAS_TAG 连接。"""

    COMMUNITY = "community"
    """确定性知识社区（v3.7 新增）。
    由 community.py 基于共享 source/tag/wiki_section 的确定性分组结果。
    拥有 evidence trail 和 representative cards，可被引用和导航。"""

    TOPIC = "topic"
    """确定性知识主题（v3.7 新增）。
    由 topic.py 合并重叠社区的结果，覆盖更宽泛的知识领域。
    通过 INCLUDES 连接其成员 Community。"""

    ENTITY = "entity"
    """用户确认的语义实体（v3.7 新增）。
    独立于 Card 存在：多张 Card 可以 mention 同一个 Entity。
    由 ConceptCandidate 经用户显式确认后升级而来。
    拥有 canonical label 和 alias set。"""

    # ── Candidate Graph Nodes ─────────────────────
    CONCEPT_CANDIDATE = "concept_candidate"
    """自动检测的候选实体（v3.7 重命名，原 CONCEPT）。
    由确定性规则从 card title/tags/body 中提取。
    不能自动升级为 ENTITY — 需用户显式确认。
    属于 candidate graph，不是 fact graph。"""


class EdgeType(str, enum.Enum):
    """图边类型 — v3.7 ontology v1（ADR-006）。

    中文学习型说明：每条边必须表达真实语义，不能只有 RELATED_TO。
    边必须有 type、direction、evidence/reason/provenance。
    Candidate edge（带 _CANDIDATE 后缀）属于 candidate graph，
    需用户确认后才能进入 fact graph。

    v3.7 变更：
    - 新增: HAS_TAG, IN_SECTION, CONTAINS, INCLUDES,
            MENTIONS_CANDIDATE, RESOLVES_TO, BELONGS_TO_TOPIC
    - 移除: APPROVAL_STATE_OF（Approval 是 card 状态转换，不是图边关系）
    """

    # ── Fact Graph Edges — Card ↔ Source/Wiki/Tag ─
    DERIVED_FROM = "derived_from"
    """Card → Source：卡片从源文档派生。evidence = source_id。"""

    HAS_TAG = "has_tag"
    """Card → Tag：卡片被标签标记。evidence = card.tags 字段。v3.7 新增。"""

    IN_SECTION = "in_section"
    """Card → WikiSection：卡片属于 Wiki 章节。evidence = card.wiki_sections 字段。v3.7 新增。"""

    # ── Fact Graph Edges — Card ↔ Card ────────────
    SHARES_TAG = "shares_tag"
    """Card ↔ Card：共享至少一个 tag。evidence = shared tag names。"""

    RELATED_BY_SOURCE = "related_by_source"
    """Card ↔ Card：来自同一 source document。evidence = shared source_id。"""

    RELATED_BY_WIKI_SECTION = "related_by_wiki_section"
    """Card ↔ Card：属于同一 Wiki section。evidence = shared wiki_section。"""

    SIMILAR_TITLE_OR_TERM = "similar_title_or_term"
    """Card ↔ Card：标题或关键术语相似。evidence = token overlap。"""

    LINKS_TO = "links_to"
    """Card → Card：用户人工创建的显式链接。evidence = user action。"""

    # ── Fact Graph Edges — Community / Topic 层次 ─
    CONTAINS = "contains"
    """Community → Card / Community → Source：社区包含成员。evidence = community membership。v3.7 新增。"""

    INCLUDES = "includes"
    """Topic → Community：主题包含子社区。evidence = overlap evidence。v3.7 新增。"""

    BELONGS_TO_TOPIC = "belongs_to_topic"
    """Card → Topic：卡片归属某个知识主题。evidence = community overlap。v3.7 新增。"""

    # ── Fact Graph Edges — Wiki ───────────────────
    WIKI_SECTION_REFERENCE = "wiki_section_reference"
    """Card → WikiSection：卡片内容引用 Wiki 章节。evidence = section title。"""

    # ── Candidate Graph Edges（需用户确认）─────────
    MENTIONS_CANDIDATE = "mentions_candidate"
    """Card → ConceptCandidate：卡片可能提及候选实体。
    evidence = token match / normalized label。
    属于 candidate graph — 需用户确认才能升级为 Card → Entity 关系。v3.7 新增。"""

    RESOLVES_TO = "resolves_to"
    """ConceptCandidate → Entity：候选实体解析为已确认实体。
    evidence = user confirmation。
    此为 candidate→fact 的桥接边。v3.7 新增。"""


# ── Relation Evidence ──────────────────────────────


@dataclass(frozen=True)
class RelationEvidence:
    """边关系的可解释证据。

    中文学习型说明：每条边必须携带 evidence，让用户理解"为什么这两者相关"。
    不做"相关度 85%"这种无解释的数字。evidence 文本是人类可读的溯源理由。

    detail 字典携带机器可读的结构化证据，供 API 和 UI 消费。
    """

    reason: str
    """人类可读的关系理由，如 'shared_tag'、'derived_from'。"""

    evidence: str
    """人类可读的证据描述，如 'shared tag: #machine-learning'。"""

    strength: float
    """关系强度 0.0-1.0，由确定性规则计算，非 LLM 生成。"""

    detail: dict = field(default_factory=dict)
    """结构化证据详情，包含 shared_entity_type、shared_entity_name 等字段。"""


# ── Graph Elements ─────────────────────────────────


@dataclass(frozen=True)
class GraphNode:
    """图中的节点。

    v3.7 升级：新增 card_count 用于 Source/Tag/Community/Topic 等聚合节点，
    表示该节点包含/关联的卡片数量。
    """

    id: str
    """节点唯一标识符。对于 Card 是 card.id，对于 Tag 是 tag name，对于 Entity 是 entity id。"""

    type: NodeType
    """节点类型，决定节点在 graph view 中的视觉呈现和交互语义。"""

    label: str
    """人类可读的显示标签。"""

    href: str | None = None
    """可选的导航链接（如 /library?card=xxx）。"""

    card_count: int = 0
    """关联卡片数（Source/Tag/Community/Topic 等聚合节点使用）。"""


@dataclass(frozen=True)
class GraphEdge:
    """图中的有向边，附带可解释证据。

    中文学习型说明：每条边有确定的方向（source → target），
    除非 edge_type 明确标记为 symmetric（如 SHARES_TAG）。
    evidence 字段携带 RelationEvidence，使用户可追溯关系来源。
    """

    source_id: str
    """边的源节点 ID。"""

    target_id: str
    """边的目标节点 ID。"""

    edge_type: EdgeType
    """边类型，决定边的视觉样式和语义含义。"""

    evidence: RelationEvidence
    """可解释的关系证据。非 LLM 生成，由确定性规则计算。"""


# ── Graph ──────────────────────────────────────────


@dataclass(frozen=True)
class Graph:
    """以某个节点为中心的知识图谱（subgraph）。

    中文学习型说明：Graph 是图查询的返回单位。与 LocalGraph 的区别：
    - LocalGraph 固定 1-hop，用于卡片详情侧边栏
    - Graph 支持 depth 参数（1-hop / 2-hop），用于 graph-first discovery 主界面
    - Graph 的每条边附带 RelationEvidence，LocalGraph 只有 reason 字符串

    v3.7 升级：center_type 支持当前已实现的 4 种 NodeType（CARD/SOURCE/TAG/WIKI_SECTION）。
    """

    center_id: str
    """中心节点 ID。"""

    center_type: NodeType
    """中心节点类型。v3.7 支持所有 NodeType。"""

    depth: int
    """图深度（1 = 仅邻居, 2 = 邻居的邻居）。"""

    nodes: tuple[GraphNode, ...]
    """图中所有节点（包含中心节点）。"""

    edges: tuple[GraphEdge, ...]
    """图中所有边。每条边附带 RelationEvidence。"""


__all__ = [
    "NodeType",
    "EdgeType",
    "RelationEvidence",
    "GraphNode",
    "GraphEdge",
    "Graph",
]
