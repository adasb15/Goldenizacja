from dataclasses import asdict

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.sql import get_db
from app.layers.validation.schemas import LayerStatus, ValidationLoadResponse
from app.layers.validation.service import RecordsForValidationNotFoundError, load_validation_results


router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="validation", status="ready")


@router.post("/validation-load", response_model=ValidationLoadResponse)
def validation_load(
    raw_file_id: int = Form(...),
    entity_type: str = Form(...),
    check_email_dns: bool = Form(False),
    db: Session = Depends(get_db),
) -> ValidationLoadResponse:
    try:
        result = load_validation_results(
            db=db,
            raw_file_id=raw_file_id,
            entity_type=entity_type,
            check_email_dns=check_email_dns,
        )
        return ValidationLoadResponse(**asdict(result))
    except (RecordsForValidationNotFoundError, ValueError) as exc:
        # Brak danych po preprocessingu albo błędny typ encji to problem wejścia, nie awaria API
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"VALIDATION_LOAD failed: {exc}") from exc
