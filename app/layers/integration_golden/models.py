from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MatchCandidateRecord(Base):
    __tablename__ = "Match_Candidate_Levenshtein"
    __table_args__ = {"schema": "stg"}

    Match_Candidate_Levenshtein_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Entity_Type: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    RawFile_ID: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    Left_Preprocessed_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Right_Preprocessed_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Left_Staging_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Right_Staging_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Left_RawFile_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Right_RawFile_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Left_Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Right_Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Score: Mapped[float] = mapped_column(Float, nullable=False)
    Decision: Mapped[str] = mapped_column(Unicode(30), nullable=False)
    Strong_Match_Fields_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Conflict_Fields_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class JaroWinklerCandidateRecord(Base):
    __tablename__ = "Match_Candidate_JaroWinkler"
    __table_args__ = {"schema": "stg"}

    Match_Candidate_JaroWinkler_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Levenshtein_Candidate_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Entity_Type: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    RawFile_ID: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    Left_Preprocessed_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Right_Preprocessed_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Left_Staging_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Right_Staging_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Left_RawFile_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Right_RawFile_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Left_Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Right_Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Levenshtein_Score: Mapped[float] = mapped_column(Float, nullable=False)
    JaroWinkler_Score: Mapped[float] = mapped_column(Float, nullable=False)
    Decision: Mapped[str] = mapped_column(Unicode(30), nullable=False)
    Strong_Match_Fields_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Conflict_Fields_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Text_Match_Fields_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
