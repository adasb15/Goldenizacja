import json
import unittest
from types import SimpleNamespace

from app.layers.preprocessing.service import (
    build_preprocessed_record,
    normalize_email,
    normalize_phone,
    normalize_text_key,
)


class PreprocessingTests(unittest.TestCase):
    def test_normalizes_text_for_matching(self) -> None:
        self.assertEqual(normalize_text_key("  Łódź sp. z o.o.\n"), "LÓDŹ SP. Z O.O.")

    def test_normalizes_phone_and_email(self) -> None:
        self.assertEqual(normalize_phone("502 693 570"), "+48502693570")
        self.assertEqual(normalize_email(" Jan.Kowalski@Example.TEST "), "jan.kowalski@example.test")

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
        self.assertEqual(preprocessed["Street_Normalized"], "BAŁTYCKA")
        self.assertEqual(preprocessed["Building_Number_Normalized"], "136")
        self.assertEqual(preprocessed["Apartment_Number_Normalized"], "11")
        self.assertEqual(preprocessed["Postal_Code_Normalized"], "66-157")
        self.assertEqual(preprocessed["City_Normalized"], "BYDGOSZCZ")
        self.assertEqual(preprocessed["Country_Normalized"], "PL")

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

        self.assertEqual(preprocessed["Full_Name_Normalized"], "ŁUKASZ ZÓŁC")
        self.assertEqual(preprocessed["Street_Normalized"], "ŁĄKOWA")
        self.assertEqual(preprocessed["Building_Number_Normalized"], "38")
        self.assertEqual(preprocessed["Apartment_Number_Normalized"], "43")
        self.assertEqual(preprocessed["Postal_Code_Normalized"], "44-508")
        self.assertEqual(preprocessed["City_Normalized"], "RZESZÓW")


if __name__ == "__main__":
    unittest.main()
