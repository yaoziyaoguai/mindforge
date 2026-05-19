from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from mindforge_web.deps import get_facade
from mindforge_web.schemas import (
    FrequencyUpdateRequest,
    IngestionActionResponse,
    IngestionRequest,
    NextAction,
    PathActionRequest,
    PathActionResponse,
    RevealRequest,
    SourcesResponse,
    UnavailableResponse,
    WatchSourcesResponse,
)
from mindforge_web.services.web_path_action_service import PathActionError
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=SourcesResponse)
def sources(facade: WebFacade = Depends(get_facade)) -> SourcesResponse:
    return facade.sources()


@router.get("/watch", response_model=WatchSourcesResponse)
def watch_sources(facade: WebFacade = Depends(get_facade)) -> WatchSourcesResponse:
    return facade.watch_sources()


@router.post("/watch", response_model=IngestionActionResponse)
def watch_add(
    payload: IngestionRequest,
    facade: WebFacade = Depends(get_facade),
) -> IngestionActionResponse:
    return facade.watch_add(
        Path(payload.path),
        frequency=payload.frequency,
        recursive=payload.recursive,
        process_now=payload.process_now,
    )


@router.post("/watch/scan", response_model=IngestionActionResponse)
def watch_scan(
    ref: str | None = None,
    all_sources: bool = False,
    facade: WebFacade = Depends(get_facade),
) -> IngestionActionResponse:
    return facade.watch_scan(ref=ref, all_sources=all_sources)


@router.delete("/watch/{ref:path}", response_model=IngestionActionResponse)
def watch_delete(ref: str, facade: WebFacade = Depends(get_facade)) -> IngestionActionResponse:
    return facade.watch_delete(ref)


@router.patch("/watch/{ref:path}/frequency", response_model=IngestionActionResponse)
def watch_frequency(
    ref: str,
    payload: FrequencyUpdateRequest,
    facade: WebFacade = Depends(get_facade),
) -> IngestionActionResponse:
    return facade.watch_frequency(ref, payload.frequency)


@router.post("/import", response_model=IngestionActionResponse)
def import_source(
    payload: IngestionRequest,
    facade: WebFacade = Depends(get_facade),
) -> IngestionActionResponse:
    return facade.import_source(Path(payload.path))


@router.post("/path-actions/copy", response_model=PathActionResponse)
def copy_path(
    payload: PathActionRequest,
    facade: WebFacade = Depends(get_facade),
) -> PathActionResponse:
    # 中文学习型说明：raw path endpoint 已禁用 —— 接受任意 absolute path
    # 构成 path probing oracle（403/404 差异泄露路径是否存在）。
    # 前端改用 client-side clipboard，从 card/draft response 的
    # source_path_view.display_path 直接复制。
    raise HTTPException(
        status_code=410,
        detail={
            "message": "Raw path copy is disabled. "
            "Copy display paths client-side from source_path_view in card/draft API responses."
        },
    )


@router.post("/path-actions/reveal", response_model=PathActionResponse)
def reveal_path(
    payload: PathActionRequest,
    facade: WebFacade = Depends(get_facade),
) -> PathActionResponse:
    # 中文学习型说明：raw path endpoint 已禁用。
    # 请改用 object-reference endpoint: POST /api/sources/reveal
    # 传 card_id 或 draft_id，后端自行查找对象并校验权限。
    raise HTTPException(
        status_code=410,
        detail={
            "message": "Raw path reveal is disabled. "
            "Use POST /api/sources/reveal with card_id or draft_id instead."
        },
    )


@router.post("/reveal", response_model=PathActionResponse)
def reveal_source(
    payload: RevealRequest,
    facade: WebFacade = Depends(get_facade),
) -> PathActionResponse:
    """安全的 object-reference reveal 端点。

    中文学习型说明：前端传 card_id 或 draft_id，后端自行查找对象、
    校验 source_path_view 权限，再执行 reveal。不接受 raw path。
    """
    try:
        return facade.reveal_by_ref(card_id=payload.card_id, draft_id=payload.draft_id)
    except PathActionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.post("/import-local", response_model=UnavailableResponse)
def import_local(_facade: WebFacade = Depends(get_facade)) -> UnavailableResponse:
    return UnavailableResponse(
        reason="兼容旧入口：请改用 /api/sources/import。它会一次性导入并只生成 ai_draft。",
        next_action=NextAction(
            label="Use Web import",
            description="Web import 不加入 watched sources，也不会自动 approve。",
            href="/sources",
        ),
    )


@router.post("/import-cubox-json", response_model=UnavailableResponse)
def import_cubox_json(_facade: WebFacade = Depends(get_facade)) -> UnavailableResponse:
    return UnavailableResponse(
        reason="External account import 尚未开放；当前只提供 honest unavailable，不伪造成功。",
        next_action=NextAction(
            label="Use local source",
            description="请先添加本地文件或文件夹 source；不会联网或自动 approve。",
            href="/sources",
        ),
    )
