from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from mindforge_web.deps import get_facade
from mindforge_web.schemas import (
    ConfigStatusResponse,
    SetupConfigPatch,
    SetupConfigUpdateResponse,
    SetupEditableConfigResponse,
    SetupValidationResponse,
)
from mindforge_web.services.web_config_service import ConfigUpdateError
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/status", response_model=ConfigStatusResponse)
def config_status(facade: WebFacade = Depends(get_facade)) -> ConfigStatusResponse:
    return facade.config_status()


@router.post("/check", response_model=ConfigStatusResponse)
def config_check(facade: WebFacade = Depends(get_facade)) -> ConfigStatusResponse:
    return facade.config_status()


@router.get("/editable", response_model=SetupEditableConfigResponse)
def editable_config(facade: WebFacade = Depends(get_facade)) -> SetupEditableConfigResponse:
    return facade.setup_editable_config()


@router.post("/validate", response_model=SetupValidationResponse)
def validate_config(
    payload: SetupConfigPatch,
    facade: WebFacade = Depends(get_facade),
) -> SetupValidationResponse:
    return facade.validate_setup_config_patch(payload)


@router.patch("/editable", response_model=SetupConfigUpdateResponse)
def update_config(
    payload: SetupConfigPatch,
    facade: WebFacade = Depends(get_facade),
) -> SetupConfigUpdateResponse:
    try:
        return facade.update_setup_config_patch(payload)
    except ConfigUpdateError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "errors": exc.errors}) from exc
