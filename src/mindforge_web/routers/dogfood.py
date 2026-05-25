"""v2.5 U3 Dogfood Report API — 工作台使用报告端点。

中文学习型说明：报告从现有本地数据聚合统计值，不调用 LLM、
不做 embedding/RAG、不修改任何文件。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import DogfoodReportResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/dogfood", tags=["dogfood"])


@router.get("/report", response_model=DogfoodReportResponse)
def dogfood_report(facade: WebFacade = Depends(get_facade)) -> DogfoodReportResponse:
    """返回结构化工作台使用报告。"""
    return facade.dogfood_report()
