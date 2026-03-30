from fastapi import APIRouter

from app.layers.integration_golden.schemas import LayerStatus

router = APIRouter(prefix="/integration_golden", tags=["integration_golden"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="integration_golden", status="ready")
