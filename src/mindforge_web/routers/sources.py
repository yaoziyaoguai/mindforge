from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import NextAction, SourcesResponse, UnavailableResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=SourcesResponse)
def sources(facade: WebFacade = Depends(get_facade)) -> SourcesResponse:
    return facade.sources()


@router.post("/import-local", response_model=UnavailableResponse)
def import_local(_facade: WebFacade = Depends(get_facade)) -> UnavailableResponse:
    return UnavailableResponse(
        reason="Web v1 没有安全的本地 import write service；请把文件放入 configured inbox 后运行 scan/process。",
        next_action=NextAction(
            label="Use CLI scan",
            description="先通过现有 CLI 路径写 state，避免 Web 重写 source/import 业务。",
            command="mindforge scan",
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
