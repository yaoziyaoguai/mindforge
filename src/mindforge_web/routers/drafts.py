from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.presenters.web_errors import user_error
from mindforge_web.schemas import CardBodyUpdateRequest, CardBodyUpdateResponse, DraftDetailResponse, DraftsResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/drafts", tags=["drafts"])


@router.get("", response_model=DraftsResponse)
def drafts(facade: WebFacade = Depends(get_facade)) -> DraftsResponse:
    return facade.drafts()


@router.get("/{draft_id:path}", response_model=DraftDetailResponse)
def draft_detail(draft_id: str, facade: WebFacade = Depends(get_facade)) -> DraftDetailResponse:
    detail = facade.draft_detail(draft_id)
    if detail is None:
        raise user_error(404, "draft_not_found", "未找到该 ai_draft。", "回到 Drafts 列表重新选择。")
    return detail


@router.patch("/{draft_id:path}", response_model=CardBodyUpdateResponse)
def update_draft_body(
    draft_id: str,
    payload: CardBodyUpdateRequest,
    facade: WebFacade = Depends(get_facade),
) -> CardBodyUpdateResponse:
    result = facade.update_draft_body(draft_id, payload.body)
    if result is None:
        raise user_error(404, "draft_not_found", "未找到该 ai_draft。", "回到 Drafts 列表重新选择。")
    if not result.ok:
        raise user_error(400, "draft_save_failed", result.message, "回到 Draft detail 检查状态后重试。")
    return result
