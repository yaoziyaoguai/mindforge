"""v0.6 Graph Domain Models — 统一图数据结构。

中文学习型说明：本模块定义了 MindForge 知识图谱的通用数据类型。
Node/Edge/RelationEvidence/Graph 是 GraphPort 和 GraphBuilder 的共享合约，
不依赖具体存储实现（in-memory / Kuzu / SQLite FTS 等）。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class NodeType(str, enum.Enum):
    """图节点类型 — 知识图谱中的实体类别。"""
    CARD = "card"
    SOURCE = "source"
    WIKI_SECTION = "wiki_section"
    TAG = "tag"
    CONCEPT = "concept"


class EdgeType(str, enum.Enum):
    """图边类型 — 节点间关系的语义类别。

    每条边必须有确定的 relation reason，不可有黑盒相似度。
    """
    DERIVED_FROM = "derived_from"
    MENTIONS = "mentions"
    SHARES_TAG = "shares_tag"
    RELATED_BY_SOURCE = "related_by_source"
    RELATED_BY_WIKI_SECTION = "related_by_wiki_section"
    SIMILAR_TITLE_OR_TERM = "similar_title_or_term"
    APPROVAL_STATE_OF = "approval_state_of"
    LINKS_TO = "links_to"
    WIKI_SECTION_REFERENCE = "wiki_section_reference"


# ── Relation Evidence ──────────────────────────────


@dataclass(frozen=True)
class RelationEvidence:
    """边关系的可解释证据。

    每条边必须携带 evidence，让用户理解"为什么这两张卡片相关"。
    不做"相关度 85%"这种无解释的数字。
    """
    reason: str
    evidence: str
    strength: float
    detail: dict = field(default_factory=dict)


# ── Graph Elements ─────────────────────────────────


@dataclass(frozen=True)
class GraphNode:
    """图中的节点。"""
    id: str
    type: NodeType
    label: str
    href: str | None = None
    card_count: int = 0


@dataclass(frozen=True)
class GraphEdge:
    """图中的有向边，附带可解释证据。"""
    source_id: str
    target_id: str
    edge_type: EdgeType
    evidence: RelationEvidence


# ── Graph ──────────────────────────────────────────


@dataclass(frozen=True)
class Graph:
    """以某个节点为中心的知识图谱。

    与 LocalGraph 的区别：
    - LocalGraph 固定 1-hop，用于卡片详情侧边栏
    - Graph 支持 depth 参数，用于 graph-first discovery 主界面
    - Graph 的每条边附带 RelationEvidence，LocalGraph 只有 reason 字符串
    """
    center_id: str
    center_type: NodeType
    depth: int
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


__all__ = [
    "NodeType",
    "EdgeType",
    "RelationEvidence",
    "GraphNode",
    "GraphEdge",
    "Graph",
]
