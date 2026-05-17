"""M6 Local Graph Preview — SDD §10, TDD §7。

确定性 in-memory graph construction：1-hop neighbors only。
不做 force-directed graph，不依赖 canvas/graph DB/d3/NetworkX。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from collections import defaultdict


class NodeType(str, enum.Enum):
    CARD = "card"
    SOURCE = "source"
    WIKI_SECTION = "wiki_section"
    TAG = "tag"


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: NodeType
    label: str
    href: str | None = None


@dataclass(frozen=True)
class GraphEdge:
    source_id: str
    target_id: str
    reason: str  # same_source, same_tag, same_wiki_section


LocalGraphNode = GraphNode
LocalGraphEdge = GraphEdge


@dataclass(frozen=True)
class LocalGraph:
    center_id: str
    center_type: NodeType
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


def build_card_centered_graph(
    card_id: str,
    all_cards: list[dict[str, object]],
) -> LocalGraph:
    """构建以一张卡片为中心的 1-hop local graph。

    节点类型：card, source, wiki_section, tag
    边类型：same_source, same_tag, same_wiki_section
    """
    center = _find(card_id, all_cards)
    if center is None:
        return LocalGraph(
            center_id=card_id,
            center_type=NodeType.CARD,
            nodes=(),
            edges=(),
        )

    center_src = center.get("source_id")
    center_tags = set(center.get("tags") or [])
    center_sections = set(center.get("wiki_sections") or [])

    # Pre-build indexes
    source_index: dict[str, list[str]] = defaultdict(list)
    tag_index: dict[str, list[str]] = defaultdict(list)
    section_index: dict[str, list[str]] = defaultdict(list)

    for c in all_cards:
        cid = str(c["id"])
        sid = c.get("source_id")
        if sid:
            source_index[str(sid)].append(cid)
        for tag in (c.get("tags") or []):
            tag_index[str(tag)].append(cid)
        for sec in (c.get("wiki_sections") or []):
            section_index[str(sec)].append(cid)

    # Collect nodes and edges
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    # Center card node
    center_label = str(center.get("title", card_id))
    nodes[card_id] = GraphNode(
        id=card_id, type=NodeType.CARD,
        label=center_label,
        href=f"/library?card={card_id}",
    )

    def add_card_node(cid: str) -> None:
        if cid in nodes:
            return
        card = _find(cid, all_cards)
        label = str(card["title"]) if card and card.get("title") else cid
        nodes[cid] = GraphNode(
            id=cid, type=NodeType.CARD,
            label=label,
            href=f"/library?card={cid}",
        )

    # same_source → edges to neighbor cards + source node
    if center_src:
        src_key = str(center_src)
        nodes[src_key] = GraphNode(
            id=src_key, type=NodeType.SOURCE,
            label=src_key,
        )
        edges.append(GraphEdge(source_id=card_id, target_id=src_key, reason="same_source"))
        for target in source_index.get(src_key, []):
            if target != card_id:
                add_card_node(target)
                edges.append(GraphEdge(source_id=card_id, target_id=target, reason="same_source"))

    # same_tag → edges to neighbor cards + tag nodes
    for tag in center_tags:
        tag_key = str(tag)
        nodes[tag_key] = GraphNode(
            id=tag_key, type=NodeType.TAG,
            label=f"#{tag_key}",
        )
        edges.append(GraphEdge(source_id=card_id, target_id=tag_key, reason="same_tag"))
        for target in tag_index.get(tag_key, []):
            if target != card_id:
                add_card_node(target)
                edges.append(GraphEdge(source_id=card_id, target_id=target, reason="same_tag"))

    # same_wiki_section → edges to neighbor cards + section nodes
    for sec in center_sections:
        sec_key = str(sec)
        nodes[sec_key] = GraphNode(
            id=sec_key, type=NodeType.WIKI_SECTION,
            label=sec_key,
        )
        edges.append(GraphEdge(source_id=card_id, target_id=sec_key, reason="same_wiki_section"))
        for target in section_index.get(sec_key, []):
            if target != card_id:
                add_card_node(target)
                edges.append(GraphEdge(source_id=card_id, target_id=target, reason="same_wiki_section"))

    return LocalGraph(
        center_id=card_id,
        center_type=NodeType.CARD,
        nodes=tuple(nodes.values()),
        edges=tuple(edges),
    )


def build_wiki_section_centered_graph(
    section: str,
    all_cards: list[dict[str, object]],
) -> LocalGraph:
    """构建以 Wiki section 为中心的 1-hop local graph。

    中文学习型说明：section-centered graph 是 Wiki 页面的最低可见入口。
    它只用卡片摘要中的 wiki_sections/source_id/tags 字段，不读取 Wiki 或
    source 正文，也不构建全局 graph。
    """

    nodes: dict[str, GraphNode] = {
        section: GraphNode(
            id=section,
            type=NodeType.WIKI_SECTION,
            label=section,
            href=f"/wiki#{section}",
        )
    }
    edges: list[GraphEdge] = []

    referenced = [
        card for card in all_cards
        if section in {str(item) for item in (card.get("wiki_sections") or [])}
    ]
    for card in referenced:
        card_id = str(card["id"])
        nodes[card_id] = GraphNode(
            id=card_id,
            type=NodeType.CARD,
            label=str(card.get("title") or card_id),
            href=f"/library?card={card_id}",
        )
        edges.append(GraphEdge(source_id=section, target_id=card_id, reason="wiki_section_reference"))

        source_id = card.get("source_id")
        if source_id:
            source_key = str(source_id)
            nodes[source_key] = GraphNode(id=source_key, type=NodeType.SOURCE, label=source_key)
            edges.append(GraphEdge(source_id=card_id, target_id=source_key, reason="same_source"))

        for tag in card.get("tags") or []:
            tag_key = str(tag)
            nodes[tag_key] = GraphNode(id=tag_key, type=NodeType.TAG, label=f"#{tag_key}")
            edges.append(GraphEdge(source_id=card_id, target_id=tag_key, reason="same_tag"))

    return LocalGraph(
        center_id=section,
        center_type=NodeType.WIKI_SECTION,
        nodes=tuple(nodes.values()),
        edges=tuple(edges),
    )


def _find(
    card_id: str,
    all_cards: list[dict[str, object]],
) -> dict[str, object] | None:
    for c in all_cards:
        if str(c["id"]) == card_id:
            return c
    return None
