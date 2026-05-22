import unittest
from types import SimpleNamespace

from app.layers.integration_golden.service import (
    FIELD_RULES_BY_ENTITY_TYPE,
    MatchDecision,
    MatchingPairLimitExceededError,
    choose_trusted_value,
    find_match_candidates,
    score_match,
)


class IntegrationGoldenMatchingTests(unittest.TestCase):
    def test_auto_merges_person_by_pesel_even_when_dynamic_data_changes(self) -> None:
        left = SimpleNamespace(
            PESEL_Normalized="90010112345",
            First_Name_Normalized="JAN",
            Last_Name_Normalized="KOWALSKI",
            Phone_Normalized="+48500100100",
            Email_Normalized="jan@example.test",
        )
        right = SimpleNamespace(
            PESEL_Normalized="90010112345",
            First_Name_Normalized="JAN",
            Last_Name_Normalized="KOWALSKI",
            Phone_Normalized="+48600200200",
            Email_Normalized="jan.kowalski@example.test",
        )

        result = score_match(left, right, "PERSON")

        self.assertEqual(result.decision, MatchDecision.AUTO_MERGE)
        self.assertIn("PESEL", result.strong_match_fields)
        self.assertGreaterEqual(result.score, 0.95)

    def test_keeps_same_pesel_in_review_when_stable_fields_conflict(self) -> None:
        left = SimpleNamespace(
            PESEL_Normalized="90010112345",
            Birth_Date="1990-01-01",
            First_Name_Normalized="JAN",
            Last_Name_Normalized="KOWALSKI",
        )
        right = SimpleNamespace(
            PESEL_Normalized="90010112345",
            Birth_Date="1985-05-05",
            First_Name_Normalized="ADAM",
            Last_Name_Normalized="NOWAK",
        )

        result = score_match(left, right, "PERSON")

        self.assertEqual(result.decision, MatchDecision.REVIEW)
        self.assertIn("PESEL", result.strong_match_fields)
        self.assertIn("Birth_Date", result.conflict_fields)
        self.assertIn("Last_Name", result.conflict_fields)

    def test_catches_person_when_pesel_has_typo_but_stable_fields_match(self) -> None:
        left = SimpleNamespace(
            PESEL_Normalized="90010112345",
            Birth_Date="1990-01-01",
            First_Name_Normalized="JAN",
            Last_Name_Normalized="KOWALSKI",
            Full_Name_Normalized="JAN KOWALSKI",
            Place_Of_Birth_Normalized="WARSZAWA",
        )
        right = SimpleNamespace(
            PESEL_Normalized="90010112346",
            Birth_Date="1990-01-01",
            First_Name_Normalized="JAN",
            Last_Name_Normalized="KOWALSKI",
            Full_Name_Normalized="JAN KOWALSKI",
            Place_Of_Birth_Normalized="WARSZAWA",
        )

        result = score_match(left, right, "PERSON")

        self.assertEqual(result.decision, MatchDecision.REVIEW)
        self.assertEqual(result.strong_match_fields, ())
        self.assertIn("PESEL", result.conflict_fields)
        self.assertGreaterEqual(result.score, 0.70)

    def test_marks_party_for_review_on_name_and_address_similarity_without_strong_id(self) -> None:
        left = {
            "Name_Normalized": "ALFA TRADE SP. Z O.O.",
            "Short_Name_Normalized": "ALFA TRADE",
            "Legal_Entity_Type_Normalized": "SP. Z O.O.",
            "Street_Normalized": "KWIATOWA",
            "Building_Number_Normalized": "10",
            "City_Normalized": "WARSZAWA",
            "Postal_Code_Normalized": "00-001",
            "Country_Normalized": "PL",
        }
        right = {
            "Name_Normalized": "ALFA TRADE SERVICES SP ZOO",
            "Short_Name_Normalized": "ALFA SERVICES",
            "Legal_Entity_Type_Normalized": "SP. Z O.O.",
            "Street_Normalized": "KWIATOWA",
            "Building_Number_Normalized": "12",
            "City_Normalized": "WARSZAWA",
            "Postal_Code_Normalized": "00-001",
            "Country_Normalized": "PL",
        }

        result = score_match(left, right, "PARTY")

        self.assertEqual(result.decision, MatchDecision.REVIEW)
        self.assertGreaterEqual(result.score, 0.70)
        self.assertLess(result.score, 0.90)

    def test_keeps_party_with_conflicting_strong_identifier_in_review(self) -> None:
        left = {
            "NIP_Normalized": "1234567890",
            "REGON_Normalized": "111222333",
            "Name_Normalized": "BETA FINANCE S.A.",
        }
        right = {
            "NIP_Normalized": "1234567890",
            "REGON_Normalized": "999888777",
            "Name_Normalized": "BETA FINANCE SA",
        }

        result = score_match(left, right, "PARTY")

        self.assertEqual(result.decision, MatchDecision.REVIEW)
        self.assertIn("NIP", result.strong_match_fields)
        self.assertIn("REGON", result.conflict_fields)

    def test_chooses_value_from_more_trusted_source(self) -> None:
        value = choose_trusted_value(
            [
                ("WWW_FORM", "Jan Nowak"),
                ("PESEL", "Jan Kowalski"),
            ]
        )

        self.assertEqual(value, "Jan Kowalski")

    def test_weights_follow_attribute_stability(self) -> None:
        person_weights = {rule.name: rule.weight for rule in FIELD_RULES_BY_ENTITY_TYPE["PERSON"]}
        party_weights = {rule.name: rule.weight for rule in FIELD_RULES_BY_ENTITY_TYPE["PARTY"]}

        self.assertGreater(person_weights["PESEL"], person_weights["Last_Name"])
        self.assertGreater(person_weights["Sex"], person_weights["Last_Name"])
        self.assertGreater(person_weights["Place_Of_Birth"], person_weights["Last_Name"])
        self.assertGreater(person_weights["Birth_Date"], person_weights["Email_Address"])
        self.assertGreater(person_weights["Last_Name"], person_weights["Phone_Number"])
        self.assertGreater(person_weights["Country"], person_weights["Street"])
        self.assertGreater(person_weights["Country"], person_weights["Province"])
        self.assertGreater(person_weights["Province"], person_weights["City"])
        self.assertGreater(person_weights["City"], person_weights["Street"])
        self.assertEqual(person_weights["District"], person_weights["Postal_Code"])
        self.assertEqual(person_weights["District"], person_weights["City"])
        self.assertEqual(person_weights["District"], person_weights["Postal_City"])
        self.assertEqual(person_weights["Street"], person_weights["Building_Number"])
        self.assertEqual(person_weights["Street"], person_weights["Apartment_Number"])
        self.assertGreater(person_weights["Street"], person_weights["Full_Address"])
        self.assertGreater(party_weights["NIP"], party_weights["Name"])
        self.assertGreater(party_weights["Establishment_Date"], party_weights["Full_Address"])
        self.assertGreater(party_weights["Name"], party_weights["Phone_Number"])
        self.assertGreater(party_weights["Country"], party_weights["Street"])
        self.assertGreater(party_weights["Country"], party_weights["Province"])
        self.assertGreater(party_weights["Province"], party_weights["City"])
        self.assertGreater(party_weights["City"], party_weights["Street"])
        self.assertEqual(party_weights["District"], party_weights["Postal_Code"])
        self.assertEqual(party_weights["District"], party_weights["City"])
        self.assertEqual(party_weights["District"], party_weights["Postal_City"])
        self.assertEqual(party_weights["Street"], party_weights["Building_Number"])
        self.assertEqual(party_weights["Street"], party_weights["Apartment_Number"])
        self.assertGreater(party_weights["Street"], party_weights["Full_Address"])

    def test_finds_match_candidates_from_preprocessed_records(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                Staging_ID=10,
                RawFile_ID=100,
                Source_Record_ID="A",
                NIP_Normalized="1234567890",
                Name_Normalized="ALFA TRADE SP ZOO",
            ),
            SimpleNamespace(
                Preprocessed_ID=2,
                Staging_ID=20,
                RawFile_ID=200,
                Source_Record_ID="B",
                NIP_Normalized="1234567890",
                Name_Normalized="ALFA TRADE SP. Z O.O.",
            ),
            SimpleNamespace(
                Preprocessed_ID=3,
                Staging_ID=30,
                RawFile_ID=300,
                Source_Record_ID="C",
                NIP_Normalized="9999999999",
                Name_Normalized="OMEGA SERVICES",
            ),
        ]

        class Repo:
            def get_preprocessed_records(self, entity_type: str, raw_file_id: int | None = None):
                if raw_file_id is None:
                    return records
                return [record for record in records if record.RawFile_ID == raw_file_id]

        result = find_match_candidates(
            db=None,
            entity_type="PARTY",
            raw_file_id=100,
            repo=Repo(),
        )

        self.assertEqual(result.records_in_scope, 1)
        self.assertEqual(result.records_compared_against, 3)
        self.assertEqual(result.pairs_evaluated, 2)
        self.assertEqual(result.candidates_out, 1)
        self.assertEqual(result.candidates[0].decision, MatchDecision.AUTO_MERGE)
        self.assertEqual(result.candidates[0].strong_match_fields, ("NIP",))

    def test_uses_blocked_candidates_when_repository_supports_it(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                Staging_ID=10,
                RawFile_ID=100,
                Source_Record_ID="A",
                NIP_Normalized="1234567890",
                Name_Normalized="ALFA TRADE SP ZOO",
            ),
            SimpleNamespace(
                Preprocessed_ID=2,
                Staging_ID=20,
                RawFile_ID=200,
                Source_Record_ID="B",
                NIP_Normalized="1234567890",
                Name_Normalized="ALFA TRADE SP. Z O.O.",
            ),
            SimpleNamespace(
                Preprocessed_ID=3,
                Staging_ID=30,
                RawFile_ID=300,
                Source_Record_ID="C",
                NIP_Normalized="9999999999",
                Name_Normalized="OMEGA SERVICES",
            ),
        ]

        class Repo:
            def get_preprocessed_records(self, entity_type: str, raw_file_id: int | None = None):
                return [record for record in records if record.RawFile_ID == raw_file_id]

            def count_preprocessed_records(self, entity_type: str) -> int:
                return len(records)

            def get_candidate_records_for_match(self, entity_type: str, record):
                return [candidate for candidate in records if candidate.NIP_Normalized == record.NIP_Normalized]

        result = find_match_candidates(
            db=None,
            entity_type="PARTY",
            raw_file_id=100,
            repo=Repo(),
        )

        self.assertEqual(result.records_compared_against, 3)
        self.assertEqual(result.pairs_evaluated, 1)
        self.assertEqual(result.candidates_out, 1)

    def test_max_pairs_zero_disables_safety_limit(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=idx,
                Staging_ID=idx * 10,
                RawFile_ID=100 if idx == 1 else 200,
                Source_Record_ID=str(idx),
                NIP_Normalized=str(1000000000 + idx),
                Name_Normalized=f"COMPANY {idx}",
            )
            for idx in range(1, 5)
        ]

        class Repo:
            def get_preprocessed_records(self, entity_type: str, raw_file_id: int | None = None):
                if raw_file_id is None:
                    return records
                return [record for record in records if record.RawFile_ID == raw_file_id]

        with self.assertRaises(MatchingPairLimitExceededError):
            find_match_candidates(
                db=None,
                entity_type="PARTY",
                raw_file_id=100,
                repo=Repo(),
                max_pairs=1,
            )

        result = find_match_candidates(
            db=None,
            entity_type="PARTY",
            raw_file_id=100,
            repo=Repo(),
            max_pairs=0,
        )

        self.assertEqual(result.pairs_evaluated, 3)


if __name__ == "__main__":
    unittest.main()
