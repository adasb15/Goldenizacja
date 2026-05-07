import json
import unittest
from datetime import date

from app.layers.staging_validation.mapper import (
    MISSING_COLUMNS_KEY,
    UNRECOGNIZED_COLUMNS_KEY,
    map_record_to_canonical,
)
from app.layers.staging_validation.service import (
    RawFileAlreadyLoadedToStagingError,
    build_staging_record,
    load_raw_file_to_staging,
    parse_raw_file_records,
)


# python -m unittest discover -s tests -p test_staging_mapper.py -v

class StagingMapperTests(unittest.TestCase):
    def test_maps_party_record_and_builds_identifiers_json(self) -> None:
        source_record = {
            "nazwa": "ABC Sp. z o.o.",
            "nip": "1234567890",
            "regon": "123456789",
            "unknown_col": "left for report",
        }
        mapping = {
            "nazwa": "Name",
            "nip": "Identifiers_JSON",
            "regon": "Identifiers_JSON",
            "missing_source": "City",
        }

        result = map_record_to_canonical(source_record, mapping, "PARTY")

        self.assertEqual(result["Name"], "ABC Sp. z o.o.")
        self.assertEqual(
            json.loads(result["Identifiers_JSON"]),
            {"NIP": "1234567890", "REGON": "123456789"},
        )
        self.assertEqual(json.loads(result["Raw_Record_JSON"]), source_record)
        self.assertEqual(result[MISSING_COLUMNS_KEY], ["missing_source"])
        self.assertEqual(result[UNRECOGNIZED_COLUMNS_KEY], ["unknown_col"])

    def test_maps_person_record_with_case_insensitive_source_columns(self) -> None:
        source_record = {
            "firstName": "Jan",
            "SURNAME": "Kowalski",
            "NumerPaszportu": "AB1234567",
        }
        mapping = {
            "firstname": "First_Name",
            "surname": "Last_Name",
            "NumerPaszportu": "Serial_Number_Passport",
        }

        result = map_record_to_canonical(source_record, mapping, "PERSON")

        self.assertEqual(result["First_Name"], "Jan")
        self.assertEqual(result["Last_Name"], "Kowalski")
        self.assertEqual(result["Serial_Number_Passport"], "AB1234567")
        self.assertEqual(result[MISSING_COLUMNS_KEY], [])
        self.assertEqual(result[UNRECOGNIZED_COLUMNS_KEY], [])

    def test_maps_person_sex_to_bit_values(self) -> None:
        female_record = build_staging_record(
            canonical_record={
                "PESEL": "90010112345",
                "Sex": "kobieta",
            },
            source_record={"PESEL": "90010112345"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PERSON",
            row_number=1,
        )
        male_record = build_staging_record(
            canonical_record={
                "PESEL": "90010112346",
                "Sex": "M",
            },
            source_record={"PESEL": "90010112346"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PERSON",
            row_number=2,
        )

        self.assertEqual(female_record["Sex"], True)
        self.assertEqual(male_record["Sex"], False)

    def test_maps_nested_json_paths(self) -> None:
        source_record = {
            "firma": {
                "nazwa": "Nested Company",
                "wlasciciel": {
                    "imie": "Anna",
                },
            }
        }
        mapping = {
            "firma.wlasciciel.imie": "First_Name",
        }

        result = map_record_to_canonical(source_record, mapping, "PERSON")

        self.assertEqual(result["First_Name"], "Anna")
        self.assertEqual(result[MISSING_COLUMNS_KEY], [])
        self.assertEqual(result[UNRECOGNIZED_COLUMNS_KEY], [])

    def test_maps_flat_dot_notation_columns_from_csv(self) -> None:
        source_record = {
            "firma.nazwa": "CSV Company",
            "firma.nip": "1234567890",
            "firma.regon": "987654321",
            "firma.extra": "not mapped",
        }
        mapping = {
            "firma.nazwa": "Name",
            "firma.nip": "Identifiers_JSON",
            "firma.regon": "Identifiers_JSON",
        }

        result = map_record_to_canonical(source_record, mapping, "PARTY")

        self.assertEqual(result["Name"], "CSV Company")
        self.assertEqual(
            json.loads(result["Identifiers_JSON"]),
            {"NIP": "1234567890", "REGON": "987654321"},
        )
        self.assertEqual(result[MISSING_COLUMNS_KEY], [])
        self.assertEqual(result[UNRECOGNIZED_COLUMNS_KEY], ["firma.extra"])

    def test_keeps_first_non_empty_value_for_duplicate_canonical_columns(self) -> None:
        source_record = {
            "empty_name": "",
            "nazwa_firmy": "Fallback Company",
        }
        mapping = {
            "empty_name": "Name",
            "nazwa_firmy": "Name",
        }

        result = map_record_to_canonical(source_record, mapping, "PARTY")

        self.assertEqual(result["Name"], "Fallback Company")

    def test_maps_flat_gleif_record(self) -> None:
        source_record = {
            "LEI": "529900T8BM49AURSDO55",
            "LegalName": "GLEIF Company",
            "LegalJurisdiction": "PL",
            "EntityLegalFormCode": "PL-SPZOO",
            "InitialRegistrationDate": "2020-01-15T00:00:00Z",
            "FirstAddressLine": "Kwiatowa 1",
            "City": "Warszawa",
            "PostalCode": "00-001",
            "Country": "PL",
            "DirectParentLEI": "DIRECTPARENT123456789",
            "DirectParentName": "Parent Company",
            "DirectParentRelationshipStatus": "ACTIVE",
            "DirectParentRelationshipStartDate": "2021-02-03T00:00:00Z",
            "UltimateParentLEI": "",
        }
        mapping = {
            "LegalName": "Name",
            "LegalJurisdiction": "Registration_Country",
            "EntityLegalFormCode": "Legal_Entity_Type",
            "InitialRegistrationDate": "Establishment_Date",
            "FirstAddressLine": "Street",
            "City": "City",
            "PostalCode": "Postal_Code",
            "Country": "Country",
            "LEI": "Identifiers_JSON",
            "DirectParentLEI": "Direct_Parent_LEI",
            "DirectParentName": "Direct_Parent_Name",
            "DirectParentRelationshipStatus": "Direct_Parent_Relationship_Status",
            "DirectParentRelationshipStartDate": "Direct_Parent_Relationship_Start_Date",
            "UltimateParentLEI": "Ultimate_Parent_LEI",
        }

        result = map_record_to_canonical(source_record, mapping, "PARTY")

        self.assertEqual(result["Name"], "GLEIF Company")
        self.assertEqual(result["Registration_Country"], "PL")
        self.assertEqual(result["Legal_Entity_Type"], "PL-SPZOO")
        self.assertEqual(result["City"], "Warszawa")
        self.assertEqual(
            json.loads(result["Identifiers_JSON"]),
            {"LEI": "529900T8BM49AURSDO55"},
        )
        self.assertEqual(result["Direct_Parent_LEI"], "DIRECTPARENT123456789")
        self.assertEqual(result["Direct_Parent_Name"], "Parent Company")
        self.assertEqual(result["Direct_Parent_Relationship_Status"], "ACTIVE")
        self.assertEqual(
            result["Direct_Parent_Relationship_Start_Date"],
            "2021-02-03T00:00:00Z",
        )
        self.assertEqual(result["Ultimate_Parent_LEI"], None)

    def test_builds_gleif_staging_record_with_relationship_dates(self) -> None:
        canonical_record = {
            "Name": "GLEIF Company",
            "Establishment_Date": "2020-01-15T00:00:00Z",
            "Last_Update_Date": "2024-01-10T00:00:00Z",
            "Next_Renewal_Date": "2025-01-10T00:00:00Z",
            "Direct_Parent_Relationship_Start_Date": "2021-02-03T00:00:00Z",
            "Direct_Parent_Relationship_End_Date": "",
            "Ultimate_Parent_Relationship_Start_Date": "2022-03-04T00:00:00Z",
            "Ultimate_Parent_Relationship_End_Date": None,
        }

        result = build_staging_record(
            canonical_record=canonical_record,
            source_record={"LEI": "529900T8BM49AURSDO55"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PARTY",
            row_number=3,
        )

        self.assertEqual(result["Establishment_Date"], date(2020, 1, 15))
        self.assertEqual(result["Last_Update_Date"], date(2024, 1, 10))
        self.assertEqual(result["Next_Renewal_Date"], date(2025, 1, 10))
        self.assertEqual(result["Direct_Parent_Relationship_Start_Date"], date(2021, 2, 3))
        self.assertEqual(result["Direct_Parent_Relationship_End_Date"], None)
        self.assertEqual(result["Ultimate_Parent_Relationship_Start_Date"], date(2022, 3, 4))
        self.assertEqual(result["Ultimate_Parent_Relationship_End_Date"], None)

    def test_normalizes_party_dates_and_boolean_values(self) -> None:
        result = build_staging_record(
            canonical_record={
                "Name": "Typed Company",
                "Registration_Date": "31.12.2024",
                "Decision_Date": "2024/01/10",
                "Has_Virtual_Accounts": "Prawda",
            },
            source_record={"nip": "1234567890"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PARTY",
            row_number=3,
        )

        self.assertEqual(result["Registration_Date"], date(2024, 12, 31))
        self.assertEqual(result["Decision_Date"], date(2024, 1, 10))
        self.assertEqual(result["Has_Virtual_Accounts"], True)

    def test_maps_false_boolean_values_to_bit_false(self) -> None:
        result = build_staging_record(
            canonical_record={
                "Name": "Typed Company",
                "Has_Virtual_Accounts": "nie",
            },
            source_record={"nip": "1234567890"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PARTY",
            row_number=3,
        )

        self.assertEqual(result["Has_Virtual_Accounts"], False)

    def test_builds_party_related_json_and_ignores_structured_krs_columns(self) -> None:
        source_record = {
            "nazwa": "KRS Company",
            "CzlonekZarzadu1_Imie": "Anna",
            "CzlonekZarzadu1_Nazwisko": "Nowak",
            "CzlonekZarzadu1_PESEL": "90010112345",
            "CzlonekZarzadu1_Funkcja": "PREZES",
            "CzlonekZarzadu1_DataOd": "2020-01-01",
            "WspolnikPodmiot1_Nazwa": "Parent Company",
            "WspolnikPodmiot1_KRS": "0000123456",
            "WspolnikPodmiot1_NIP": "1234567890",
            "WspolnikPodmiot1_DataOd": "2021-01-01",
        }
        canonical_record = map_record_to_canonical(
            source_record,
            {"nazwa": "Name"},
            "PARTY",
        )

        staging_record = build_staging_record(
            canonical_record=canonical_record,
            source_record=source_record,
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PARTY",
            row_number=3,
        )

        self.assertEqual(canonical_record[UNRECOGNIZED_COLUMNS_KEY], [])
        self.assertEqual(
            json.loads(staging_record["Related_Persons_JSON"]),
            [
                {
                    "role_group": "BOARD_MEMBER",
                    "slot": 1,
                    "first_name": "Anna",
                    "last_name": "Nowak",
                    "pesel": "90010112345",
                    "role_name": "PREZES",
                    "valid_from": "2020-01-01",
                }
            ],
        )
        self.assertEqual(
            json.loads(staging_record["Related_Parties_JSON"]),
            [
                {
                    "relationship_group": "PARTY_SHAREHOLDER",
                    "slot": 1,
                    "name": "Parent Company",
                    "krs": "0000123456",
                    "nip": "1234567890",
                    "valid_from": "2021-01-01",
                }
            ],
        )

    def test_normalizes_vat_bank_accounts_json(self) -> None:
        staging_record = build_staging_record(
            canonical_record={
                "Name": "VAT Company",
                "Bank_Accounts_JSON": "111, 222",
            },
            source_record={"nip": "1234567890"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PARTY",
            row_number=3,
        )

        self.assertEqual(json.loads(staging_record["Bank_Accounts_JSON"]), ["111", "222"])

    def test_preserves_party_address_line_in_staging(self) -> None:
        staging_record = build_staging_record(
            canonical_record={
                "Name": "Address Company",
                "Street": "ulica Krotka 122/64",
            },
            source_record={"nip": "1234567890"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PARTY",
            row_number=3,
        )

        self.assertEqual(staging_record["Street"], "ulica Krotka 122/64")
        self.assertIsNone(staging_record["Building_Number"])
        self.assertIsNone(staging_record["Apartment_Number"])

    def test_sanitizes_staging_text_values_before_insert(self) -> None:
        staging_record = build_staging_record(
            canonical_record={
                "Name": "\x00  Dirty Company\t",
                "Street": "\x07 ul. Testowa 12/3 \n",
            },
            source_record={"id": "\t SRC-1\x00 "},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PARTY",
            row_number=3,
        )

        self.assertEqual(staging_record["Name"], "Dirty Company")
        self.assertEqual(staging_record["Street"], "ul. Testowa 12/3")
        self.assertIsNone(staging_record["Building_Number"])
        self.assertIsNone(staging_record["Apartment_Number"])
        self.assertEqual(staging_record["Source_Record_ID"], "SRC-1")

    def test_preserves_person_address_line_in_staging(self) -> None:
        staging_record = build_staging_record(
            canonical_record={
                "PESEL": "90010112345",
                "Street": "ul. Kosciuszki 174/39",
            },
            source_record={"PESEL": "90010112345"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PERSON",
            row_number=3,
        )

        self.assertEqual(staging_record["Street"], "ul. Kosciuszki 174/39")
        self.assertIsNone(staging_record["Building_Number"])
        self.assertIsNone(staging_record["Apartment_Number"])

    def test_preserves_full_address_mapped_to_street(self) -> None:
        staging_record = build_staging_record(
            canonical_record={
                "Name": "Full Address Company",
                "Street": "Baltycka 136/11, 66-157 Bydgoszcz",
            },
            source_record={"nip": "1234567890"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PARTY",
            row_number=3,
        )

        self.assertEqual(staging_record["Street"], "Baltycka 136/11, 66-157 Bydgoszcz")
        self.assertIsNone(staging_record["Building_Number"])
        self.assertIsNone(staging_record["Apartment_Number"])
        self.assertIsNone(staging_record["Postal_Code"])
        self.assertIsNone(staging_record["City"])

    def test_preserves_full_address_mapped_to_postal_city(self) -> None:
        staging_record = build_staging_record(
            canonical_record={
                "Name": "Postal City Company",
                "Postal_City": "82-801 Krakow, ul Baltycka 152",
            },
            source_record={"nip": "1234567890"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PARTY",
            row_number=3,
        )

        self.assertIsNone(staging_record["Street"])
        self.assertIsNone(staging_record["Building_Number"])
        self.assertIsNone(staging_record["Apartment_Number"])
        self.assertIsNone(staging_record["Postal_Code"])
        self.assertIsNone(staging_record["City"])
        self.assertEqual(staging_record["Postal_City"], "82-801 Krakow, ul Baltycka 152")

    def test_preserves_city_line_even_when_it_contains_street_details(self) -> None:
        staging_record = build_staging_record(
            canonical_record={
                "PESEL": "90010112345",
                "City": "Rzeszow, ul Lakowa 38 m. 43",
                "Postal_Code": "44-508",
            },
            source_record={"PESEL": "90010112345"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PERSON",
            row_number=3,
        )

        self.assertIsNone(staging_record["Street"])
        self.assertIsNone(staging_record["Building_Number"])
        self.assertIsNone(staging_record["Apartment_Number"])
        self.assertEqual(staging_record["Postal_Code"], "44-508")
        self.assertEqual(staging_record["City"], "Rzeszow, ul Lakowa 38 m. 43")

    def test_preserves_postal_city_line_mapped_to_street(self) -> None:
        staging_record = build_staging_record(
            canonical_record={
                "PESEL": "90010112345",
                "Street": "54-172 Rzeszow",
            },
            source_record={"PESEL": "90010112345"},
            import_batch_id=1,
            raw_file_id=2,
            entity_type="PERSON",
            row_number=3,
        )

        self.assertEqual(staging_record["Street"], "54-172 Rzeszow")
        self.assertIsNone(staging_record["Postal_Code"])
        self.assertIsNone(staging_record["City"])

    def test_parses_xml_records_with_field_name_attributes(self) -> None:
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<dataset name="gleif">
  <record>
    <field name="LEI">529900T8BM49AURSDO55</field>
    <field name="LegalName">GLEIF Company</field>
  </record>
</dataset>
"""

        records = parse_raw_file_records("XML", xml_content)

        self.assertEqual(
            records,
            [{"LEI": "529900T8BM49AURSDO55", "LegalName": "GLEIF Company"}],
        )

    def test_rejects_loading_same_raw_file_to_same_staging_twice(self) -> None:
        class RawFile:
            RawFile_ID = 10
            ImportBatch_ID = 20
            File_Type = "CSV"
            File_Content = b"Name\nExisting Company\n"

        class ImportBatch:
            ImportBatch_ID = 20
            SourceSystem_ID = 30

        class Repo:
            def get_raw_file(self, raw_file_id: int) -> RawFile:
                return RawFile()

            def get_import_batch(self, import_batch_id: int) -> ImportBatch:
                return ImportBatch()

            def count_staging_records_for_raw_file(self, raw_file_id: int, entity_type: str) -> int:
                return 1

            def rollback(self) -> None:
                pass

        with self.assertRaises(RawFileAlreadyLoadedToStagingError):
            load_raw_file_to_staging(
                db=None,
                raw_file_id=10,
                entity_type="PARTY",
                repo=Repo(),
            )


if __name__ == "__main__":
    unittest.main()
