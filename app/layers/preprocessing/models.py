from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PersonPreprocessed(Base):
    # Trzymamy wartości po standaryzacji, żeby matching nie musiał niszczyć danych ze stagingu
    __tablename__ = "Person_Preprocessed"
    __table_args__ = {"schema": "stg"}

    Preprocessed_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Staging_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("stg.Person_Staging.Staging_ID"),
        nullable=False,
    )
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
    PESEL_Normalized: Mapped[str | None] = mapped_column(String(20), nullable=True)
    First_Name_Normalized: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Second_Name_Normalized: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Last_Name_Normalized: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Family_Name_Normalized: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Full_Name_Normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    Phone_Normalized: Mapped[str | None] = mapped_column(String(50), nullable=True)
    Email_Normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    Street_Normalized: Mapped[str | None] = mapped_column(String(150), nullable=True)
    Building_Number_Normalized: Mapped[str | None] = mapped_column(String(30), nullable=True)
    Apartment_Number_Normalized: Mapped[str | None] = mapped_column(String(30), nullable=True)
    City_Normalized: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Postal_Code_Normalized: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Country_Normalized: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Full_Address_Normalized: Mapped[str | None] = mapped_column(String(500), nullable=True)
    Preprocessing_Rules_JSON: Mapped[str | None] = mapped_column(Text, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PartyPreprocessed(Base):
    # Trzymamy ujednolicone klucze podmiotu osobno od stagingu, żeby zachować lineage źródła
    __tablename__ = "Party_Preprocessed"
    __table_args__ = {"schema": "stg"}

    Preprocessed_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    Staging_ID: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("stg.Party_Staging.Staging_ID"),
        nullable=False,
    )
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
    Name_Normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    Short_Name_Normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    Legal_Entity_Type_Normalized: Mapped[str | None] = mapped_column(String(100), nullable=True)
    NIP_Normalized: Mapped[str | None] = mapped_column(String(20), nullable=True)
    REGON_Normalized: Mapped[str | None] = mapped_column(String(20), nullable=True)
    KRS_Normalized: Mapped[str | None] = mapped_column(String(20), nullable=True)
    LEI_Normalized: Mapped[str | None] = mapped_column(String(30), nullable=True)
    Phone_Normalized: Mapped[str | None] = mapped_column(String(50), nullable=True)
    Email_Normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    Website_Normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    Street_Normalized: Mapped[str | None] = mapped_column(String(150), nullable=True)
    Building_Number_Normalized: Mapped[str | None] = mapped_column(String(30), nullable=True)
    Apartment_Number_Normalized: Mapped[str | None] = mapped_column(String(30), nullable=True)
    City_Normalized: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Postal_Code_Normalized: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Country_Normalized: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Full_Address_Normalized: Mapped[str | None] = mapped_column(String(500), nullable=True)
    Preprocessing_Rules_JSON: Mapped[str | None] = mapped_column(Text, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
