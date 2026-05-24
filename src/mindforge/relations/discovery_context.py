"""v0.6 Discovery Context — 图感知的检索/发现上下文组装器（非 RAG）。

中文学习型说明：DiscoveryContext 是 graph-first discovery 的 context assembly 层。
它从 DeterministicGraphBuilder 获取图数据，然后将图数据重组为面向 discovery UI
的结构化上下文。不调用 LLM、不做 embedding、不做 RAG answering。
"""

from __future__ import annotations

from dataclasses import dataclass

from mindforge.relations.graph_models import Graph, NodeType


@dataclass(frozen=True)
class DiscoveryCardRef:
    """发现上下文中引用的卡片引用。"""
    card_id: str
    title: str
    relation_reason: str  # e.g. "same_source_document", "shared_tag"
    relation_strength: float
    evidence: str


@dataclass(frozen=True)
class DiscoverySectionRef:
    """发现上下文中引用的 Wiki section。"""
    section_title: str
    card_count: int


@dataclass(frozen=True)
class DiscoveryTagRef:
    """发现上下文中引用的 Tag。"""
    tag: str
    card_count: int


@dataclass(frozen=True)
class DiscoverySourceRef:
    """发现上下文中引用的 Source。"""
    source_id: str
    card_count: int


@dataclass(frozen=True)
class DiscoveryCommunityRef:
    """发现上下文中引用的知识社区。"""
    community_type: str  # "source", "tag", "wiki_section"
    shared_entity: str
    member_count: int
    description: str


@dataclass(frozen=True)
class DiscoveryContext:
    """图感知的发现上下文。

    每个字段都是 deterministic 计算的结果，每条 relation 可解释。
    这是给 discovery UI 的结构化数据，不是给 LLM 的 prompt context。
    """
    center_card_id: str
    center_card_title: str
    direct_matches: tuple[DiscoveryCardRef, ...] = ()
    """与中心卡片直接相关的卡片（1-hop 邻居）。"""
    neighbor_cards: tuple[DiscoveryCardRef, ...] = ()
    """2-hop 邻居卡片（邻居的邻居，排除中心卡片和 1-hop 邻居）。"""
    wiki_sections: tuple[DiscoverySectionRef, ...] = ()
    """卡片所属或相关的 wiki sections。"""
    shared_tags: tuple[DiscoveryTagRef, ...] = ()
    """中心卡片涉及的 tags 及其覆盖卡片数。"""
    shared_sources: tuple[DiscoverySourceRef, ...] = ()
    """中心卡片涉及的 sources 及其覆盖卡片数。"""
    communities: tuple[DiscoveryCommunityRef, ...] = ()
    """中心卡片所属的知识社区（source/tag/wiki_section 分组）。"""


def assemble_discovery_context(
    graph: Graph,
    *,
    communities: tuple[DiscoveryCommunityRef, ...] = (),
) -> DiscoveryContext:
    """从图数据组装发现上下文。

    中文学习型说明：此函数负责将 Graph 数据结构重组为 DiscoveryContext。
    它不构建图（图构建由 GraphBuilder 负责），只做数据转换和聚合。
    这是 deterministic 的纯函数：相同输入 → 相同输出。

    额外接受 knowledge communities（由外部 detect_communities 产出），
    以保持此函数仍是 Graph 的纯函数。
    """
    center_node = next(
        (n for n in graph.nodes if n.id == graph.center_id and n.type == NodeType.CARD),
        None,
    )
    center_title = center_node.label if center_node else graph.center_id

    # 分类节点
    card_nodes = [n for n in graph.nodes if n.type == NodeType.CARD and n.id != graph.center_id]
    section_nodes = [n for n in graph.nodes if n.type == NodeType.WIKI_SECTION]
    tag_nodes = [n for n in graph.nodes if n.type == NodeType.TAG]
    source_nodes = [n for n in graph.nodes if n.type == NodeType.SOURCE]

    # 构建 edge lookup: (source, target) → edge
    edge_map: dict[tuple[str, str], object] = {}
    for e in graph.edges:
        key = (e.source_id, e.target_id)
        if key not in edge_map:
            edge_map[key] = e

    # 1-hop 邻居卡片（与 center 有直接边的卡片）
    center_neighbor_ids: set[str] = set()
    direct_matches: list[DiscoveryCardRef] = []
    for card in card_nodes:
        edge_fwd = edge_map.get((graph.center_id, card.id))
        edge_rev = edge_map.get((card.id, graph.center_id))
        edge = edge_fwd or edge_rev
        if edge:
            center_neighbor_ids.add(card.id)
            direct_matches.append(DiscoveryCardRef(
                card_id=card.id,
                title=card.label,
                relation_reason=edge.evidence.reason,
                relation_strength=edge.evidence.strength,
                evidence=edge.evidence.evidence,
            ))

    # 2-hop 邻居卡片（与 1-hop 邻居有边，但不是 center 也不是 1-hop 邻居）
    neighbor_cards: list[DiscoveryCardRef] = []
    seen_neighbor_ids: set[str] = set()
    for card in card_nodes:
        if card.id in center_neighbor_ids:
            continue
        # 检查是否与任何 1-hop 邻居有边
        for neighbor_id in center_neighbor_ids:
            edge_fwd = edge_map.get((neighbor_id, card.id))
            edge_rev = edge_map.get((card.id, neighbor_id))
            edge = edge_fwd or edge_rev
            if edge and card.id not in seen_neighbor_ids:
                seen_neighbor_ids.add(card.id)
                neighbor_cards.append(DiscoveryCardRef(
                    card_id=card.id,
                    title=card.label,
                    relation_reason=f"via {neighbor_id}: {edge.evidence.reason}",
                    relation_strength=edge.evidence.strength * 0.8,  # 2-hop 衰减
                    evidence=edge.evidence.evidence,
                ))
                break

    # Wiki sections
    wiki_sections = [
        DiscoverySectionRef(section_title=n.label, card_count=n.card_count or 0)
        for n in section_nodes
    ]

    # Shared tags（排除纯文本 "#tag" 格式的标签节点，仅保留有 card_count 的）
    shared_tags = [
        DiscoveryTagRef(tag=n.label.lstrip("#"), card_count=n.card_count or 0)
        for n in tag_nodes
    ]

    # Shared sources
    shared_sources = [
        DiscoverySourceRef(source_id=n.id, card_count=n.card_count or 0)
        for n in source_nodes
    ]

    return DiscoveryContext(
        center_card_id=graph.center_id,
        center_card_title=center_title,
        direct_matches=tuple(direct_matches),
        neighbor_cards=tuple(neighbor_cards),
        wiki_sections=tuple(wiki_sections),
        shared_tags=tuple(shared_tags),
        shared_sources=tuple(shared_sources),
        communities=communities,
    )


__all__ = [
    "DiscoveryCardRef",
    "DiscoverySectionRef",
    "DiscoveryTagRef",
    "DiscoverySourceRef",
    "DiscoveryCommunityRef",
    "DiscoveryContext",
    "assemble_discovery_context",
]
