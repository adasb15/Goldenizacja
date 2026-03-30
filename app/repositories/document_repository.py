from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, title: str, content: str, file_path: str) -> Document:
        entity = Document(title=title, content=content, file_path=file_path)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def list_all(self) -> list[Document]:
        return list(self.db.scalars(select(Document).order_by(Document.id.desc())).all())
