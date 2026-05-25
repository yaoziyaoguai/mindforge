"""v2.5 U2 Source-to-Card Lifecycle — 知识流转生命周期 API。

中文学习型说明：返回每个 source 的卡片生命周期统计（Source → ai_draft → human_approved），
帮助用户理解知识从来源到确认的完整流转。
"""

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import LifecycleResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api", tags=["lifecycle"])


@router.get("/lifecycle", response_model=LifecycleResponse)
def source_lifecycle(
    facade: WebFacade = Depends(get_facade),
) -> LifecycleResponse:
    """返回每个 source 的卡片生命周期统计。"""
    return facade.source_lifecycle()
