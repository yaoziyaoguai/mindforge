from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from mindforge_web.deps import get_facade
from mindforge_web.schemas import (
    IngestionActionResponse,
    IngestionRequest,
    NextAction,
    PathActionRequest,
    PathActionResponse,
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
    try:
        return facade.copy_path(Path(payload.path))
    except PathActionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc


@router.post("/path-actions/reveal", response_model=PathActionResponse)
def reveal_path(
    payload: PathActionRequest,
    facade: WebFacade = Depends(get_facade),
) -> PathActionResponse:
    try:
        return facade.reveal_path(Path(payload.path))
    except PathActionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc


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
        reason="Cubox JSON Web import 尚未开放；当前只提供 honest unavailable，不伪造成功。",
        next_action=NextAction(
            label="Use Cubox dry-run",
            description="用现有 CLI 验证 JSON export；不会联网或自动 approve。",
            command="mindforge cubox dry-run --export <file.json>",
        ),
    )
