from datetime import datetime
from datetime import date

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Boolean,
    Date,
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


class DimAddress(Base):
    __tablename__ = "DimAddress"
    __table_args__ = {"schema": "gold"}

    Address_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Street: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Building_Number: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    Apartment_Number: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    City: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Postal_City: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Postal_Code: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    District: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Province: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Country: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DimParty(Base):
    __tablename__ = "DimParty"
    __table_args__ = {"schema": "gold"}

    Party_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Short_Name: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Legal_Entity_Type: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Registration_Country: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Establishment_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    Updated_At: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DimPerson(Base):
    __tablename__ = "DimPerson"
    __table_args__ = {"schema": "gold"}

    Person_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    PESEL: Mapped[str | None] = mapped_column(Unicode(11), nullable=True)
    Serial_Number_ID_Card: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    Serial_Number_Passport: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    First_Name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Second_Name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Last_Name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Family_Name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Birth_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Place_Of_Birth: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Sex: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    Citizenship: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Phone_Number: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    Email_Address: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    Updated_At: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
