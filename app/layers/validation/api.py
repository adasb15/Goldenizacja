from dataclasses import asdict
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.sql import get_db
from app.layers.validation.schemas import LayerStatus, ValidationLoadResponse
from app.layers.validation.service import RecordsForValidationNotFoundError, load_validation_results


router = APIRouter(prefix="/validation", tags=["validation"])
FILESTREAM_PATH_ENV = "FILESTREAM_PATH"


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="validation", status="ready")


@router.post("/teryt-load")
async def teryt_load(
    simc: UploadFile = File(...),
    ulic: UploadFile = File(...),
) -> dict[str, str]:
    try:
        filestream_base = os.getenv(FILESTREAM_PATH_ENV, "/data/filestream")
        target_dir = Path(filestream_base) / "teryt"
        target_dir.mkdir(parents=True, exist_ok=True)

        (target_dir / "SIMC.csv").write_bytes(await simc.read())
        (target_dir / "ULIC.csv").write_bytes(await ulic.read())

        return {"status": "ok", "teryt_dir": str(target_dir)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TERYT_LOAD failed: {exc}") from exc


@router.post("/validation-load", response_model=ValidationLoadResponse)
def validation_load(
    raw_file_id: int = Form(...),
    entity_type: str = Form(...),
    check_email_dns: bool = Form(True),
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
