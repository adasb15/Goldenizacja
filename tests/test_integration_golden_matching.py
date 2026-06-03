from datetime import datetime
import unittest
from types import SimpleNamespace

from app.layers.integration_golden.service import (
    FIELD_RULES_BY_ENTITY_TYPE,
    MatchDecision,
    MatchingPairLimitExceededError,
    build_entity_groups,
    choose_trusted_value,
    find_match_candidates,
    get_source_priority_order,
    get_source_priority_rank,
    group_auto_merge_candidates,
    refine_match_candidates_with_jaro_winkler,
    score_jaro_winkler_match,
    score_match,
    select_survivor_value,
    SurvivorValueCandidate,
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

    def test_auto_merges_person_when_only_family_name_has_typo(self) -> None:
        left = SimpleNamespace(
            PESEL_Normalized="74042826025",
            Serial_Number_ID_Card_Normalized="BAI679005",
            Serial_Number_Passport_Normalized="PL0346801",
            Birth_Date="1974-04-28",
            First_Name_Normalized="PAULINA",
            Second_Name_Normalized="IWONA",
            Last_Name_Normalized="GRABOWSKA",
            Family_Name_Normalized="BARAN",
            Full_Name_Normalized="PAULINA IWONA GRABOWSKA",
            Place_Of_Birth_Normalized="KATOWICE",
        )
        right = SimpleNamespace(
            PESEL_Normalized="74042826025",
            Serial_Number_ID_Card_Normalized="BAI679005",
            Serial_Number_Passport_Normalized="PL0346801",
            Birth_Date="1974-04-28",
            First_Name_Normalized="PAULINA",
            Second_Name_Normalized="IWONA",
            Last_Name_Normalized="GRABOWSKA",
            Family_Name_Normalized="BRAAN",
            Full_Name_Normalized="PAULINA IWONA GRABOWSKA",
            Place_Of_Birth_Normalized="KATOWICE",
        )

        result = score_match(left, right, "PERSON")

        self.assertEqual(result.decision, MatchDecision.AUTO_MERGE)
        self.assertNotIn("Family_Name", result.conflict_fields)

    def test_keeps_same_pesel_as_candidate_when_stable_fields_conflict(self) -> None:
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

        self.assertEqual(result.decision, MatchDecision.CANDIDATE)
        self.assertIn("PESEL", result.strong_match_fields)
        self.assertIn("Birth_Date", result.conflict_fields)
        self.assertIn("Last_Name", result.conflict_fields)
        self.assertLess(result.score, 0.70)

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

    def test_rejects_person_candidate_when_many_stable_fields_conflict(self) -> None:
        left = SimpleNamespace(
            PESEL_Normalized="74042882265",
            Serial_Number_ID_Card_Normalized="ABC123456",
            Serial_Number_Passport_Normalized="PA1234567",
            Birth_Date="1974-04-28",
            First_Name_Normalized="JAN",
            Last_Name_Normalized="KOWALSKI",
            Full_Name_Normalized="JAN KOWALSKI",
            Place_Of_Birth_Normalized="WARSZAWA",
            Country_Normalized="PL",
            Phone_Normalized="500100200",
            Email_Normalized="jan.kowalski@example.test",
        )
        right = SimpleNamespace(
            PESEL_Normalized="62082861665",
            Serial_Number_ID_Card_Normalized="XYZ987654",
            Serial_Number_Passport_Normalized="PB9876543",
            Birth_Date="1962-08-28",
            First_Name_Normalized="ADAM",
            Last_Name_Normalized="NOWAK",
            Full_Name_Normalized="ADAM NOWAK",
            Place_Of_Birth_Normalized="KRAKOW",
            Country_Normalized="PL",
            Phone_Normalized="500100201",
            Email_Normalized="adam.nowak@example.test",
        )

        result = score_match(left, right, "PERSON")

        self.assertEqual(result.decision, MatchDecision.NO_MATCH)
        self.assertEqual(result.strong_match_fields, ())
        self.assertIn("PESEL", result.conflict_fields)
        self.assertIn("Birth_Date", result.conflict_fields)

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
            "Establishment_Date": "2020-01-01",
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
            "Establishment_Date": "2020-01-01",
        }

        result = score_match(left, right, "PARTY")

        self.assertEqual(result.decision, MatchDecision.REVIEW)
        self.assertGreaterEqual(result.score, 0.70)
        self.assertLess(result.score, 0.90)

    def test_keeps_lower_levenshtein_match_as_candidate_for_later_stages(self) -> None:
        left = {
            "Name_Normalized": "ALFA TRADE SPOLKA Z OGRANICZONA ODPOWIEDZIALNOSCIA",
            "City_Normalized": "WARSZAWA",
            "Country_Normalized": "PL",
        }
        right = {
            "Name_Normalized": "ALFA MARKET SPOLKA AKCYJNA",
            "City_Normalized": "WARSZAWA",
            "Country_Normalized": "PL",
        }

        result = score_match(left, right, "PARTY")

        self.assertEqual(result.decision, MatchDecision.NO_MATCH)
        self.assertLess(result.score, 0.50)

    def test_keeps_party_with_conflicting_strong_identifier_as_candidate(self) -> None:
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

        self.assertEqual(result.decision, MatchDecision.CANDIDATE)
        self.assertIn("NIP", result.strong_match_fields)
        self.assertIn("REGON", result.conflict_fields)
        self.assertLess(result.score, 0.70)

    def test_person_source_priority_prefers_pesel_for_identity_fields(self) -> None:
        priority = get_source_priority_order("PERSON", "Birth_Date")

        self.assertEqual(priority[:3], ("PESEL", "CEIDG", "INSURANCE_CORE"))
        self.assertLess(
            get_source_priority_rank("PERSON", "Birth_Date", "PESEL"),
            get_source_priority_rank("PERSON", "Birth_Date", "KNF_AGENT"),
        )

    def test_person_source_priority_prefers_ceidg_for_contact_fields(self) -> None:
        priority = get_source_priority_order("PERSON", "Email_Address")

        self.assertEqual(priority[:3], ("CEIDG", "INSURANCE_CORE", "PESEL"))
        self.assertLess(
            get_source_priority_rank("PERSON", "Email_Address", "CEIDG"),
            get_source_priority_rank("PERSON", "Email_Address", "PESEL"),
        )

    def test_party_source_priority_prefers_gleif_for_lei_fields(self) -> None:
        priority = get_source_priority_order("PARTY", "LEI")

        self.assertEqual(priority[:4], ("GLEIF", "KRS", "REGON", "VAT"))
        self.assertLess(
            get_source_priority_rank("PARTY", "LEI", "GLEIF"),
            get_source_priority_rank("PARTY", "LEI", "CEIDG"),
        )

    def test_party_source_priority_prefers_regon_for_address_fields(self) -> None:
        priority = get_source_priority_order("PARTY", "Street")

        self.assertEqual(priority[:4], ("REGON", "VAT", "CEIDG", "KRS"))
        self.assertLess(
            get_source_priority_rank("PARTY", "Street", "REGON"),
            get_source_priority_rank("PARTY", "Street", "GLEIF"),
        )

    def test_single_matching_regon_does_not_pass_when_stable_fields_conflict(self) -> None:
        left = {
            "NIP_Normalized": "1234567890",
            "REGON_Normalized": "111222333",
            "KRS_Normalized": "0000000001",
            "Name_Normalized": "ALFA TRADE SP ZOO",
            "Short_Name_Normalized": "ALFA TRADE",
            "Establishment_Date": "2020-01-01",
            "Register_Status_Normalized": "AKTYWNY",
        }
        right = {
            "NIP_Normalized": "9876543210",
            "REGON_Normalized": "111222333",
            "KRS_Normalized": "0000000999",
            "Name_Normalized": "OMEGA MARKET SA",
            "Short_Name_Normalized": "OMEGA",
            "Establishment_Date": "2015-06-30",
            "Register_Status_Normalized": "WYKRESLONY",
        }

        result = score_match(left, right, "PARTY")

        self.assertEqual(result.decision, MatchDecision.NO_MATCH)
        self.assertIn("REGON", result.strong_match_fields)
        self.assertLess(result.score, 0.50)

    def test_chooses_value_from_more_trusted_source(self) -> None:
        value = choose_trusted_value(
            [
                ("WWW_FORM", "Jan Nowak"),
                ("PESEL", "Jan Kowalski"),
            ]
        )

        self.assertEqual(value, "Jan Kowalski")

    def test_survivorship_prefers_non_empty_value(self) -> None:
        selection = select_survivor_value(
            entity_type="PERSON",
            field_name="First_Name",
            candidates=[
                SurvivorValueCandidate(
                    value="",
                    source_system_code="PESEL",
                    validation_status="PASS",
                    trust_level=90,
                ),
                SurvivorValueCandidate(
                    value="JAN",
                    source_system_code="PESEL",
                    validation_status="PASS",
                    trust_level=90,
                ),
            ],
        )

        self.assertEqual(selection.value, "JAN")
        self.assertEqual(selection.selected_by_rule, "NON_EMPTY_VALUE")

    def test_survivorship_prefers_validated_value(self) -> None:
        selection = select_survivor_value(
            entity_type="PARTY",
            field_name="NIP",
            candidates=[
                SurvivorValueCandidate(
                    value="1234567890",
                    source_system_code="VAT",
                    validation_status="ERROR",
                    trust_level=85,
                ),
                SurvivorValueCandidate(
                    value="1234567890",
                    source_system_code="VAT",
                    validation_status="PASS",
                    trust_level=85,
                ),
            ],
        )

        self.assertEqual(selection.validation_status, "PASS")
        self.assertEqual(selection.selected_by_rule, "PASSED_VALIDATION")

    def test_survivorship_uses_source_priority_before_trust_level(self) -> None:
        selection = select_survivor_value(
            entity_type="PERSON",
            field_name="Email_Address",
            candidates=[
                SurvivorValueCandidate(
                    value="jan@firma.pl",
                    source_system_code="PESEL",
                    validation_status="PASS",
                    trust_level=90,
                ),
                SurvivorValueCandidate(
                    value="jan@firma.pl",
                    source_system_code="CEIDG",
                    validation_status="PASS",
                    trust_level=80,
                ),
            ],
        )

        self.assertEqual(selection.source_system_code, "CEIDG")
        self.assertEqual(selection.selected_by_rule, "SOURCE_PRIORITY")

    def test_survivorship_uses_trust_level_when_source_priority_ties(self) -> None:
        selection = select_survivor_value(
            entity_type="PARTY",
            field_name="Related_Parties_JSON",
            candidates=[
                SurvivorValueCandidate(
                    value='["A"]',
                    source_system_code="INSURANCE_CORE",
                    validation_status="PASS",
                    trust_level=70,
                ),
                SurvivorValueCandidate(
                    value='["B"]',
                    source_system_code="INSURANCE_CORE",
                    validation_status="PASS",
                    trust_level=90,
                ),
            ],
        )

        self.assertEqual(selection.value, '["B"]')
        self.assertEqual(selection.selected_by_rule, "TRUST_LEVEL")

    def test_survivorship_prefers_newer_import_on_full_tie(self) -> None:
        selection = select_survivor_value(
            entity_type="PARTY",
            field_name="Street",
            candidates=[
                SurvivorValueCandidate(
                    value="UL KWIATOWA 1",
                    source_system_code="REGON",
                    validation_status="PASS",
                    trust_level=85,
                    import_started_at=datetime(2026, 5, 1, 10, 0, 0),
                ),
                SurvivorValueCandidate(
                    value="UL KWIATOWA 2",
                    source_system_code="REGON",
                    validation_status="PASS",
                    trust_level=85,
                    import_started_at=datetime(2026, 5, 3, 10, 0, 0),
                ),
            ],
        )

        self.assertEqual(selection.value, "UL KWIATOWA 2")
        self.assertEqual(selection.selected_by_rule, "NEWEST_IMPORT")

    def test_survivorship_prefers_teryt_confirmed_address(self) -> None:
        selection = select_survivor_value(
            entity_type="PARTY",
            field_name="Street",
            candidates=[
                SurvivorValueCandidate(
                    value="UL KWIATOWA 12",
                    source_system_code="REGON",
                    validation_status="PASS",
                    trust_level=85,
                    teryt_confirmed=False,
                ),
                SurvivorValueCandidate(
                    value="UL KWIATOWA 10",
                    source_system_code="CEIDG",
                    validation_status="PASS",
                    trust_level=80,
                    teryt_confirmed=True,
                ),
            ],
        )

        self.assertEqual(selection.value, "UL KWIATOWA 10")
        self.assertEqual(selection.teryt_confirmed, True)
        self.assertEqual(selection.selected_by_rule, "TERYT_CONFIRMED_ADDRESS")

    def test_survivorship_keeps_teryt_confirmed_candidates_in_further_tie_break(self) -> None:
        selection = select_survivor_value(
            entity_type="PARTY",
            field_name="City",
            candidates=[
                SurvivorValueCandidate(
                    value="WARSZAWA",
                    source_system_code="REGON",
                    validation_status="PASS",
                    trust_level=85,
                    teryt_confirmed=True,
                ),
                SurvivorValueCandidate(
                    value="KRAKOW",
                    source_system_code="CEIDG",
                    validation_status="PASS",
                    trust_level=80,
                    teryt_confirmed=True,
                ),
                SurvivorValueCandidate(
                    value="LODZ",
                    source_system_code="KRS",
                    validation_status="PASS",
                    trust_level=90,
                    teryt_confirmed=False,
                ),
            ],
        )

        self.assertEqual(selection.value, "WARSZAWA")
        self.assertEqual(selection.selected_by_rule, "SOURCE_PRIORITY")

    def test_weights_mix_identification_strength_and_stability(self) -> None:
        person_weights = {rule.name: rule.weight for rule in FIELD_RULES_BY_ENTITY_TYPE["PERSON"]}
        party_weights = {rule.name: rule.weight for rule in FIELD_RULES_BY_ENTITY_TYPE["PARTY"]}

        self.assertGreater(person_weights["PESEL"], person_weights["Last_Name"])
        self.assertGreater(person_weights["Full_Name"], person_weights["Sex"])
        self.assertGreater(person_weights["Birth_Date"], person_weights["Place_Of_Birth"])
        self.assertGreater(person_weights["Birth_Date"], person_weights["Email_Address"])
        self.assertGreater(person_weights["Last_Name"], person_weights["Phone_Number"])
        self.assertLess(person_weights["Country"], person_weights["Last_Name"])
        self.assertLess(person_weights["Sex"], person_weights["First_Name"])
        self.assertGreater(person_weights["Postal_Code"], person_weights["City"])
        self.assertGreater(person_weights["City"], person_weights["Province"])
        self.assertEqual(person_weights["Street"], person_weights["Building_Number"])
        self.assertGreater(person_weights["Street"], person_weights["Apartment_Number"])
        self.assertGreater(party_weights["NIP"], party_weights["Name"])
        self.assertGreater(party_weights["Establishment_Date"], party_weights["Full_Address"])
        self.assertGreater(party_weights["Name"], party_weights["Phone_Number"])
        self.assertLess(party_weights["Country"], party_weights["Name"])
        self.assertLess(party_weights["Legal_Entity_Type"], party_weights["Name"])
        self.assertLess(party_weights["Register_Status"], party_weights["Name"])
        self.assertGreater(party_weights["Postal_Code"], party_weights["City"])
        self.assertGreater(party_weights["City"], party_weights["Province"])
        self.assertEqual(party_weights["Street"], party_weights["Building_Number"])
        self.assertGreater(party_weights["Street"], party_weights["Apartment_Number"])

    def test_common_party_attributes_do_not_push_unrelated_company_above_review(self) -> None:
        left = {
            "NIP_Normalized": "1240744717",
            "KRS_Normalized": "0000007283",
            "Name_Normalized": "ZIELONY WEKTOR S A",
            "Short_Name_Normalized": "ZIELONY WEKTOR",
            "Legal_Entity_Type_Normalized": "S.A.",
            "Establishment_Date": "2018-10-12",
            "Register_Status_Normalized": "AKTYWNY",
            "Business_Scope_Normalized": "66.22.Z",
            "Ownership_Form_Normalized": "WLASNOSC PRYWATNA KRAJOWA",
            "City_Normalized": "KRAKOW",
            "Municipality_Normalized": "KRAKOW",
            "Province_Normalized": "MALOPOLSKIE",
            "Country_Normalized": "PL",
        }
        right = {
            "NIP_Normalized": "1240749999",
            "KRS_Normalized": "0000007999",
            "Name_Normalized": "ZIELONY HORYZONT S A",
            "Short_Name_Normalized": "ZIELONY HORYZONT",
            "Legal_Entity_Type_Normalized": "S.A.",
            "Establishment_Date": "2019-01-15",
            "Register_Status_Normalized": "AKTYWNY",
            "Business_Scope_Normalized": "66.22.Z",
            "Ownership_Form_Normalized": "WLASNOSC PRYWATNA KRAJOWA",
            "City_Normalized": "KRAKOW",
            "Municipality_Normalized": "KRAKOW",
            "Province_Normalized": "MALOPOLSKIE",
            "Country_Normalized": "PL",
        }

        result = score_match(left, right, "PARTY")

        self.assertLess(result.score, 0.70)
        self.assertNotEqual(result.decision, MatchDecision.REVIEW)
        self.assertIn("NIP", result.conflict_fields)
        self.assertIn("KRS", result.conflict_fields)

    def test_jaro_winkler_promotes_close_text_match_after_levenshtein(self) -> None:
        left = SimpleNamespace(
            PESEL_Normalized="90010112345",
            First_Name_Normalized="JAN",
            Last_Name_Normalized="KOWALSKI",
            Full_Name_Normalized="JAN KOWALSKI",
            Place_Of_Birth_Normalized="WARSZAWA",
        )
        right = SimpleNamespace(
            PESEL_Normalized="90010112345",
            First_Name_Normalized="JAN",
            Last_Name_Normalized="KOWALSKY",
            Full_Name_Normalized="JAN KOWALSKY",
            Place_Of_Birth_Normalized="WARSZAWA",
        )

        result = score_jaro_winkler_match(
            left,
            right,
            "PERSON",
            original_strong_fields=("PESEL",),
            original_conflict_fields=(),
            levenshtein_decision=MatchDecision.AUTO_MERGE.value,
        )

        self.assertEqual(result.decision, MatchDecision.AUTO_MERGE)
        self.assertGreaterEqual(result.score, 0.94)

    def test_jaro_winkler_rejects_weak_text_match_from_large_sieve(self) -> None:
        left = {
            "Name_Normalized": "ALFA TRADE SP ZOO",
            "City_Normalized": "WARSZAWA",
            "Street_Normalized": "KWIATOWA",
        }
        right = {
            "Name_Normalized": "OMEGA MARKET SA",
            "City_Normalized": "KRAKOW",
            "Street_Normalized": "DLUGA",
        }

        result = score_jaro_winkler_match(
            left,
            right,
            "PARTY",
            original_strong_fields=(),
            original_conflict_fields=(),
            levenshtein_decision=MatchDecision.CANDIDATE.value,
        )

        self.assertEqual(result.decision, MatchDecision.NO_MATCH)
        self.assertLess(result.score, 0.78)

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

    def test_persists_match_candidates_when_repository_supports_it(self) -> None:
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
        ]

        class Repo:
            saved = None

            def get_preprocessed_records(self, entity_type: str, raw_file_id: int | None = None):
                return [record for record in records if record.RawFile_ID == raw_file_id]

            def count_preprocessed_records(self, entity_type: str) -> int:
                return len(records)

            def get_candidate_records_for_match(self, entity_type: str, record):
                return records

            def replace_match_candidates(self, entity_type: str, raw_file_id: int | None, candidates):
                self.saved = (entity_type, raw_file_id, list(candidates))
                return len(candidates)

        repo = Repo()
        result = find_match_candidates(
            db=None,
            entity_type="PARTY",
            raw_file_id=100,
            repo=repo,
        )

        self.assertEqual(result.candidates_out, 1)
        self.assertIsNotNone(repo.saved)
        self.assertEqual(repo.saved[0], "PARTY")
        self.assertEqual(repo.saved[1], 100)
        self.assertEqual(len(repo.saved[2]), 1)

    def test_persists_match_candidate_in_canonical_direction(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=2,
                Staging_ID=20,
                RawFile_ID=200,
                Source_Record_ID="B",
                NIP_Normalized="1234567890",
                Name_Normalized="ALFA TRADE SP. Z O.O.",
            ),
            SimpleNamespace(
                Preprocessed_ID=1,
                Staging_ID=10,
                RawFile_ID=100,
                Source_Record_ID="A",
                NIP_Normalized="1234567890",
                Name_Normalized="ALFA TRADE SP ZOO",
            ),
        ]

        class Repo:
            saved = None

            def get_preprocessed_records(self, entity_type: str, raw_file_id: int | None = None):
                return [record for record in records if record.RawFile_ID == raw_file_id]

            def count_preprocessed_records(self, entity_type: str) -> int:
                return len(records)

            def get_candidate_records_for_match(self, entity_type: str, record):
                return records

            def replace_match_candidates(self, entity_type: str, raw_file_id: int | None, candidates):
                self.saved = list(candidates)
                return len(candidates)

        repo = Repo()
        find_match_candidates(
            db=None,
            entity_type="PARTY",
            raw_file_id=200,
            repo=repo,
        )

        self.assertEqual(len(repo.saved), 1)
        self.assertEqual(repo.saved[0].left_preprocessed_id, 1)
        self.assertEqual(repo.saved[0].right_preprocessed_id, 2)
        self.assertEqual(repo.saved[0].left_source_record_id, "A")
        self.assertEqual(repo.saved[0].right_source_record_id, "B")

    def test_rerun_clears_jaro_winkler_candidates_before_levenshtein_candidates(self) -> None:
        from app.layers.integration_golden.repository import IntegrationGoldenRepository

        class Db:
            def __init__(self):
                self.deleted_tables = []

            def execute(self, statement):
                self.deleted_tables.append(statement.table.name)

            def add_all(self, entities):
                pass

            def commit(self):
                pass

        db = Db()
        IntegrationGoldenRepository(db).replace_match_candidates(
            entity_type="PARTY",
            raw_file_id=100,
            candidates=[],
        )

        self.assertEqual(
            db.deleted_tables,
            ["Match_Candidate_JaroWinkler", "Match_Candidate_Levenshtein"],
        )

    def test_refines_persisted_levenshtein_candidates_with_jaro_winkler(self) -> None:
        records = {
            1: SimpleNamespace(
                Preprocessed_ID=1,
                Staging_ID=10,
                RawFile_ID=100,
                Source_Record_ID="A",
                NIP_Normalized="1234567890",
                Name_Normalized="ALFA TRADE SP ZOO",
                City_Normalized="WARSZAWA",
            ),
            2: SimpleNamespace(
                Preprocessed_ID=2,
                Staging_ID=20,
                RawFile_ID=200,
                Source_Record_ID="B",
                NIP_Normalized="1234567890",
                Name_Normalized="ALFA TRADE SP. Z O.O.",
                City_Normalized="WARSZAWA",
            ),
        }
        levenshtein_candidates = [
            SimpleNamespace(
                Match_Candidate_Levenshtein_ID=1000,
                Entity_Type="PARTY",
                RawFile_ID=100,
                Left_Preprocessed_ID=1,
                Right_Preprocessed_ID=2,
                Left_Staging_ID=10,
                Right_Staging_ID=20,
                Left_RawFile_ID=100,
                Right_RawFile_ID=200,
                Left_Source_Record_ID="A",
                Right_Source_Record_ID="B",
                Score=0.95,
                Decision=MatchDecision.AUTO_MERGE.value,
                Strong_Match_Fields_JSON='["NIP"]',
                Conflict_Fields_JSON="[]",
            )
        ]

        class Repo:
            saved = None

            def get_levenshtein_candidates(self, entity_type: str, raw_file_id: int | None = None):
                return levenshtein_candidates

            def get_preprocessed_record_by_id(self, entity_type: str, preprocessed_id: int):
                return records[preprocessed_id]

            def replace_jaro_winkler_candidates(self, entity_type: str, raw_file_id: int | None, candidates):
                self.saved = (entity_type, raw_file_id, list(candidates))
                return len(candidates)

        repo = Repo()
        result = refine_match_candidates_with_jaro_winkler(
            db=None,
            entity_type="PARTY",
            raw_file_id=100,
            repo=repo,
        )

        self.assertEqual(result.candidates_in_scope, 1)
        self.assertEqual(result.candidates_out, 1)
        self.assertIsNotNone(repo.saved)
        self.assertEqual(repo.saved[0], "PARTY")
        self.assertEqual(repo.saved[1], 100)
        self.assertEqual(repo.saved[2][0].levenshtein_candidate_id, 1000)

    def test_jaro_winkler_refinement_allows_empty_levenshtein_result(self) -> None:
        class Repo:
            saved = None

            def get_levenshtein_candidates(self, entity_type: str, raw_file_id: int | None = None):
                return []

            def replace_jaro_winkler_candidates(self, entity_type: str, raw_file_id: int | None, candidates):
                self.saved = (entity_type, raw_file_id, list(candidates))
                return len(candidates)

        repo = Repo()
        result = refine_match_candidates_with_jaro_winkler(
            db=None,
            entity_type="PERSON",
            raw_file_id=100,
            repo=repo,
        )

        self.assertEqual(result.candidates_in_scope, 0)
        self.assertEqual(result.candidates_out, 0)
        self.assertEqual(repo.saved, ("PERSON", 100, []))

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

    def test_groups_auto_merge_candidates_transitively_and_ignores_pair_direction(self) -> None:
        candidates = [
            SimpleNamespace(Left_Preprocessed_ID=1, Right_Preprocessed_ID=2),
            SimpleNamespace(Left_Preprocessed_ID=2, Right_Preprocessed_ID=1),
            SimpleNamespace(Left_Preprocessed_ID=2, Right_Preprocessed_ID=3),
            SimpleNamespace(Left_Preprocessed_ID=10, Right_Preprocessed_ID=11),
        ]

        groups = build_entity_groups(candidates)

        self.assertEqual(
            [group.member_preprocessed_ids for group in groups],
            [(1, 2, 3), (10, 11)],
        )
        self.assertEqual(len({group.group_key for group in groups}), 2)

    def test_grouping_persists_only_auto_merge_candidates(self) -> None:
        candidates = [
            SimpleNamespace(
                Left_Preprocessed_ID=1,
                Right_Preprocessed_ID=2,
                Decision=MatchDecision.AUTO_MERGE.value,
            ),
            SimpleNamespace(
                Left_Preprocessed_ID=2,
                Right_Preprocessed_ID=3,
                Decision=MatchDecision.REVIEW.value,
            ),
            SimpleNamespace(
                Left_Preprocessed_ID=10,
                Right_Preprocessed_ID=11,
                Decision=MatchDecision.CANDIDATE.value,
            ),
        ]

        class Repo:
            saved = None

            def get_jaro_winkler_candidates(self, entity_type: str):
                return candidates

            def replace_entity_groups(self, entity_type: str, groups):
                self.saved = (entity_type, list(groups))
                return len(groups), sum(len(group.member_preprocessed_ids) for group in groups)

        repo = Repo()
        result = group_auto_merge_candidates(
            db=None,
            entity_type="PARTY",
            repo=repo,
        )

        self.assertEqual(result.entity_type, "PARTY")
        self.assertEqual(result.auto_merge_pairs_in_scope, 1)
        self.assertEqual(result.groups_out, 1)
        self.assertEqual(result.members_out, 2)
        self.assertEqual(result.groups[0].member_preprocessed_ids, (1, 2))
        self.assertEqual(repo.saved[0], "PARTY")

    def test_group_key_is_stable_for_repeated_grouping(self) -> None:
        candidates = [
            SimpleNamespace(Left_Preprocessed_ID=3, Right_Preprocessed_ID=2),
            SimpleNamespace(Left_Preprocessed_ID=1, Right_Preprocessed_ID=2),
        ]

        first_run = build_entity_groups(candidates)
        second_run = build_entity_groups(list(reversed(candidates)))

        self.assertEqual(first_run, second_run)

    def test_grouping_rerun_replaces_state_without_duplicates(self) -> None:
        candidates = [
            SimpleNamespace(
                Left_Preprocessed_ID=1,
                Right_Preprocessed_ID=2,
                Decision=MatchDecision.AUTO_MERGE.value,
            ),
            SimpleNamespace(
                Left_Preprocessed_ID=2,
                Right_Preprocessed_ID=3,
                Decision=MatchDecision.AUTO_MERGE.value,
            ),
        ]

        class Repo:
            def __init__(self):
                self.saved_groups = {}
                self.saved_members = set()

            def get_jaro_winkler_candidates(self, entity_type: str):
                return candidates

            def replace_entity_groups(self, entity_type: str, groups):
                self.saved_groups = {group.group_key: group for group in groups}
                self.saved_members = {
                    (entity_type, group.group_key, preprocessed_id)
                    for group in groups
                    for preprocessed_id in group.member_preprocessed_ids
                }
                return len(self.saved_groups), len(self.saved_members)

        repo = Repo()
        first_run = group_auto_merge_candidates(db=None, entity_type="PARTY", repo=repo)
        first_groups = dict(repo.saved_groups)
        first_members = set(repo.saved_members)
        second_run = group_auto_merge_candidates(db=None, entity_type="PARTY", repo=repo)

        self.assertEqual(first_run, second_run)
        self.assertEqual(repo.saved_groups, first_groups)
        self.assertEqual(repo.saved_members, first_members)
        self.assertEqual(second_run.groups_out, 1)
        self.assertEqual(second_run.members_out, 3)


if __name__ == "__main__":
    unittest.main()
