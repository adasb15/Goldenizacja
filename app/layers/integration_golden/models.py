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
    Numeric,
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


class GoldenRecordReject(Base):
    __tablename__ = "Golden_Record_Reject"
    __table_args__ = (
        ForeignKeyConstraint(
            ["Entity_Group_ID", "Entity_Type"],
            ["stg.Entity_Group.Entity_Group_ID", "stg.Entity_Group.Entity_Type"],
            name="FK_Golden_Record_Reject_Group",
        ),
        CheckConstraint(
            "Entity_Type IN ('PERSON', 'PARTY')",
            name="CK_Golden_Record_Reject_Entity_Type",
        ),
        CheckConstraint(
            "Status IN ('OPEN', 'RESOLVED', 'IGNORED')",
            name="CK_Golden_Record_Reject_Status",
        ),
        {"schema": "stg"},
    )

    Reject_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Entity_Type: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    Entity_Group_ID: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    RawFile_ID: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("raw.RawFile.RawFile_ID", name="FK_Golden_Record_Reject_RawFile"),
        nullable=True,
    )
    Reason_Code: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    Reason_Message: Mapped[str] = mapped_column(Unicode(1000), nullable=False)
    Missing_Fields_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Survivor_Values_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Member_Preprocessed_IDs_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Status: Mapped[str] = mapped_column(Unicode(30), nullable=False, server_default="OPEN")
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    Resolved_At: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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


class DimAddressType(Base):
    __tablename__ = "DimAddressType"
    __table_args__ = {"schema": "gold"}

    AddressType_ID: Mapped[int] = mapped_column(primary_key=True)
    AddressType_Name: Mapped[str] = mapped_column(Unicode(50), nullable=False, unique=True)


class DimIdentityType(Base):
    __tablename__ = "DimIdentityType"
    __table_args__ = {"schema": "gold"}

    IdentityType_ID: Mapped[int] = mapped_column(primary_key=True)
    IdentityType_Name: Mapped[str] = mapped_column(Unicode(50), nullable=False, unique=True)


class FactlessPartyIdentities(Base):
    __tablename__ = "FactlessPartyIdentities"
    __table_args__ = (
        UniqueConstraint(
            "IdentityType_ID",
            "Identity_Value",
            name="UQ_FactlessPartyIdentities_Type_Value",
        ),
        CheckConstraint(
            "Match_Confidence IS NULL OR (Match_Confidence >= 0 AND Match_Confidence <= 1)",
            name="CK_FactlessPartyIdentities_Match_Confidence",
        ),
        CheckConstraint(
            "Valid_To IS NULL OR Valid_From IS NULL OR Valid_To >= Valid_From",
            name="CK_FactlessPartyIdentities_Dates",
        ),
        {"schema": "gold"},
    )

    PartyIdentity_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Party_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("gold.DimParty.Party_ID"),
        nullable=False,
    )
    IdentityType_ID: Mapped[int] = mapped_column(
        ForeignKey("gold.DimIdentityType.IdentityType_ID"),
        nullable=False,
    )
    Identity_Value: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    Is_Valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    Match_Confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    Valid_From: Mapped[date | None] = mapped_column(Date, nullable=True)
    Valid_To: Mapped[date | None] = mapped_column(Date, nullable=True)


class FactlessPersonAddress(Base):
    __tablename__ = "FactlessPersonAddress"
    __table_args__ = (
        CheckConstraint(
            "Valid_To IS NULL OR Valid_From IS NULL OR Valid_To >= Valid_From",
            name="CK_FactlessPersonAddress_Dates",
        ),
        {"schema": "gold"},
    )

    PersonAddress_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Person_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("gold.DimPerson.Person_ID"),
        nullable=False,
    )
    Address_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("gold.DimAddress.Address_ID"),
        nullable=False,
    )
    AddressType_ID: Mapped[int] = mapped_column(
        ForeignKey("gold.DimAddressType.AddressType_ID"),
        nullable=False,
    )
    Valid_From: Mapped[date | None] = mapped_column(Date, nullable=True)
    Valid_To: Mapped[date | None] = mapped_column(Date, nullable=True)


class FactlessPartyAddress(Base):
    __tablename__ = "FactlessPartyAddress"
    __table_args__ = (
        CheckConstraint(
            "Valid_To IS NULL OR Valid_From IS NULL OR Valid_To >= Valid_From",
            name="CK_FactlessPartyAddress_Dates",
        ),
        {"schema": "gold"},
    )

    PartyAddress_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Party_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("gold.DimParty.Party_ID"),
        nullable=False,
    )
    Address_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("gold.DimAddress.Address_ID"),
        nullable=False,
    )
    AddressType_ID: Mapped[int] = mapped_column(
        ForeignKey("gold.DimAddressType.AddressType_ID"),
        nullable=False,
    )
    Valid_From: Mapped[date | None] = mapped_column(Date, nullable=True)
    Valid_To: Mapped[date | None] = mapped_column(Date, nullable=True)


class EntityChangeLog(Base):
    __tablename__ = "EntityChangeLog"
    __table_args__ = {"schema": "gold"}

    Change_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Entity_Type: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    DimPerson_ID: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("gold.DimPerson.Person_ID", name="FK_EntityChangeLog_Person"),
        nullable=True,
    )
    DimParty_ID: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("gold.DimParty.Party_ID", name="FK_EntityChangeLog_Party"),
        nullable=True,
    )
    DimAddress_ID: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("gold.DimAddress.Address_ID", name="FK_EntityChangeLog_Address"),
        nullable=True,
    )
    PartyIdentity_ID: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("gold.FactlessPartyIdentities.PartyIdentity_ID", name="FK_EntityChangeLog_PartyIdentity"),
        nullable=True,
    )
    Attribute_Name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    Old_Value: Mapped[str | None] = mapped_column(Unicode(4000), nullable=True)
    New_Value: Mapped[str | None] = mapped_column(Unicode(4000), nullable=True)
    Change_Date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ImportBatch_ID: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("meta.ImportBatch.ImportBatch_ID", name="FK_EntityChangeLog_ImportBatch"),
        nullable=True,
    )


class GoldenPersonLineage(Base):
    __tablename__ = "GoldenPersonLineage"
    __table_args__ = {"schema": "gold"}

    Lineage_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    DimPerson_ID: Mapped[int] = mapped_column(BigInteger, ForeignKey("gold.DimPerson.Person_ID"), nullable=False)
    Attribute_Name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    SourceSystem_ID: Mapped[int] = mapped_column(ForeignKey("meta.SourceSystem.SourceSystem_ID"), nullable=False)
    Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    ImportBatch_ID: Mapped[int] = mapped_column(BigInteger, ForeignKey("meta.ImportBatch.ImportBatch_ID"), nullable=False)
    Selection_Rule: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Trust_Score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    Quality_Score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    Validation_Status: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Recorded_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GoldenPartyLineage(Base):
    __tablename__ = "GoldenPartyLineage"
    __table_args__ = {"schema": "gold"}

    Lineage_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    DimParty_ID: Mapped[int] = mapped_column(BigInteger, ForeignKey("gold.DimParty.Party_ID"), nullable=False)
    Attribute_Name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    SourceSystem_ID: Mapped[int] = mapped_column(ForeignKey("meta.SourceSystem.SourceSystem_ID"), nullable=False)
    Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    ImportBatch_ID: Mapped[int] = mapped_column(BigInteger, ForeignKey("meta.ImportBatch.ImportBatch_ID"), nullable=False)
    Selection_Rule: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Trust_Score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    Quality_Score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    Validation_Status: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Recorded_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GoldenAddressLineage(Base):
    __tablename__ = "GoldenAddressLineage"
    __table_args__ = {"schema": "gold"}

    Lineage_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    DimAddress_ID: Mapped[int] = mapped_column(BigInteger, ForeignKey("gold.DimAddress.Address_ID"), nullable=False)
    Attribute_Name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    SourceSystem_ID: Mapped[int] = mapped_column(ForeignKey("meta.SourceSystem.SourceSystem_ID"), nullable=False)
    Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    ImportBatch_ID: Mapped[int] = mapped_column(BigInteger, ForeignKey("meta.ImportBatch.ImportBatch_ID"), nullable=False)
    Selection_Rule: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Trust_Score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    Quality_Score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    Validation_Status: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Recorded_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GoldenPartyIdentityLineage(Base):
    __tablename__ = "GoldenPartyIdentityLineage"
    __table_args__ = {"schema": "gold"}

    Lineage_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    PartyIdentity_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("gold.FactlessPartyIdentities.PartyIdentity_ID"),
        nullable=False,
    )
    Attribute_Name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    SourceSystem_ID: Mapped[int] = mapped_column(ForeignKey("meta.SourceSystem.SourceSystem_ID"), nullable=False)
    Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    ImportBatch_ID: Mapped[int] = mapped_column(BigInteger, ForeignKey("meta.ImportBatch.ImportBatch_ID"), nullable=False)
    Selection_Rule: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Trust_Score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    Quality_Score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    Validation_Status: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Recorded_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
