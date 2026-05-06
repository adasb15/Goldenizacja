import json
import unittest

from app.layers.staging_validation.mapper import (
    MISSING_COLUMNS_KEY,
    UNRECOGNIZED_COLUMNS_KEY,
    map_record_to_canonical,
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
        }
        mapping = {
            "firstname": "First_Name",
            "surname": "Last_Name",
        }

        result = map_record_to_canonical(source_record, mapping, "PERSON")

        self.assertEqual(result["First_Name"], "Jan")
        self.assertEqual(result["Last_Name"], "Kowalski")
        self.assertEqual(result[MISSING_COLUMNS_KEY], [])
        self.assertEqual(result[UNRECOGNIZED_COLUMNS_KEY], [])

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


if __name__ == "__main__":
    unittest.main()
