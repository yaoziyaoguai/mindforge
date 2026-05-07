from __future__ import annotations

from fastapi import APIRouter, Depends

from mindforge_web.deps import get_facade
from mindforge_web.schemas import HealthResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(facade: WebFacade = Depends(get_facade)) -> HealthResponse:
    return facade.health()
