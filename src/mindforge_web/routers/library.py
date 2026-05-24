from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from mindforge_web.deps import get_facade
from mindforge_web.presenters.web_errors import user_error
from mindforge_web.schemas import (
    CardBodyUpdateRequest,
    CardBodyUpdateResponse,
    ExportCardsRequest,
    ExportCardsResponse,
    LibraryCardDetailResponse,
    LibraryCardsResponse,
    LibraryStatsResponse,
    ProvenanceTrailResponse,
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
    show_content: bool = Query(True, description="Show card body; source body is never returned."),
    facade: WebFacade = Depends(get_facade),
) -> LibraryCardDetailResponse:
    detail = facade.library_card_detail(ref, show_content=show_content)
    if detail is None:
        raise user_error(404, "card_not_found", "未找到该 Knowledge Card。", "回到 Library 列表重新选择。")
    return detail


@router.get("/library/trail", response_model=ProvenanceTrailResponse)
def provenance_trail(
    ref: str = Query(..., description="Card id, filename, absolute path, or vault-relative path"),
    facade: WebFacade = Depends(get_facade),
) -> ProvenanceTrailResponse:
    trail = facade.provenance_trail(ref)
    if trail is None:
        raise user_error(404, "card_not_found", "未找到该 Knowledge Card。", "回到 Library 列表重新选择。")
    return trail


@router.patch("/library/card", response_model=CardBodyUpdateResponse)
def update_library_card(
    payload: CardBodyUpdateRequest,
    ref: str = Query(..., description="Card id, filename, absolute path, or vault-relative path"),
    facade: WebFacade = Depends(get_facade),
) -> CardBodyUpdateResponse:
    result = facade.update_library_card_body(ref, payload.body)
    if result is None:
        raise user_error(404, "card_not_found", "未找到该 Knowledge Card。", "回到 Library 列表重新选择。")
    if not result.ok:
        raise user_error(400, "card_save_failed", result.message, "重新打开 card detail 后再保存。")
    return result


@router.post("/knowledge/export", response_model=ExportCardsResponse)
def export_cards(
    payload: ExportCardsRequest,
    facade: WebFacade = Depends(get_facade),
) -> ExportCardsResponse:
    """导出选中卡片为安全 Markdown（白名单过滤）。"""
    parts: list[str] = []
    for card_id in payload.card_ids:
        detail = facade.library_card_detail(card_id, show_content=True)
        if detail is None:
            continue
        card = detail.card
        body = detail.body or ""
        # 安全白名单：仅导出 title + body + status + created_at + source_title
        status_label = "已确认" if card.status == "human_approved" else card.status
        created = card.created_at[:10] if card.created_at else "未知"
        source = card.source_title or "-"
        parts.append(
            f"# {card.title or '未命名卡片'}\n\n"
            f"状态: {status_label} | 创建: {created} | 来源: {source}\n\n"
            f"{body}\n"
        )
    markdown = "\n---\n\n".join(parts)
    return ExportCardsResponse(markdown=markdown, card_count=len(parts))
