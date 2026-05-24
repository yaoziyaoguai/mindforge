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

    v2.1: reasoning 提供确定性可解释文本，estimated_token_count 估计上下文大小。
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
    # v2.1
    reasoning: str = ""
    """确定性可解释文本：为什么这些卡片/标签/Wiki 章节与中心卡片相关。"""
    estimated_token_count: int = 0
    """粗略的 token 估计（不调用 LLM），帮助 UI 判断上下文规模。"""


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

    reasoning = _build_reasoning(
        center_title=center_title,
        direct_count=len(direct_matches),
        neighbor_count=len(neighbor_cards),
        tag_count=len(shared_tags),
        source_count=len(shared_sources),
        section_count=len(wiki_sections),
        community_count=len(communities),
    )
    token_estimate = _estimate_token_count(
        center_title=center_title,
        direct_matches=direct_matches,
        neighbor_cards=neighbor_cards,
        communities=communities,
    )

    return DiscoveryContext(
        center_card_id=graph.center_id,
        center_card_title=center_title,
        direct_matches=tuple(direct_matches),
        neighbor_cards=tuple(neighbor_cards),
        wiki_sections=tuple(wiki_sections),
        shared_tags=tuple(shared_tags),
        shared_sources=tuple(shared_sources),
        communities=communities,
        reasoning=reasoning,
        estimated_token_count=token_estimate,
    )


def _build_reasoning(
    *,
    center_title: str,
    direct_count: int,
    neighbor_count: int,
    tag_count: int,
    source_count: int,
    section_count: int,
    community_count: int,
) -> str:
    """生成确定性可解释文本（v2.1）。

    不调用 LLM，纯基于计数的确定性描述。
    帮助用户理解"为什么这些内容是相关的"。
    """
    parts: list[str] = [f"中心卡片「{center_title}」"]

    rel_parts: list[str] = []
    if direct_count > 0:
        rel_parts.append(f"{direct_count} 个直接关联")
    if neighbor_count > 0:
        rel_parts.append(f"{neighbor_count} 个间接关联")
    if rel_parts:
        parts.append(f"通过{'、'.join(rel_parts)}连接到知识图谱")

    shared_parts: list[str] = []
    if source_count > 0:
        shared_parts.append(f"{source_count} 个来源")
    if tag_count > 0:
        shared_parts.append(f"{tag_count} 个标签")
    if section_count > 0:
        shared_parts.append(f"{section_count} 个 Wiki 章节")
    if shared_parts:
        parts.append(f"共享{'、'.join(shared_parts)}")

    if community_count > 0:
        parts.append(f"属于 {community_count} 个知识社区")

    return "。".join(parts) + "。"


def _estimate_token_count(
    *,
    center_title: str,
    direct_matches: list[DiscoveryCardRef],
    neighbor_cards: list[DiscoveryCardRef],
    communities: tuple[DiscoveryCommunityRef, ...],
) -> int:
    """粗略 token 估计（v2.1）。

    不调用 LLM，也不使用 tiktoken。基于字符数的启发式估计：
    - 中文字符 ≈ 0.7 token/char
    - 英文/ASCII ≈ 0.25 token/char
    混合文本取折中：≈ 0.5 token/char。

    仅统计可见文本：标题、evidence、描述。
    """
    texts: list[str] = [center_title]
    for ref in direct_matches:
        texts.extend([ref.title, ref.evidence, ref.relation_reason])
    for ref in neighbor_cards:
        texts.extend([ref.title, ref.evidence, ref.relation_reason])
    for comm in communities:
        texts.append(comm.description)

    total_chars = sum(len(t) for t in texts)
    return max(1, int(total_chars * 0.5))


__all__ = [
    "DiscoveryCardRef",
    "DiscoverySectionRef",
    "DiscoveryTagRef",
    "DiscoverySourceRef",
    "DiscoveryCommunityRef",
    "DiscoveryContext",
    "assemble_discovery_context",
]
