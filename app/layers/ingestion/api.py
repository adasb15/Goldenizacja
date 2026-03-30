from fastapi import APIRouter

from app.layers.ingestion.schemas import LayerStatus

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="ingestion", status="ready")
