from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import HomeStatusResponse, WorkspaceStatus
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api", tags=["home"])


@router.get("/home/status", response_model=HomeStatusResponse)
def home_status(facade: WebFacade = Depends(get_facade)) -> HomeStatusResponse:
    return facade.home_status()


@router.get("/workspace/status", response_model=WorkspaceStatus)
def workspace_status(facade: WebFacade = Depends(get_facade)) -> WorkspaceStatus:
    return facade.workspace_status()
