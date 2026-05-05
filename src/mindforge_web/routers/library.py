from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from mindforge_web.deps import get_facade
from mindforge_web.presenters.web_errors import user_error
from mindforge_web.schemas import (
    LibraryCardDetailResponse,
    LibraryCardsResponse,
    LibraryStatsResponse,
    WorkflowSummaryResponse,
)
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api", tags=["library"])


@router.get("/workflow/summary", response_model=WorkflowSummaryResponse)
def workflow_summary(facade: WebFacade = Depends(get_facade)) -> WorkflowSummaryResponse:
    return facade.workflow_summary()


@router.get("/library/stats", response_model=LibraryStatsResponse)
def library_stats(facade: WebFacade = Depends(get_facade)) -> LibraryStatsResponse:
    return facade.library_cards().stats


@router.get("/library/cards", response_model=LibraryCardsResponse)
def library_cards(facade: WebFacade = Depends(get_facade)) -> LibraryCardsResponse:
    return facade.library_cards()


@router.get(
    "/library/card",
    response_model=LibraryCardDetailResponse,
    response_model_exclude_none=True,
)
def library_card(
    ref: str = Query(..., description="Card id, filename, absolute path, or vault-relative path"),
    show_content: bool = Query(False, description="Show card body; source body is never returned."),
    facade: WebFacade = Depends(get_facade),
) -> LibraryCardDetailResponse:
    detail = facade.library_card_detail(ref, show_content=show_content)
    if detail is None:
        raise user_error(404, "card_not_found", "未找到该 Knowledge Card。", "回到 Library 列表重新选择。")
    return detail
