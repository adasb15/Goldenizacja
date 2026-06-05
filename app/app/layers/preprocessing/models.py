from datetime import datetime

from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Unicode, UnicodeText, func
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
    Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    PESEL_Normalized: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    Serial_Number_ID_Card_Normalized: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Serial_Number_Passport_Normalized: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    First_Name_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Second_Name_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Last_Name_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Family_Name_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Full_Name_Normalized: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Birth_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Place_Of_Birth_Normalized: Mapped[str | None] = mapped_column(Unicode(150), nullable=True)
    Sex: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    Citizenship_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Phone_Normalized: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Email_Normalized: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Street_Normalized: Mapped[str | None] = mapped_column(Unicode(150), nullable=True)
    Building_Number_Normalized: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Apartment_Number_Normalized: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    City_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Postal_City_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Postal_Code_Normalized: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    District_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Province_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Country_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Full_Address_Normalized: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    Preprocessing_Rules_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
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
    Source_Record_ID: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Name_Normalized: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Short_Name_Normalized: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Legal_Entity_Type_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Registration_Country_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Establishment_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    NIP_Normalized: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    REGON_Normalized: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    KRS_Normalized: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    LEI_Normalized: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Register_Status_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Registration_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Deregistration_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Decision_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Decision_Number_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Register_Number_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Bank_Accounts_Normalized_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Has_Virtual_Accounts: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    Business_Scope_Normalized: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Ownership_Form_Normalized: Mapped[str | None] = mapped_column(Unicode(150), nullable=True)
    Municipality_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Phone_Normalized: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Email_Normalized: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Website_Normalized: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Agent_Type_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Insurance_Company_Normalized: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Related_Persons_Normalized_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Related_Parties_Normalized_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Registration_Status_Normalized: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Last_Update_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Next_Renewal_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Managing_LOU_Normalized: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Validation_Sources_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Validation_Authority_ID_Normalized: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    Validation_Authority_Entity_ID_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Direct_Parent_LEI_Normalized: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    Direct_Parent_Name_Normalized: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Direct_Parent_Relationship_Type_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Direct_Parent_Relationship_Status_Normalized: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Direct_Parent_Relationship_Start_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Direct_Parent_Relationship_End_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Ultimate_Parent_LEI_Normalized: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    Ultimate_Parent_Name_Normalized: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    Ultimate_Parent_Relationship_Type_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Ultimate_Parent_Relationship_Status_Normalized: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    Ultimate_Parent_Relationship_Start_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Ultimate_Parent_Relationship_End_Date: Mapped[date | None] = mapped_column(Date, nullable=True)
    Street_Normalized: Mapped[str | None] = mapped_column(Unicode(150), nullable=True)
    Building_Number_Normalized: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    Apartment_Number_Normalized: Mapped[str | None] = mapped_column(Unicode(30), nullable=True)
    City_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Postal_City_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Postal_Code_Normalized: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    District_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Province_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Country_Normalized: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    Full_Address_Normalized: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    Preprocessing_Rules_JSON: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
