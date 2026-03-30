from fastapi import APIRouter

from app.layers.staging_validation.schemas import LayerStatus

router = APIRouter(prefix="/staging_validation", tags=["staging_validation"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="staging_validation", status="ready")
