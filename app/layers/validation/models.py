from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ValidationResult(Base):
    # Wynik zapisujemy per reguła, żeby później dało się analizować konkretne błędy jakości
    __tablename__ = "Validation_Result"
    __table_args__ = {"schema": "stg"}

    Validation_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ImportBatch_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("meta.ImportBatch.ImportBatch_ID"),
        nullable=False,
    )
    RawFile_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("raw.RawFile.RawFile_ID"),
        nullable=False,
    )
    Entity_Type: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    Staging_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Preprocessed_ID: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    Validation_Level: Mapped[str] = mapped_column(Unicode(30), nullable=False)
    Rule_Code: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    Field_Name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    Severity: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    Status: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    Message: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    Checked_Value: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
