from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from mindforge_web.deps import get_facade
from mindforge_web.schemas import RecallResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api", tags=["recall"])


@router.get("/recall", response_model=RecallResponse)
def recall(
    q: str = Query("", description="Local lexical recall query"),
    context: str | None = Query(
        None,
        description="附加 context 类型。'graph' = BM25 + 图感知邻居/tag 计数。",
    ),
    facade: WebFacade = Depends(get_facade),
) -> RecallResponse:
    return facade.recall(q, context=context)
