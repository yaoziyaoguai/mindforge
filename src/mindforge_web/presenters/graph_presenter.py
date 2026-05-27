"""Graph response builders — 将内部模型转换为 Web API response。

中文学习型说明：此模块包含 local graph 和 full graph 两类 response 构造函数。
两者都从 core 层的图模型（LocalGraph / GraphResult / GraphNode / GraphEdge）
转换为 mindforge_web.schemas 中的 Pydantic response 类型。

所有函数都是纯数据变换，无 IO，无副作用。
"""

from __future__ import annotations

from mindforge.cards import iter_cards
from mindforge.config import MindForgeConfig
from mindforge.library_service import LibraryLookupError, show_library_card
from mindforge.relations.graph_builder import DeterministicGraphBuilder
from mindforge.relations.graph_models import (
    Graph as GraphResult,
    GraphEdge,
    GraphNode,
)
from mindforge.relations.local_graph import LocalGraph, NodeType
from mindforge_web.presenters.shared import get_relation_reason_label
from mindforge_web.schemas import (
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    LocalGraphEdgeResponse,
    LocalGraphNodeResponse,
    LocalGraphResponse,
    RelationEvidenceResponse,
)


def build_local_graph_response(graph: LocalGraph) -> LocalGraphResponse:
    section_card_counts: dict[str, int] = {}
    for edge in graph.edges:
        if edge.reason == "same_wiki_section":
            section_card_counts[edge.target_id] = section_card_counts.get(edge.target_id, 0) + 1

    return LocalGraphResponse(
        center_id=graph.center_id,
        center_type=graph.center_type.value,
        nodes=[
            LocalGraphNodeResponse(
                id=node.id,
                type=node.type.value,
                label=node.label,
                href=node.href,
                card_count=section_card_counts.get(node.id) if node.type == NodeType.WIKI_SECTION else None,
            )
            for node in graph.nodes
        ],
        edges=[
            LocalGraphEdgeResponse(
                source_id=edge.source_id,
                target_id=edge.target_id,
                reason=edge.reason,
                label=get_relation_reason_label(edge.reason),
            )
            for edge in graph.edges
        ],
    )


def build_graph_response(graph: GraphResult) -> GraphResponse:
    """将内部 Graph 转换为 API response。"""
    return GraphResponse(
        center_id=graph.center_id,
        center_type=graph.center_type.value,
        depth=graph.depth,
        nodes=[build_graph_node_response(n) for n in graph.nodes],
        edges=[build_graph_edge_response(e) for e in graph.edges],
    )


def build_graph_node_response(node: GraphNode) -> GraphNodeResponse:
    return GraphNodeResponse(
        id=node.id,
        type=node.type.value,
        label=node.label,
        href=node.href,
        card_count=node.card_count,
    )


def build_graph_edge_response(edge: GraphEdge) -> GraphEdgeResponse:
    return GraphEdgeResponse(
        source_id=edge.source_id,
        target_id=edge.target_id,
        edge_type=edge.edge_type.value,
        evidence=RelationEvidenceResponse(
            reason=edge.evidence.reason,
            evidence=edge.evidence.evidence,
            strength=edge.evidence.strength,
            detail=edge.evidence.detail,
        ),
    )


def build_graph_builder(cfg: MindForgeConfig) -> DeterministicGraphBuilder | None:
    """从 vault 中所有 approved cards 构建 DeterministicGraphBuilder。"""
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved = [card for card in scan.cards if card.status == "human_approved"]
    if not approved:
        return None
    from mindforge_web.presenters.shared import make_relation_record

    records = [make_relation_record(card) for card in approved]
    return DeterministicGraphBuilder(records)


def resolve_card_id(cfg: MindForgeConfig, ref: str) -> str | None:
    """将用户输入的 ref 解析为卡片 id。"""
    detail = show_library_card(cfg, ref, show_content=False)
    if isinstance(detail, LibraryLookupError):
        return None
    return detail.card.summary.id or detail.card.summary.rel_path


def get_graph_neighbor_count(
    builder: DeterministicGraphBuilder | None,
    card_id: str,
) -> int | None:
    """获取卡片 1-hop 邻居数量（轻量，不做 full 2-hop build）。"""
    if builder is None:
        return None
    try:
        edges = builder.get_edges(card_id, direction="outgoing")
        neighbor_ids = {e.target_id for e in edges}
        return len(neighbor_ids)
    except Exception:
        return None
