"""Usage Report API — 本地使用摘要端点。

中文学习型说明：纯本地数据聚合，不上传，不追踪，不收集隐私。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import UsageReportResponse as UsageReportResponseSchema
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/report", response_model=UsageReportResponseSchema)
def usage_report(facade: WebFacade = Depends(get_facade)) -> UsageReportResponseSchema:
    """返回本地使用摘要 — local-only，无遥测，无 secret。"""
    return facade.usage_report()
