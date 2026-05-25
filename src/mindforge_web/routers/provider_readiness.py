"""v2.5 U4 Provider Readiness Center — 独立 provider 就绪状态 API。

中文学习型说明：基于 provider_readiness.py 的 build_readiness_report，
返回所有 provider 的就绪状态，不读取或返回 API key 值。
"""

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import ProviderReadinessResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/provider", tags=["provider"])


@router.get("/readiness", response_model=ProviderReadinessResponse)
def provider_readiness(
    facade: WebFacade = Depends(get_facade),
) -> ProviderReadinessResponse:
    """返回完整 provider 就绪状态报告。

    包含：active_profile, opt_in_state, model_setup, aliases（不返回 key 值）,
    blockers, invariants。
    """
    return facade.provider_readiness_detail()
