"""v2.5 U4 Provider Readiness Center — 独立 provider 就绪状态 API。

中文学习型说明：基于 provider_readiness.py 的 build_readiness_report，
返回所有 provider 的就绪状态，不读取或返回 API key 值。
"""

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import (
    ProviderReadinessResponse,
    ProviderStatusResponse,
    TestConnectionRequest,
    TestConnectionResponse,
)
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


@router.get("/status", response_model=ProviderStatusResponse)
def provider_status(
    facade: WebFacade = Depends(get_facade),
) -> ProviderStatusResponse:
    """返回安全脱敏的 provider 连接状态。

    只返回 redacted/masked 信息：configured, verified, verification_status,
    masked_key, provider_type, model, base_url host/path。
    绝不返回 API key 明文、Authorization header 或 raw secret。
    """
    return facade.provider_status_detail()


@router.post("/test-connection", response_model=TestConnectionResponse)
def test_provider_connection(
    body: TestConnectionRequest,
    facade: WebFacade = Depends(get_facade),
) -> TestConnectionResponse:
    """手动触发一次真实 provider 连接测试。

    使用最小 prompt ("ping")，max_tokens=1。不生成 ai_draft，不写 Library，
    不进入 Review。仅更新 checkpoint 的 verification 状态。
    错误信息经过脱敏处理，不输出 secret。
    """
    return facade.test_provider_connection(body.model_id)
