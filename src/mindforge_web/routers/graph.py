"""v0.6 Graph API router — 可解释知识图谱端点。

中文学习型说明：Graph API 提供以节点为中心的图浏览和边查询能力。
每条边都携带 reason + evidence + strength，确保关系可解释。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from mindforge_web.deps import get_facade
from mindforge_web.presenters.web_errors import user_error
from mindforge_web.schemas import GraphEdgeDetailResponse, GraphResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/node", response_model=GraphResponse)
def graph_node(
    ref: str = Query(..., description="Card id, filename, or vault-relative path"),
    depth: int = Query(2, ge=1, le=3, description="Graph expansion depth (1-3)"),
    facade: WebFacade = Depends(get_facade),
) -> GraphResponse:
    """以卡片为中心的 1-hop 或 2-hop 可解释关系图。

    每条边包含 reason（关系类型）、evidence（关系证据）和 strength（强度）。
    """
    result = facade.get_graph_node(ref, depth=depth)
    if result is None:
        raise user_error(
            404, "graph_not_found", "未找到该节点的图数据。",
            "请确认卡片存在且已 approved。",
        )
    return result


@router.get("/explore", response_model=GraphResponse)
def graph_explore(
    node_type: str = Query(..., description="Node type: card, source, wiki_section, tag"),
    node_id: str = Query(..., description="Node identifier"),
    depth: int = Query(1, ge=1, le=3, description="Graph expansion depth (1-3)"),
    facade: WebFacade = Depends(get_facade),
) -> GraphResponse:
    """以任意节点类型为中心的图浏览。

    支持 source / tag / wiki_section / card 节点类型。
    """
    result = facade.get_graph_explore(node_type, node_id, depth=depth)
    if result is None:
        raise user_error(
            404, "graph_not_found", "未找到该节点的图数据。",
            "请确认 node_type 和 node_id 正确。",
        )
    return result


@router.get("/edge", response_model=GraphEdgeDetailResponse)
def graph_edge(
    source: str = Query(..., description="源节点 id"),
    target: str = Query(..., description="目标节点 id"),
    facade: WebFacade = Depends(get_facade),
) -> GraphEdgeDetailResponse:
    """查询两节点间所有的边及其可解释证据。

    返回所有从 source 到 target 的有向边，每条边附带 reason + evidence + strength。
    """
    result = facade.get_graph_edge(source, target)
    if result is None:
        raise user_error(
            404, "edge_not_found", "未找到两节点间的边。",
            "请确认 source 和 target 之间存在关系。",
        )
    return result
