from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.sql import get_db
from app.layers.ingestion.schemas import LayerStatus, RawLoadResponse, RelationalQueryInfo
from app.layers.ingestion.service import (
    InvalidFileContentError,
    RelationalConnectionConfigurationError,
    UnsupportedRelationalQueryError,
    UnsupportedFileTypeError,
    UnsupportedSourceSystemError,
    import_raw_file,
    import_relational_source,
    list_relational_queries,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="ingestion", status="ready")


@router.get("/relational-queries", response_model=list[RelationalQueryInfo])
def relational_queries() -> list[RelationalQueryInfo]:
    return list_relational_queries()


@router.post("/raw-load", response_model=RawLoadResponse)
async def raw_load(
    file: UploadFile = File(...),
    source_system_code: str = Form(...),
    created_by: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> RawLoadResponse:
    filename = file.filename or "uploaded_file"
    # Odczytujemy upload do bajtów, żeby service mógł policzyć hash i zapisać oryginał w RAW
    content = await file.read()

    try:
        return import_raw_file(
            db=db,
            filename=filename,
            content=content,
            source_system_code=source_system_code,
            created_by=created_by,
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnsupportedSourceSystemError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidFileContentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAW_LOAD failed: {exc}") from exc


@router.post("/relational-load", response_model=RawLoadResponse)
def relational_load(
    source_system_code: str = Form(...),
    query_name: str = Form(...),
    entity_type: str | None = Form(default=None),
    created_by: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> RawLoadResponse:
    try:
        return import_relational_source(
            db=db,
            source_system_code=source_system_code,
            query_name=query_name,
            entity_type=entity_type,
            created_by=created_by,
        )
    except UnsupportedSourceSystemError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnsupportedRelationalQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RelationalConnectionConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidFileContentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RELATIONAL_LOAD failed: {exc}") from exc
