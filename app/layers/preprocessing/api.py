from dataclasses import asdict

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.sql import get_db
from app.layers.preprocessing.schemas import LayerStatus, PreprocessingLoadResponse
from app.layers.preprocessing.service import (
    StagingRecordsAlreadyPreprocessedError,
    StagingRecordsNotFoundError,
    load_staging_to_preprocessing,
)


router = APIRouter(prefix="/preprocessing", tags=["preprocessing"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="preprocessing", status="ready")


@router.post("/preprocessing-load", response_model=PreprocessingLoadResponse)
def preprocessing_load(
    raw_file_id: int = Form(...),
    entity_type: str = Form(...),
    db: Session = Depends(get_db),
) -> PreprocessingLoadResponse:
    try:
        result = load_staging_to_preprocessing(
            db=db,
            raw_file_id=raw_file_id,
            entity_type=entity_type,
        )
        return PreprocessingLoadResponse(**asdict(result))
    except (
        StagingRecordsNotFoundError,
        StagingRecordsAlreadyPreprocessedError,
        ValueError,
    ) as exc:
        # Błędy danych wejściowych zwracamy jako 400, żeby Postman pokazał konkretną przyczynę
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PREPROCESSING_LOAD failed: {exc}") from exc
