"""v0.6 Deterministic Graph Builder — 基于现有关系引擎的统一图构建器。

中文学习型说明：DeterministicGraphBuilder 是 GraphPort 的默认实现，
复用 compute_related_cards() 和 build_card_centered_graph() 的现有逻辑，
并将结果统一为带 RelationEvidence 的 Graph 数据结构。

核心升级：
- 1-hop → depth 参数支持 1-hop / 2-hop
- RelatedCardEdge → GraphEdge + RelationEvidence（每条边可解释）
- 支持从任意 NodeType 出发构建图（不只是 CARD）
- 不引入新依赖，纯 in-memory deterministic computation
"""

from __future__ import annotations

from collections import defaultdict

from mindforge.relations.graph_models import (
    EdgeType,
    Graph,
    GraphEdge,
    GraphNode,
    NodeType,
    RelationEvidence,
)
from mindforge.relations.graph_port import GraphPort
from mindforge.relations.local_graph import (
    GraphEdge as LocalGraphEdge,
    build_card_centered_graph,
    build_wiki_section_centered_graph,
    NodeType as LocalNodeType,
)
from mindforge.relations.related_cards import (
    RelationReason,
    compute_related_cards,
)

# ── Reason → EdgeType 映射 ─────────────────────────


_REASON_TO_EDGE_TYPE: dict[RelationReason, EdgeType] = {
    RelationReason.SAME_SOURCE: EdgeType.RELATED_BY_SOURCE,
    RelationReason.SAME_TAG: EdgeType.SHARES_TAG,
    RelationReason.SAME_WIKI_SECTION: EdgeType.RELATED_BY_WIKI_SECTION,
    RelationReason.SAME_REVIEW_BATCH: EdgeType.RELATED_BY_SOURCE,
    RelationReason.SOURCE_LOCATION_NEIGHBOR: EdgeType.RELATED_BY_SOURCE,
    RelationReason.MANUAL_LINK: EdgeType.MENTIONS,
}

# Edge type → strength weight (与 _STRENGTH 保持一致)
_EDGE_TYPE_STRENGTH: dict[EdgeType, float] = {
    EdgeType.RELATED_BY_SOURCE: 0.8,
    EdgeType.SHARES_TAG: 0.5,
    EdgeType.RELATED_BY_WIKI_SECTION: 0.7,
    EdgeType.WIKI_SECTION_REFERENCE: 0.7,
    EdgeType.MENTIONS: 1.0,
    EdgeType.SIMILAR_TITLE_OR_TERM: 0.4,
    EdgeType.LINKS_TO: 0.6,
    EdgeType.DERIVED_FROM: 0.8,
    EdgeType.APPROVAL_STATE_OF: 0.5,
}


class DeterministicGraphBuilder(GraphPort):
    """基于确定性规则的图构建器。

    使用方式：
        builder = DeterministicGraphBuilder(all_cards)
        graph = builder.get_graph("card_1", NodeType.CARD, depth=2)
    """

    def __init__(self, all_cards: list[dict[str, object]]) -> None:
        self._cards = all_cards
        self._cards_by_id: dict[str, dict[str, object]] = {
            str(c["id"]): c for c in all_cards
        }
        # 预建索引用数据（与 compute_related_cards 共享逻辑）
        self._source_index: dict[str, list[str]] = defaultdict(list)
        self._tag_index: dict[str, list[str]] = defaultdict(list)
        self._section_index: dict[str, list[str]] = defaultdict(list)
        for c in all_cards:
            cid = str(c["id"])
            sid = c.get("source_id")
            if sid:
                self._source_index[str(sid)].append(cid)
            for tag in (c.get("tags") or []):
                self._tag_index[str(tag)].append(cid)
            for sec in (c.get("wiki_sections") or []):
                self._section_index[str(sec)].append(cid)

    # ── GraphPort 实现 ───────────────────────────

    def get_node(self, node_id: str, node_type: NodeType) -> GraphNode | None:
        if node_type == NodeType.CARD:
            card = self._cards_by_id.get(node_id)
            if card is None:
                return None
            return GraphNode(
                id=node_id,
                type=NodeType.CARD,
                label=str(card.get("title", node_id)),
                href=f"/library?card={node_id}",
            )
        if node_type == NodeType.SOURCE:
            count = len(self._source_index.get(node_id, []))
            return GraphNode(
                id=node_id,
                type=NodeType.SOURCE,
                label=node_id,
                card_count=count,
            )
        if node_type == NodeType.TAG:
            count = len(self._tag_index.get(node_id, []))
            return GraphNode(
                id=node_id,
                type=NodeType.TAG,
                label=f"#{node_id}",
                card_count=count,
            )
        if node_type == NodeType.WIKI_SECTION:
            count = len(self._section_index.get(node_id, []))
            return GraphNode(
                id=node_id,
                type=NodeType.WIKI_SECTION,
                label=node_id,
                card_count=count,
            )
        return None

    def get_edges(
        self,
        node_id: str,
        *,
        edge_types: set[EdgeType] | None = None,
        direction: str = "both",
    ) -> list[GraphEdge]:
        if direction not in ("outgoing", "incoming", "both"):
            raise ValueError(f"invalid direction: {direction}")

        # 使用 compute_related_cards 获取所有关系
        raw_edges = compute_related_cards(node_id, self._cards, context="library")
        result: list[GraphEdge] = []
        for raw in raw_edges:
            et = _REASON_TO_EDGE_TYPE.get(raw.reason)
            if et is None:
                continue
            if edge_types is not None and et not in edge_types:
                continue
            evidence = RelationEvidence(
                reason=raw.reason.value,
                evidence=raw.reason_detail,
                strength=raw.strength,
            )
            if direction in ("outgoing", "both"):
                result.append(GraphEdge(
                    source_id=raw.source_card_id,
                    target_id=raw.target_card_id,
                    edge_type=et,
                    evidence=evidence,
                ))
            if direction in ("incoming", "both"):
                result.append(GraphEdge(
                    source_id=raw.target_card_id,
                    target_id=raw.source_card_id,
                    edge_type=et,
                    evidence=evidence,
                ))
        return result

    def get_graph(
        self,
        center_id: str,
        center_type: NodeType,
        *,
        depth: int = 2,
    ) -> Graph:
        if center_type == NodeType.CARD:
            return self._card_centered_graph(center_id, depth=depth)
        if center_type == NodeType.WIKI_SECTION:
            return self._wiki_section_centered_graph(center_id)
        if center_type == NodeType.SOURCE:
            return self._source_centered_graph(center_id, depth=depth)
        if center_type == NodeType.TAG:
            return self._tag_centered_graph(center_id, depth=depth)
        # fallback: 空图
        return Graph(
            center_id=center_id,
            center_type=center_type,
            depth=depth,
            nodes=(),
            edges=(),
        )

    def get_path(
        self,
        source_id: str,
        target_id: str,
        *,
        max_depth: int = 4,
    ) -> list[list[GraphEdge]]:
        # BFS 查找两节点间的最短路径（最多 max_depth 跳）
        if max_depth < 1:
            return []
        # 获取 source 的所有出边
        edges = self.get_edges(source_id, direction="outgoing")
        edge_by_target: dict[str, GraphEdge] = {}
        for e in edges:
            if e.target_id not in edge_by_target:
                edge_by_target[e.target_id] = e

        if target_id in edge_by_target:
            return [[edge_by_target[target_id]]]

        if max_depth > 1:
            for neighbor_id in edge_by_target:
                sub_paths = self.get_path(neighbor_id, target_id, max_depth=max_depth - 1)
                if sub_paths:
                    return [[edge_by_target[neighbor_id]] + sp for sp in sub_paths]
        return []

    # ── 内部构建方法 ──────────────────────────────

    def _card_centered_graph(self, card_id: str, *, depth: int) -> Graph:
        """构建以卡片为中心的 1-hop 或 2-hop graph。"""
        # 1-hop: 复用现有 local_graph
        lg = build_card_centered_graph(card_id, self._cards)

        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        # 转换 LocalGraph nodes
        for gn in lg.nodes:
            nodes[gn.id] = GraphNode(
                id=gn.id,
                type=_map_node_type(gn.type),
                label=gn.label,
                href=gn.href,
            )

        # 转换 LocalGraph edges 为 GraphEdge（附带 evidence）
        for ge in lg.edges:
            edge = self._local_graph_edge_to_graph_edge(ge, card_id)
            edges.append(edge)

        # 2-hop: 对每个邻居卡片计算其关系并合并
        if depth >= 2:
            neighbor_card_ids = [
                n.id for n in lg.nodes
                if _map_node_type(n.type) == NodeType.CARD and n.id != card_id
            ]
            for neighbor_id in neighbor_card_ids:
                neighbor_edges = compute_related_cards(
                    neighbor_id, self._cards, context="library"
                )
                for raw in neighbor_edges:
                    et = _REASON_TO_EDGE_TYPE.get(raw.reason)
                    if et is None:
                        continue
                    # 添加邻居节点（如果尚未存在）
                    target_id = raw.target_card_id
                    if target_id not in nodes:
                        target_card = self._cards_by_id.get(target_id)
                        if target_card:
                            nodes[target_id] = GraphNode(
                                id=target_id,
                                type=NodeType.CARD,
                                label=str(target_card.get("title", target_id)),
                                href=f"/library?card={target_id}",
                            )
                    evidence = RelationEvidence(
                        reason=raw.reason.value,
                        evidence=raw.reason_detail,
                        strength=raw.strength,
                    )
                    edges.append(GraphEdge(
                        source_id=neighbor_id,
                        target_id=target_id,
                        edge_type=et,
                        evidence=evidence,
                    ))

        return Graph(
            center_id=card_id,
            center_type=NodeType.CARD,
            depth=depth,
            nodes=tuple(nodes.values()),
            edges=tuple(edges),
        )

    def _wiki_section_centered_graph(self, section: str) -> Graph:
        """构建以 Wiki section 为中心的图。复用现有 build_wiki_section_centered_graph。"""
        lg = build_wiki_section_centered_graph(section, self._cards)

        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        for gn in lg.nodes:
            nodes[gn.id] = GraphNode(
                id=gn.id,
                type=_map_node_type(gn.type),
                label=gn.label,
                href=gn.href,
            )

        for ge in lg.edges:
            edge = self._local_graph_edge_to_graph_edge(ge, section)
            edges.append(edge)

        return Graph(
            center_id=section,
            center_type=NodeType.WIKI_SECTION,
            depth=1,
            nodes=tuple(nodes.values()),
            edges=tuple(edges),
        )

    def _source_centered_graph(self, source_id: str, *, depth: int) -> Graph:
        """构建以 Source 为中心的图。"""
        card_ids = self._source_index.get(source_id, [])
        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        # source node
        nodes[source_id] = GraphNode(
            id=source_id,
            type=NodeType.SOURCE,
            label=source_id,
            card_count=len(card_ids),
        )

        for cid in card_ids:
            card = self._cards_by_id.get(cid)
            if card is None:
                continue
            nodes[cid] = GraphNode(
                id=cid,
                type=NodeType.CARD,
                label=str(card.get("title", cid)),
                href=f"/library?card={cid}",
            )
            # DERIVED_FROM edge: Card → Source
            edges.append(GraphEdge(
                source_id=cid,
                target_id=source_id,
                edge_type=EdgeType.DERIVED_FROM,
                evidence=RelationEvidence(
                    reason="derived_from",
                    evidence=f"card derived from source: {source_id}",
                    strength=0.8,
                ),
            ))
            # RELATED_BY_SOURCE edges between cards
            for other_cid in card_ids:
                if other_cid <= cid:
                    continue  # 避免重复
                edges.append(GraphEdge(
                    source_id=cid,
                    target_id=other_cid,
                    edge_type=EdgeType.RELATED_BY_SOURCE,
                    evidence=RelationEvidence(
                        reason="related_by_source",
                        evidence=f"same source: {source_id}",
                        strength=0.8,
                    ),
                ))

        return Graph(
            center_id=source_id,
            center_type=NodeType.SOURCE,
            depth=depth,
            nodes=tuple(nodes.values()),
            edges=tuple(edges),
        )

    def _tag_centered_graph(self, tag: str, *, depth: int) -> Graph:
        """构建以 Tag 为中心的图。"""
        card_ids = self._tag_index.get(tag, [])
        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        nodes[tag] = GraphNode(
            id=tag,
            type=NodeType.TAG,
            label=f"#{tag}",
            card_count=len(card_ids),
        )

        for cid in card_ids:
            card = self._cards_by_id.get(cid)
            if card is None:
                continue
            nodes[cid] = GraphNode(
                id=cid,
                type=NodeType.CARD,
                label=str(card.get("title", cid)),
                href=f"/library?card={cid}",
            )
            edges.append(GraphEdge(
                source_id=cid,
                target_id=tag,
                edge_type=EdgeType.SHARES_TAG,
                evidence=RelationEvidence(
                    reason="shared_tag",
                    evidence=f"shared tag: {tag}",
                    strength=0.5,
                ),
            ))

        return Graph(
            center_id=tag,
            center_type=NodeType.TAG,
            depth=depth,
            nodes=tuple(nodes.values()),
            edges=tuple(edges),
        )

    # ── 辅助 ──────────────────────────────────────

    def _local_graph_edge_to_graph_edge(
        self,
        ge: LocalGraphEdge,
        center_id: str,
    ) -> GraphEdge:
        """将 LocalGraphEdge 转换为带 evidence 的 GraphEdge。"""
        reason_map: dict[str, tuple[EdgeType, str, float]] = {
            "same_source": (EdgeType.RELATED_BY_SOURCE, "same_source_document", 0.8),
            "same_tag": (EdgeType.SHARES_TAG, "shared_tag", 0.5),
            "same_wiki_section": (EdgeType.RELATED_BY_WIKI_SECTION, "same_wiki_section", 0.7),
            "wiki_section_reference": (
                EdgeType.WIKI_SECTION_REFERENCE, "wiki_section_reference", 0.7
            ),
        }
        et, reason_key, strength = reason_map.get(
            ge.reason,
            (EdgeType.RELATED_BY_SOURCE, ge.reason, 0.5),
        )
        return GraphEdge(
            source_id=ge.source_id,
            target_id=ge.target_id,
            edge_type=et,
            evidence=RelationEvidence(
                reason=reason_key,
                evidence=f"{ge.reason}: {center_id} ↔ {ge.target_id}",
                strength=strength,
            ),
        )


def _map_node_type(nt: LocalNodeType) -> NodeType:
    """将 local_graph.NodeType 映射到 graph_models.NodeType。"""
    mapping = {
        "card": NodeType.CARD,
        "source": NodeType.SOURCE,
        "wiki_section": NodeType.WIKI_SECTION,
        "tag": NodeType.TAG,
    }
    return mapping.get(nt.value, NodeType.CARD)


__all__ = ["DeterministicGraphBuilder"]
