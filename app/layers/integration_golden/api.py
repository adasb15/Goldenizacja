from fastapi import APIRouter

from app.layers.integration_golden.schemas import LayerStatus

# Wystawiamy status integration_golden, żeby warstwa była widoczna zanim powstanie goldenizacja
router = APIRouter(prefix="/integration_golden", tags=["integration_golden"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="integration_golden", status="ready")
