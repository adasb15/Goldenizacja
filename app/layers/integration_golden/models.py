from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Unicode,
    UnicodeText,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MatchCandidateRecord(Base):
    __tablename__ = "Match_Candidate_Levenshtein"
    __table_args__ = (
        CheckConstraint(
            "Left_Preprocessed_ID < Right_Preprocessed_ID",
            name="CK_Match_Candidate_Levenshtein_Pair_Order",
        ),
        UniqueConstraint(
            "RawFile_ID",
            "Entity_Type",
            "Left_Preprocessed_ID",
            "Right_Preprocessed_ID",
            name="UX_Match_Candidate_Levenshtein_RawFile_Entity_Pair",
        ),
        {"schema": "stg"},
    )

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
    __table_args__ = (
        CheckConstraint(
            "Left_Preprocessed_ID < Right_Preprocessed_ID",
            name="CK_Match_Candidate_JaroWinkler_Pair_Order",
        ),
        UniqueConstraint(
            "RawFile_ID",
            "Entity_Type",
            "Left_Preprocessed_ID",
            "Right_Preprocessed_ID",
            name="UX_Match_Candidate_JaroWinkler_RawFile_Entity_Pair",
        ),
        {"schema": "stg"},
    )

    Match_Candidate_JaroWinkler_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Levenshtein_Candidate_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("stg.Match_Candidate_Levenshtein.Match_Candidate_Levenshtein_ID"),
        nullable=False,
    )
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


class EntityGroupRecord(Base):
    __tablename__ = "Entity_Group"
    __table_args__ = (
        UniqueConstraint("Entity_Type", "Group_Key", name="UQ_Entity_Group_Type_Key"),
        UniqueConstraint("Entity_Group_ID", "Entity_Type", name="UQ_Entity_Group_ID_Type"),
        CheckConstraint("Entity_Type IN ('PERSON', 'PARTY')", name="CK_Entity_Group_Entity_Type"),
        {"schema": "stg"},
    )

    Entity_Group_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Entity_Type: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    Group_Key: Mapped[str] = mapped_column(Unicode(64), nullable=False)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    Updated_At: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EntityGroupMemberRecord(Base):
    __tablename__ = "Entity_Group_Member"
    __table_args__ = (
        ForeignKeyConstraint(
            ["Entity_Group_ID", "Entity_Type"],
            ["stg.Entity_Group.Entity_Group_ID", "stg.Entity_Group.Entity_Type"],
            name="FK_Entity_Group_Member_Group_Type",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "Entity_Type",
            "Preprocessed_ID",
            name="UQ_Entity_Group_Member_Type_Preprocessed",
        ),
        CheckConstraint(
            "Entity_Type IN ('PERSON', 'PARTY')",
            name="CK_Entity_Group_Member_Entity_Type",
        ),
        CheckConstraint(
            "(Entity_Type = 'PERSON' AND Person_Preprocessed_ID = Preprocessed_ID AND Party_Preprocessed_ID IS NULL) "
            "OR (Entity_Type = 'PARTY' AND Party_Preprocessed_ID = Preprocessed_ID AND Person_Preprocessed_ID IS NULL)",
            name="CK_Entity_Group_Member_Preprocessed_Reference",
        ),
        {"schema": "stg"},
    )

    Entity_Group_Member_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Entity_Group_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Entity_Type: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    Preprocessed_ID: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Person_Preprocessed_ID: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "stg.Person_Preprocessed.Preprocessed_ID",
            name="FK_Entity_Group_Member_Person_Preprocessed",
        ),
        nullable=True,
    )
    Party_Preprocessed_ID: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "stg.Party_Preprocessed.Preprocessed_ID",
            name="FK_Entity_Group_Member_Party_Preprocessed",
        ),
        nullable=True,
    )
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
