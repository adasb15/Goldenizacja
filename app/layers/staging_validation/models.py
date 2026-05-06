from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text, func
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


class PersonStaging(Base):
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
    Source_Record_ID: Mapped[str | None] = mapped_column(String(100), nullable=True)
    PESEL: Mapped[str | None] = mapped_column(String(11), nullable=True)
    Serial_Number_ID_Card: Mapped[str | None] = mapped_column(String(30), nullable=True)
    Serial_Number_Passport: Mapped[str | None] = mapped_column(String(30), nullable=True)
    First_Name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Second_Name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Last_Name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Family_Name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Birth_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Place_Of_Birth: Mapped[str | None] = mapped_column(String(150), nullable=True)
    Sex: Mapped[str | None] = mapped_column(String(1), nullable=True)
    Citizenship: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Phone_Number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    Email_Address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    Street: Mapped[str | None] = mapped_column(String(150), nullable=True)
    Building_Number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    Apartment_Number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    City: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Postal_City: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Postal_Code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    District: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Raw_Record_JSON: Mapped[str | None] = mapped_column(Text, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PartyStaging(Base):
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
    Source_Record_ID: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    Short_Name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    Legal_Entity_Type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Registration_Country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Establishment_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Identifiers_JSON: Mapped[str | None] = mapped_column(Text, nullable=True)
    Street: Mapped[str | None] = mapped_column(String(150), nullable=True)
    Building_Number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    Apartment_Number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    City: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Postal_City: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Postal_Code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    District: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Raw_Record_JSON: Mapped[str | None] = mapped_column(Text, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
