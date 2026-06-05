from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ColumnMapping(Base):
    # Trzymamy mapowanie kolumn, żeby service mógł zamienić różne źródła na wspólny staging
    __tablename__ = "ColumnMapping"
    __table_args__ = {"schema": "meta"}

    ColumnMapping_ID: Mapped[int] = mapped_column(Integer, primary_key=True)
    SourceSystem_ID: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("meta.SourceSystem.SourceSystem_ID"),
        nullable=False,
    )
    Entity_Type: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    Source_Column_Name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Canonical_Column_Name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PersonStaging(Base):
    # Zbieramy dane osoby w stagingu, żeby później porównać źródła i zbudować golden person
    __tablename__ = "Person_Staging"
    __table_args__ = {"schema": "stg"}

    Staging_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
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
    Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    PESEL: Mapped[str | None] = mapped_column(Unicode(11), nullable=True)
    Serial_Number_ID_Card: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Serial_Number_Passport: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    First_Name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Second_Name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Last_Name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Family_Name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Birth_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Place_Of_Birth: Mapped[str | None] = mapped_column(Unicode(150), nullable=True)
    Sex: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    Citizenship: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Phone_Number: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Email_Address: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Street: Mapped[str | None] = mapped_column(Unicode(150), nullable=True)
    Building_Number: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Apartment_Number: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    City: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Postal_City: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Postal_Code: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    District: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Province: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Country: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Raw_Record_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PartyStaging(Base):
    # Zbieramy dane podmiotu w stagingu, żeby później budować golden party, identyfikatory i relacje
    __tablename__ = "Party_Staging"
    __table_args__ = {"schema": "stg"}

    Staging_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
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
    Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Name: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Short_Name: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Legal_Entity_Type: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Registration_Country: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Establishment_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Identifiers_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Street: Mapped[str | None] = mapped_column(Unicode(150), nullable=True)
    Building_Number: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Apartment_Number: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    City: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Postal_City: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Postal_Code: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    District: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Province: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Country: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Register_Status: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Registration_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Deregistration_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Decision_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Decision_Number: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Register_Number: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Bank_Accounts_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Has_Virtual_Accounts: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    Business_Scope: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Ownership_Form: Mapped[str | None] = mapped_column(Unicode(150), nullable=True)
    Municipality: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Phone_Number: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Email_Address: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Website: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Agent_Type: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Insurance_Company: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Related_Persons_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Related_Parties_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Registration_Status: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Last_Update_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Next_Renewal_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Managing_LOU: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Validation_Sources: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Validation_Authority_ID: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    Validation_Authority_Entity_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Direct_Parent_LEI: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    Direct_Parent_Name: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Direct_Parent_Relationship_Type: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Direct_Parent_Relationship_Status: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Direct_Parent_Relationship_Start_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Direct_Parent_Relationship_End_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Ultimate_Parent_LEI: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    Ultimate_Parent_Name: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Ultimate_Parent_Relationship_Type: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Ultimate_Parent_Relationship_Status: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Ultimate_Parent_Relationship_Start_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Ultimate_Parent_Relationship_End_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Raw_Record_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
