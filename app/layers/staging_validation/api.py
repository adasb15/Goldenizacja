from dataclasses import asdict

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.sql import get_db
from app.layers.staging_validation.schemas import LayerStatus, StagingLoadResponse
from app.layers.staging_validation.service import (
    ImportBatchNotFoundError,
    InvalidRawFileContentError,
    MissingColumnMappingError,
    RawFileNotFoundError,
    UnsupportedStagingFileTypeError,
    load_raw_file_to_staging,
)

router = APIRouter(prefix="/staging_validation", tags=["staging_validation"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="staging_validation", status="ready")


@router.post("/staging-load", response_model=StagingLoadResponse)
def staging_load(
    raw_file_id: int = Form(...),
    entity_type: str = Form(...),
    db: Session = Depends(get_db),
) -> StagingLoadResponse:
    try:
        result = load_raw_file_to_staging(
            db=db,
            raw_file_id=raw_file_id,
            entity_type=entity_type,
        )
        return StagingLoadResponse(**asdict(result))
    except (
        RawFileNotFoundError,
        ImportBatchNotFoundError,
        UnsupportedStagingFileTypeError,
        InvalidRawFileContentError,
        MissingColumnMappingError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"STAGING_LOAD failed: {exc}") from exc
