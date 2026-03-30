from fastapi import APIRouter

from app.layers.analytics.schemas import LayerStatus

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="analytics", status="ready")
