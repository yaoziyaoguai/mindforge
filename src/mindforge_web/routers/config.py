from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import ConfigStatusResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/status", response_model=ConfigStatusResponse)
def config_status(facade: WebFacade = Depends(get_facade)) -> ConfigStatusResponse:
    return facade.config_status()


@router.post("/check", response_model=ConfigStatusResponse)
def config_check(facade: WebFacade = Depends(get_facade)) -> ConfigStatusResponse:
    return facade.config_status()
