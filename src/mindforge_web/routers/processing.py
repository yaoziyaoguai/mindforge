from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from mindforge_web.deps import get_facade
from mindforge_web.schemas import ProcessingRunResponse
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/processing", tags=["processing"])


@router.get("/runs/{run_id}", response_model=ProcessingRunResponse)
def processing_run(
    run_id: str,
    facade: WebFacade = Depends(get_facade),
) -> ProcessingRunResponse:
    run = facade.processing_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="processing run not found")
    return run

