import json
import unittest
from types import SimpleNamespace

from app.layers.preprocessing.service import (
    build_preprocessed_record,
    normalize_email,
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
        self.assertEqual(
            split_party_name_and_legal_form("P.P.H.U. Baltic Med Supply"),
            ("P.P.H.U. Baltic Med Supply", None),
        )
        self.assertEqual(
            split_party_name_and_legal_form("Baltic Med Supply - PPHU"),
            ("Baltic Med Supply - PPHU", None),
        )

    def test_keeps_trade_name_without_legal_form(self) -> None:
        self.assertEqual(split_party_name_and_legal_form("Facebook - Meta"), ("Facebook - Meta", None))

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
            Street="Bałtycka 136/11, 66-157 Bydgoszcz",
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
        self.assertEqual(preprocessed["Street_Normalized"], "UL BAŁTYCKA")
        self.assertEqual(preprocessed["Building_Number_Normalized"], "136")
        self.assertEqual(preprocessed["Apartment_Number_Normalized"], "11")
        self.assertEqual(preprocessed["Postal_Code_Normalized"], "66-157")
        self.assertEqual(preprocessed["City_Normalized"], "BYDGOSZCZ")
        self.assertEqual(preprocessed["Country_Normalized"], "PL")

    def test_splits_estate_prefix_as_street(self) -> None:
        staging_record = SimpleNamespace(
            Staging_ID=15,
            ImportBatch_ID=25,
            RawFile_ID=35,
            Source_Record_ID="SRC-15",
            Name="Example sp. z o.o.",
            Short_Name=None,
            Legal_Entity_Type=None,
            Identifiers_JSON=json.dumps({"NIP": "1234567890"}),
            Phone_Number=None,
            Email_Address=None,
            Website=None,
            Street="os. Marszałkowskie 1/1, 00-590 Warszawa",
            Building_Number=None,
            Apartment_Number=None,
            City=None,
            Postal_City=None,
            Postal_Code=None,
            Country="PL",
        )

        preprocessed = build_preprocessed_record(staging_record, "PARTY")

        self.assertEqual(preprocessed["Street_Normalized"], "OS MARSZAŁKOWSKIE")
        self.assertEqual(preprocessed["Building_Number_Normalized"], "1")
        self.assertEqual(preprocessed["Apartment_Number_Normalized"], "1")
        self.assertEqual(preprocessed["Postal_Code_Normalized"], "00-590")
        self.assertEqual(preprocessed["City_Normalized"], "WARSZAWA")

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
                "Krajowy Rejestr Sądowy (KRS) (Ministerstwo Sprawiedliwości) | "
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
                "Krajowy Rejestr Urzędowy Podmiotów Gospodarki Narodowej REGON "
                "(Główny Urząd Statystyczny) | Poland | RA000484"
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
        self.assertEqual(preprocessed["Street_Normalized"], "UL ŁĄKOWA")
        self.assertEqual(preprocessed["Building_Number_Normalized"], "38")
        self.assertEqual(preprocessed["Apartment_Number_Normalized"], "43")
        self.assertEqual(preprocessed["Postal_Code_Normalized"], "44-508")
        self.assertEqual(preprocessed["City_Normalized"], "RZESZÓW")


if __name__ == "__main__":
    unittest.main()

