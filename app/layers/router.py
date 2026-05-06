from fastapi import APIRouter

from app.layers.analytics.api import router as analytics_router
from app.layers.ingestion.api import router as ingestion_router
from app.layers.integration_golden.api import router as integration_golden_router
from app.layers.serving.api import router as serving_router
from app.layers.staging_validation.api import router as staging_validation_router

# Grupujemy warstwy pod /layers, żeby endpointy pipeline'u miały jedną konwencję URL
router = APIRouter(prefix="/layers", tags=["layers"])
# Podpinamy routery w kolejności przepływu, żeby struktura kodu odzwierciedlała proces danych
router.include_router(ingestion_router)
router.include_router(staging_validation_router)
router.include_router(integration_golden_router)
router.include_router(analytics_router)
router.include_router(serving_router)
