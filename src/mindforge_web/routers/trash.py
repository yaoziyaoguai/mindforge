"""Trash API router — 卡片 Move to Trash / Restore / List。

中文学习型说明：Trash 操作只移动卡片文件，不删除 source 原文。
API 不返回 raw secret，不修改 config。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from mindforge.trash_service import (
    TrashError,
    list_trashed_cards,
    move_card_to_trash,
    read_trashed_card,
    restore_trashed_card,
)

from mindforge_web.deps import get_facade
from mindforge_web.schemas import (
    TrashActionRequest,
    TrashActionResponse,
    TrashCardResponse,
    TrashDetailResponse,
    TrashListResponse,
)
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/trash", tags=["trash"])


@router.get("", response_model=TrashListResponse)
def trash_list(facade: WebFacade = Depends(get_facade)) -> TrashListResponse:
    cfg = facade.cfg
    cards = list_trashed_cards(cfg)
    return TrashListResponse(
        trashed_cards=[
            TrashCardResponse(
                trash_rel_path=c.trash_rel_path,
                title=c.title,
                previous_status=c.previous_status,
                original_path=c.original_path,
                trashed_at=c.trashed_at,
                track=c.track,
                tags=c.tags,
                source_title=c.source_title,
            )
            for c in cards
        ],
        trash_dir=str(cfg.vault.root / "90-Archive" / "Trash" / "Knowledge-Cards"),
    )


@router.get("/{trash_rel_path:path}", response_model=TrashDetailResponse)
def trash_detail(
    trash_rel_path: str,
    facade: WebFacade = Depends(get_facade),
) -> TrashDetailResponse:
    cfg = facade.cfg
    result = read_trashed_card(cfg, trash_rel_path)
    if result is None:
        raise HTTPException(status_code=404, detail="trashed card not found")
    fm, body = result
    return TrashDetailResponse(
        card=TrashCardResponse(
            trash_rel_path=trash_rel_path,
            title=str(fm.get("title", "")),
            previous_status=str(fm.get("previous_status", "")),
            original_path=str(fm.get("original_path", "")),
            trashed_at=str(fm.get("trashed_at", "")),
            track=fm.get("track"),
            tags=fm.get("tags", []) if isinstance(fm.get("tags"), list) else [],
            source_title=fm.get("source_title"),
        ),
        frontmatter=fm,
        body=body,
    )


@router.post("/restore", response_model=TrashActionResponse)
def trash_restore(
    payload: TrashActionRequest,
    facade: WebFacade = Depends(get_facade),
) -> TrashActionResponse:
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="restore 需要 confirm=true")
    try:
        result = restore_trashed_card(facade.cfg, payload.trash_rel_path)
        facade._load_context()  # 刷新索引
        return TrashActionResponse(
            ok=True,
            action="restored",
            message=f"Card restored to {result.restored_path} (status: {result.previous_status})",
            card_id=result.card_id,
            previous_status=result.previous_status,
            restored_path=result.restored_path,
            conflict_resolved=result.conflict_resolved,
        )
    except TrashError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Move-to-trash endpoints on drafts and library cards
@router.post("/drafts/{draft_id}", response_model=TrashActionResponse)
def trash_draft(
    draft_id: str,
    payload: TrashActionRequest,
    facade: WebFacade = Depends(get_facade),
) -> TrashActionResponse:
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="move to trash 需要 confirm=true")
    try:
        card_path = facade._resolve_draft_path(draft_id)
        result = move_card_to_trash(facade.cfg, card_path)
        return TrashActionResponse(
            ok=True,
            action="moved_to_trash",
            message="Draft card moved to Trash. Source file is not deleted.",
            card_id=result.card_id,
            previous_status=result.previous_status,
        )
    except (TrashError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/library/{card_ref}", response_model=TrashActionResponse)
def trash_library_card(
    card_ref: str,
    payload: TrashActionRequest,
    facade: WebFacade = Depends(get_facade),
) -> TrashActionResponse:
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="move to trash 需要 confirm=true")
    try:
        card_path = facade._resolve_library_card_path(card_ref)
        result = move_card_to_trash(facade.cfg, card_path)
        facade._load_context()
        return TrashActionResponse(
            ok=True,
            action="moved_to_trash",
            message="Approved card moved to Trash. Source file is not deleted. You can restore it from Trash.",
            card_id=result.card_id,
            previous_status=result.previous_status,
        )
    except (TrashError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
