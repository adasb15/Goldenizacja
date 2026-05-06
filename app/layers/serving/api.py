from fastapi import APIRouter

from app.layers.serving.schemas import LayerStatus

# Wystawiamy status serving, żeby końcowa warstwa miała taki sam kontrakt jak reszta pipeline'u
router = APIRouter(prefix="/serving", tags=["serving"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="serving", status="ready")
