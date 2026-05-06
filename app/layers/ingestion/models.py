from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SourceSystem(Base):
    # Trzymamy słownik źródeł, żeby mapowania i poziom zaufania były przypięte do rejestru
    __tablename__ = "SourceSystem"
    __table_args__ = {"schema": "meta"}

    SourceSystem_ID: Mapped[int] = mapped_column(Integer, primary_key=True)
    SourceSystem_Code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    SourceSystem_Name: Mapped[str] = mapped_column(String(255), nullable=False)
    Trust_Level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ImportBatch(Base):
    # Grupujemy import w batch, żeby kolejne warstwy mogły śledzić jeden przebieg danych
    __tablename__ = "ImportBatch"
    __table_args__ = {"schema": "meta"}

    ImportBatch_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    SourceSystem_ID: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("meta.SourceSystem.SourceSystem_ID"),
        nullable=False,
    )
    Import_Status: Mapped[str] = mapped_column(String(30), nullable=False)
    Import_Start_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    Import_End_At: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Created_By: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Error_Message: Mapped[str | None] = mapped_column(Text, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RawFile(Base):
    # Zapisujemy oryginalny plik w RAW, żeby staging mógł odtworzyć import bez ponownego uploadu
    __tablename__ = "RawFile"
    __table_args__ = {"schema": "raw"}

    RawFile_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ImportBatch_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("meta.ImportBatch.ImportBatch_ID"),
        nullable=False,
    )
    File_Name: Mapped[str] = mapped_column(String(260), nullable=False)
    File_Type: Mapped[str] = mapped_column(String(30), nullable=False)
    File_Size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    File_Hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    File_Content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProcessLog(Base):
    # Logujemy kroki procesu, żeby diagnozować status, liczniki rekordów i błędy importu
    __tablename__ = "ProcessLog"
    __table_args__ = {"schema": "meta"}

    ProcessLog_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ImportBatch_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("meta.ImportBatch.ImportBatch_ID"),
        nullable=False,
    )
    RawFile_ID: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("raw.RawFile.RawFile_ID"),
        nullable=True,
    )
    Staging_ID: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    Step_Name: Mapped[str] = mapped_column(String(50), nullable=False)
    Step_Status: Mapped[str] = mapped_column(String(30), nullable=False)
    Started_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    Ended_At: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Records_In: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    Records_Out: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    Error_Message: Mapped[str | None] = mapped_column(Text, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
