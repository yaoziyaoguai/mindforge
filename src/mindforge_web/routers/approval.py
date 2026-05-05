from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import ApprovalResponse, ApproveRequest, RejectRequest, UnavailableResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/drafts", tags=["approval"])


@router.post("/{draft_id:path}/approve", response_model=ApprovalResponse)
def approve_draft(
    draft_id: str,
    payload: ApproveRequest,
    facade: WebFacade = Depends(get_facade),
) -> ApprovalResponse:
    return facade.review_service.approve(
        draft_id,
        confirm=payload.confirm,
        reviewed_source=payload.reviewed_source,
    )


@router.post("/{draft_id:path}/reject", response_model=UnavailableResponse)
def reject_draft(
    draft_id: str,
    _payload: RejectRequest,
    facade: WebFacade = Depends(get_facade),
) -> UnavailableResponse:
    _ = draft_id
    return facade.review_service.reject_unavailable()
