import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from neo4j import Driver
from sqlalchemy.orm import Session

from app.db.neo4j import get_neo4j_driver
from app.db.sql import get_db
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentCreate, DocumentRead, FileLineCountResponse, MatchResult
from app.services.file_storage import FileStorageService
from app.services.matching import find_best_matches

router = APIRouter()


def _save_to_neo4j(driver: Driver, doc_id: int, title: str) -> None:
    with driver.session() as session:
        session.run(
            "MERGE (d:Document {id: $id}) SET d.title = $title",
            id=doc_id,
            title=title,
        )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/documents", response_model=DocumentRead)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)) -> DocumentRead:
    storage = FileStorageService()
    file_path = storage.save_document(payload.title, payload.content)

    repo = DocumentRepository(db)
    entity = repo.create(payload.title, payload.content, file_path)

    driver = get_neo4j_driver()
    _save_to_neo4j(driver, entity.id, entity.title)
    driver.close()

    return entity


@router.get("/documents", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentRead]:
    repo = DocumentRepository(db)
    return repo.list_all()


@router.get("/documents/search", response_model=list[MatchResult])
def search_documents(q: str, db: Session = Depends(get_db)) -> list[MatchResult]:
    repo = DocumentRepository(db)
    docs = repo.list_all()
    return find_best_matches(q, docs)


@router.post("/files/line-count", response_model=FileLineCountResponse)
async def count_file_lines(file: UploadFile = File(...)) -> FileLineCountResponse:
    filename = file.filename or "uploaded_file"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    text_content = content.decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(text_content))
    line_count = sum(1 for _ in reader)

    return FileLineCountResponse(filename=filename, line_count=line_count)
