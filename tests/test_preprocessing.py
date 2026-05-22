import json
import unittest
from types import SimpleNamespace

from app.layers.preprocessing.service import (
    build_preprocessed_record,
    normalize_email,
    normalize_legal_entity_type,
    normalize_phone,
    normalize_text_key,
    split_party_name_and_legal_form,
)


class PreprocessingTests(unittest.TestCase):
    def test_normalizes_text_for_matching(self) -> None:
        self.assertEqual(normalize_text_key("  Łódź sp. z o.o.\n"), "ŁÓDŹ SP. Z O.O.")

    def test_normalizes_phone_and_email(self) -> None:
        self.assertEqual(normalize_phone("502 693 570"), "+48502693570")
        self.assertEqual(normalize_email(" Jan.Kowalski@Example.TEST "), "jan.kowalski@example.test")

    def test_keeps_pphu_as_part_of_party_name(self) -> None:
        self.assertEqual(split_party_name_and_legal_form("P.P.H.U. Baltic Med Supply"), ("P.P.H.U. Baltic Med Supply", None))
        self.assertEqual(split_party_name_and_legal_form("Baltic Med Supply - PPHU"), ("Baltic Med Supply - PPHU", None))

    def test_keeps_trade_name_without_legal_form(self) -> None:
        self.assertEqual(split_party_name_and_legal_form("Facebook - Meta"), ("Facebook - Meta", None))

    def test_normalizes_oracle_legal_form_codes(self) -> None:
        self.assertEqual(normalize_legal_entity_type("LLC_PL"), "SP. Z O.O.")
        self.assertEqual(normalize_legal_entity_type("JSC_PL"), "S.A.")

    def test_builds_party_preprocessed_record_with_address_split(self) -> None:
        staging_record = SimpleNamespace(
            Staging_ID=10,
            ImportBatch_ID=20,
            RawFile_ID=30,
            Source_Record_ID="SRC-1",
            Name="  Głogowska Spółka Akcyjna ",
            Short_Name="Głogowska SA",
            Legal_Entity_Type="Spółka akcyjna",
            Identifiers_JSON=json.dumps(
                {
                    "NIP": "123-456-78-90",
                    "REGON": " 123456789 ",
                    "KRS": "0000123456",
                    "LEI": "529900T8BM49AURSDO55",
                }
            ),
            Phone_Number="+48 502 693 570",
            Email_Address="INFO@EXAMPLE.TEST",
            Website="https://www.example.test",
            Street="Baltycka 136/11, 66-157 Bydgoszcz",
            Building_Number=None,
            Apartment_Number=None,
            City=None,
            Postal_City=None,
            Postal_Code=None,
            Country="PL",
        )

        preprocessed = build_preprocessed_record(staging_record, "PARTY")

        self.assertEqual(preprocessed["Name_Normalized"], "GŁOGOWSKA SPÓŁKA AKCYJNA")
        self.assertEqual(preprocessed["NIP_Normalized"], "1234567890")
        self.assertEqual(preprocessed["Street_Normalized"], "BALTYCKA")
        self.assertEqual(preprocessed["Building_Number_Normalized"], "136")
        self.assertEqual(preprocessed["Apartment_Number_Normalized"], "11")
        self.assertEqual(preprocessed["Postal_Code_Normalized"], "66-157")
        self.assertEqual(preprocessed["City_Normalized"], "BYDGOSZCZ")
        self.assertEqual(preprocessed["Country_Normalized"], "PL")

    def test_builds_party_preprocessed_record_with_oracle_legal_form_code(self) -> None:
        staging_record = SimpleNamespace(
            Staging_ID=15,
            ImportBatch_ID=25,
            RawFile_ID=35,
            Source_Record_ID="IC-10001",
            Name="Facebook Meta Sp. z o.o.",
            Short_Name="Facebook Meta",
            Legal_Entity_Type="LLC_PL",
            Identifiers_JSON=json.dumps({"NIP": "525-234-56-78"}),
            Phone_Number=None,
            Email_Address=None,
            Website=None,
            Street=None,
            Building_Number=None,
            Apartment_Number=None,
            City=None,
            Postal_City=None,
            Postal_Code=None,
            Country="PL",
        )

        preprocessed = build_preprocessed_record(staging_record, "PARTY")

        self.assertEqual(preprocessed["Legal_Entity_Type_Normalized"], "SP. Z O.O.")

    def test_builds_party_identifiers_from_gleif_registered_at_krs(self) -> None:
        staging_record = SimpleNamespace(
            Staging_ID=12,
            ImportBatch_ID=22,
            RawFile_ID=32,
            Source_Record_ID="529900T8BM49AURSDO55",
            Name="Facebook - Meta",
            Short_Name=None,
            Legal_Entity_Type=None,
            Identifiers_JSON=json.dumps({"LEI": "529900T8BM49AURSDO55"}),
            Validation_Authority_ID=(
                "National Court Register (Ministry of Justice) | "
                "Krajowy Rejestr Sadowy (KRS) (Ministerstwo Sprawiedliwosci) | "
                "Poland | RA000466"
            ),
            Validation_Authority_Entity_ID="0000750893",
            Phone_Number=None,
            Email_Address=None,
            Website=None,
            Street=None,
            Building_Number=None,
            Apartment_Number=None,
            City=None,
            Postal_City=None,
            Postal_Code=None,
            Country="PL",
        )

        preprocessed = build_preprocessed_record(staging_record, "PARTY")

        self.assertEqual(preprocessed["KRS_Normalized"], "0000750893")
        self.assertIsNone(preprocessed["REGON_Normalized"])
        self.assertEqual(preprocessed["LEI_Normalized"], "529900T8BM49AURSDO55")

    def test_builds_party_identifiers_from_gleif_registered_at_regon(self) -> None:
        staging_record = SimpleNamespace(
            Staging_ID=13,
            ImportBatch_ID=23,
            RawFile_ID=33,
            Source_Record_ID="259400T8BM49AURSDO55",
            Name="P.P.H.U. Baltic Med Supply",
            Short_Name=None,
            Legal_Entity_Type=None,
            Identifiers_JSON=json.dumps({"LEI": "259400T8BM49AURSDO55"}),
            Validation_Authority_ID=(
                "National Official Business Register (Central Statistical Office) | "
                "Krajowy Rejestr Urzedowy Podmiotow Gospodarki Narodowej REGON "
                "(Glowny Urzad Statystyczny) | Poland | RA000484"
            ),
            Validation_Authority_Entity_ID="235-043-036",
            Phone_Number=None,
            Email_Address=None,
            Website=None,
            Street=None,
            Building_Number=None,
            Apartment_Number=None,
            City=None,
            Postal_City=None,
            Postal_Code=None,
            Country="PL",
        )

        preprocessed = build_preprocessed_record(staging_record, "PARTY")

        self.assertEqual(preprocessed["REGON_Normalized"], "235043036")
        self.assertIsNone(preprocessed["KRS_Normalized"])
        self.assertEqual(preprocessed["Short_Name_Normalized"], "P.P.H.U. BALTIC MED SUPPLY")

    def test_gleif_registered_as_does_not_override_existing_identifier(self) -> None:
        staging_record = SimpleNamespace(
            Staging_ID=14,
            ImportBatch_ID=24,
            RawFile_ID=34,
            Source_Record_ID="SRC-14",
            Name="Example sp. z o.o.",
            Short_Name=None,
            Legal_Entity_Type=None,
            Identifiers_JSON=json.dumps({"KRS": "0000001111", "LEI": "111100T8BM49AURSDO55"}),
            Validation_Authority_ID="National Court Register | KRS | Poland | RA000466",
            Validation_Authority_Entity_ID="0000750893",
            Phone_Number=None,
            Email_Address=None,
            Website=None,
            Street=None,
            Building_Number=None,
            Apartment_Number=None,
            City=None,
            Postal_City=None,
            Postal_Code=None,
            Country="PL",
        )

        preprocessed = build_preprocessed_record(staging_record, "PARTY")

        self.assertEqual(preprocessed["KRS_Normalized"], "0000001111")

    def test_builds_person_preprocessed_record_from_city_street_line(self) -> None:
        staging_record = SimpleNamespace(
            Staging_ID=11,
            ImportBatch_ID=21,
            RawFile_ID=31,
            Source_Record_ID="90010112345",
            PESEL="90010112345",
            First_Name="Łukasz",
            Second_Name=None,
            Last_Name="Żółć",
            Family_Name="Żółć",
            Phone_Number="502 693 570",
            Email_Address="LUKASZ@example.test",
            Street=None,
            Building_Number=None,
            Apartment_Number=None,
            City="Rzeszów, ul Łąkowa 38 m. 43",
            Postal_City=None,
            Postal_Code="44508",
            Country="PL",
        )

        preprocessed = build_preprocessed_record(staging_record, "PERSON")

        self.assertEqual(preprocessed["Full_Name_Normalized"], "ŁUKASZ ŻÓŁĆ")
        self.assertEqual(preprocessed["Street_Normalized"], "ŁĄKOWA")
        self.assertEqual(preprocessed["Building_Number_Normalized"], "38")
        self.assertEqual(preprocessed["Apartment_Number_Normalized"], "43")
        self.assertEqual(preprocessed["Postal_Code_Normalized"], "44-508")
        self.assertEqual(preprocessed["City_Normalized"], "RZESZÓW")


class ExtendedPreprocessingMatchingFieldTests(unittest.TestCase):
    def test_builds_person_preprocessed_record_with_extended_matching_fields(self) -> None:
        staging_record = SimpleNamespace(
            Staging_ID=17,
            ImportBatch_ID=27,
            RawFile_ID=37,
            Source_Record_ID="SRC-17",
            PESEL="90010112345",
            Serial_Number_ID_Card="ABC 123456",
            Serial_Number_Passport="PA 987654",
            First_Name="Anna",
            Second_Name="Maria",
            Last_Name="Nowak",
            Family_Name="Kowalska",
            Birth_Date=None,
            Place_Of_Birth="Warszawa",
            Sex=True,
            Citizenship="PL",
            Phone_Number=None,
            Email_Address=None,
            Street="Kwiatowa 10",
            Building_Number=None,
            Apartment_Number=None,
            City="Warszawa",
            Postal_City="Warszawa",
            Postal_Code="00-001",
            District="Warszawski",
            Province="Mazowieckie",
            Country="PL",
        )

        preprocessed = build_preprocessed_record(staging_record, "PERSON")

        self.assertEqual(preprocessed["Serial_Number_ID_Card_Normalized"], "ABC123456")
        self.assertEqual(preprocessed["Serial_Number_Passport_Normalized"], "PA987654")
        self.assertEqual(preprocessed["Place_Of_Birth_Normalized"], "WARSZAWA")
        self.assertEqual(preprocessed["Sex"], True)
        self.assertEqual(preprocessed["Citizenship_Normalized"], "PL")
        self.assertEqual(preprocessed["Postal_City_Normalized"], "WARSZAWA")
        self.assertEqual(preprocessed["District_Normalized"], "WARSZAWSKI")
        self.assertEqual(preprocessed["Province_Normalized"], "MAZOWIECKIE")

    def test_builds_party_preprocessed_record_with_extended_matching_fields(self) -> None:
        staging_record = SimpleNamespace(
            Staging_ID=16,
            ImportBatch_ID=26,
            RawFile_ID=36,
            Source_Record_ID="SRC-16",
            Name="Extended Company sp. z o.o.",
            Short_Name=None,
            Legal_Entity_Type=None,
            Registration_Country="PL",
            Establishment_Date=None,
            Identifiers_JSON=json.dumps({"NIP": "123-456-78-90"}),
            Register_Status="aktywny",
            Registration_Date=None,
            Deregistration_Date=None,
            Decision_Date=None,
            Decision_Number="DEC 1/2024",
            Register_Number="REG 99",
            Bank_Accounts_JSON=json.dumps(["111", "222"]),
            Has_Virtual_Accounts=True,
            Business_Scope="Uslugi finansowe",
            Ownership_Form="prywatna",
            Municipality="Warszawa",
            Phone_Number=None,
            Email_Address=None,
            Website=None,
            Agent_Type="multiagent",
            Insurance_Company="Towarzystwo Ubezpieczen",
            Related_Persons_JSON=json.dumps([{"pesel": "90010112345"}]),
            Related_Parties_JSON=json.dumps([{"nip": "1234567890"}]),
            Registration_Status="ACTIVE",
            Last_Update_Date=None,
            Next_Renewal_Date=None,
            Managing_LOU="LOU-1",
            Validation_Sources="FULLY_CORROBORATED",
            Validation_Authority_ID="Krajowy Rejestr Sadowy",
            Validation_Authority_Entity_ID="0000123456",
            Direct_Parent_LEI="529900T8BM49AURSDO55",
            Direct_Parent_Name="Parent sp. z o.o.",
            Direct_Parent_Relationship_Type="DIRECT_ACCOUNTING_CONSOLIDATION_PARENT",
            Direct_Parent_Relationship_Status="ACTIVE",
            Direct_Parent_Relationship_Start_Date=None,
            Direct_Parent_Relationship_End_Date=None,
            Ultimate_Parent_LEI="259400T8BM49AURSDO55",
            Ultimate_Parent_Name="Ultimate Parent S.A.",
            Ultimate_Parent_Relationship_Type="ULTIMATE_ACCOUNTING_CONSOLIDATION_PARENT",
            Ultimate_Parent_Relationship_Status="ACTIVE",
            Ultimate_Parent_Relationship_Start_Date=None,
            Ultimate_Parent_Relationship_End_Date=None,
            Street="Kwiatowa 10",
            Building_Number=None,
            Apartment_Number=None,
            City="Warszawa",
            Postal_City="Warszawa",
            Postal_Code="00-001",
            District="Warszawski",
            Province="Mazowieckie",
            Country="PL",
        )

        preprocessed = build_preprocessed_record(staging_record, "PARTY")

        self.assertEqual(preprocessed["Registration_Country_Normalized"], "PL")
        self.assertEqual(preprocessed["Register_Status_Normalized"], "AKTYWNY")
        self.assertEqual(preprocessed["Decision_Number_Normalized"], "DEC12024")
        self.assertEqual(preprocessed["Register_Number_Normalized"], "REG99")
        self.assertEqual(preprocessed["Has_Virtual_Accounts"], True)
        self.assertEqual(preprocessed["Business_Scope_Normalized"], "USLUGI FINANSOWE")
        self.assertEqual(preprocessed["Ownership_Form_Normalized"], "PRYWATNA")
        self.assertEqual(preprocessed["Municipality_Normalized"], "WARSZAWA")
        self.assertEqual(preprocessed["Agent_Type_Normalized"], "MULTIAGENT")
        self.assertEqual(preprocessed["Insurance_Company_Normalized"], "TOWARZYSTWO UBEZPIECZEN")
        self.assertEqual(preprocessed["Validation_Authority_Entity_ID_Normalized"], "0000123456")
        self.assertEqual(preprocessed["Direct_Parent_LEI_Normalized"], "529900T8BM49AURSDO55")
        self.assertEqual(preprocessed["Ultimate_Parent_LEI_Normalized"], "259400T8BM49AURSDO55")
        self.assertEqual(preprocessed["District_Normalized"], "WARSZAWSKI")
        self.assertEqual(preprocessed["Province_Normalized"], "MAZOWIECKIE")


if __name__ == "__main__":
    unittest.main()
