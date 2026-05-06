from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ColumnMapping(Base):
    __tablename__ = "ColumnMapping"
    __table_args__ = {"schema": "meta"}

    ColumnMapping_ID: Mapped[int] = mapped_column(Integer, primary_key=True)
    SourceSystem_ID: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("meta.SourceSystem.SourceSystem_ID"),
        nullable=False,
    )
    Entity_Type: Mapped[str] = mapped_column(String(20), nullable=False)
    Source_Column_Name: Mapped[str] = mapped_column(String(255), nullable=False)
    Canonical_Column_Name: Mapped[str] = mapped_column(String(255), nullable=False)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
