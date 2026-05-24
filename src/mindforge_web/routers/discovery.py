"""v0.6 R6 Discovery Context API — 图感知的发现上下文 endpoint。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from mindforge_web.deps import get_facade
from mindforge_web.schemas import DiscoveryContextResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


@router.get("/context", response_model=DiscoveryContextResponse)
def discovery_context(
    ref: str = Query(..., description="Card id, filename, or vault-relative path"),
    facade: WebFacade = Depends(get_facade),
) -> DiscoveryContextResponse:
    """获取以指定卡片为中心的图感知发现上下文。

    中文学习型说明：此 endpoint 返回围绕一张卡片的完整 discovery context，
    包括 1-hop 邻居、2-hop 邻居、wiki sections、共享 tags、共享 sources。
    不做 RAG answering，只做 deterministic context assembly。
    """
    from mindforge_web.presenters.web_errors import user_error

    result = facade.get_discovery_context(ref)
    if result is None:
        raise user_error(
            404, "discovery_context_not_found",
            "未找到该卡片的发现上下文。",
            "请确认卡片存在且已 approved。",
        )
    return result
