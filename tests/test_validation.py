from datetime import date
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.layers.validation.service import (
    build_validation_results,
    extract_pesel_birth_date,
    extract_pesel_sex,
    get_staging_sex_value,
    validate_lei_checksum,
    validate_email_value,
    validate_nip_checksum,
    validate_pesel_birth_date_match,
    validate_pesel_checksum,
    validate_pesel_sex_match,
    validate_polish_id_card_checksum,
    validate_regon_checksum,
)


class ValidationTests(unittest.TestCase):
    def test_validates_polish_identifier_checksums(self) -> None:
        self.assertTrue(validate_pesel_checksum("44051401359"))
        self.assertFalse(validate_pesel_checksum("44051401358"))
        self.assertTrue(validate_nip_checksum("8567346215"))
        self.assertFalse(validate_nip_checksum("8567346214"))
        self.assertTrue(validate_regon_checksum("590096454"))
        self.assertFalse(validate_regon_checksum("590096453"))
        self.assertTrue(validate_lei_checksum("529900T8BM49AURSDO55"))
        self.assertFalse(validate_lei_checksum("529900T8BM49AURSDO54"))
        self.assertTrue(validate_polish_id_card_checksum("ABA300000"))
        self.assertFalse(validate_polish_id_card_checksum("ABA400000"))

    def test_extracts_birth_date_and_sex_from_pesel(self) -> None:
        self.assertEqual(extract_pesel_birth_date("00810100000"), date(1800, 1, 1))
        self.assertEqual(extract_pesel_birth_date("44051401359"), date(1944, 5, 14))
        self.assertEqual(extract_pesel_birth_date("02291410979"), date(2002, 9, 14))
        self.assertEqual(extract_pesel_birth_date("00410100000"), date(2100, 1, 1))
        self.assertEqual(extract_pesel_birth_date("00610100000"), date(2200, 1, 1))
        self.assertFalse(extract_pesel_sex("44051401359"))
        self.assertTrue(extract_pesel_sex("90013106842"))

    def test_matches_pesel_birth_date_against_source_date_value(self) -> None:
        self.assertTrue(validate_pesel_birth_date_match("90013106842", "1990-01-31"))
        self.assertTrue(validate_pesel_birth_date_match("02291410979", date(2002, 9, 14)))
        self.assertFalse(validate_pesel_birth_date_match("90013106842", "1990-01-30"))
        self.assertFalse(validate_pesel_birth_date_match("90013106842", "bad-date"))

    def test_matches_pesel_sex_against_staging_values(self) -> None:
        self.assertTrue(validate_pesel_sex_match("73121508230", False))
        self.assertTrue(validate_pesel_sex_match("73121508230", 0))
        self.assertTrue(validate_pesel_sex_match("73121508230", "0"))
        self.assertTrue(validate_pesel_sex_match("73121508230", "M"))
        self.assertTrue(validate_pesel_sex_match("90013106842", True))
        self.assertTrue(validate_pesel_sex_match("90013106842", 1))
        self.assertTrue(validate_pesel_sex_match("90013106842", "K"))

    def test_validates_email_syntax_without_dns(self) -> None:
        self.assertTrue(validate_email_value("jan.kowalski@example.com", check_dns=False))
        self.assertFalse(validate_email_value("jan.kowalski.example.com", check_dns=False))

    def test_validates_email_domain_when_dns_check_enabled(self) -> None:
        with patch("app.layers.validation.service.email_domain_exists", return_value=True) as exists:
            self.assertTrue(validate_email_value("jan.kowalski@gmail.com", check_dns=True))
            exists.assert_called_once_with("gmail.com")

        with patch("app.layers.validation.service.email_domain_exists", return_value=False) as exists:
            self.assertFalse(validate_email_value("jan.kowalski@example.com", check_dns=True))
            exists.assert_called_once_with("example.com")

    def test_does_not_check_email_domain_when_syntax_is_invalid(self) -> None:
        with patch("app.layers.validation.service.email_domain_exists") as exists:
            self.assertFalse(validate_email_value("jan.kowalski.example.com", check_dns=True))
            exists.assert_not_called()

    def test_marks_invalid_person_record_without_interrupting(self) -> None:
        staging_record = SimpleNamespace(
            ImportBatch_ID=1,
            RawFile_ID=2,
            Staging_ID=3,
            Serial_Number_ID_Card="ABA400000",
        )
        preprocessed_record = SimpleNamespace(
            Preprocessed_ID=4,
            PESEL_Normalized="44051401358",
            Email_Normalized="bad-email",
            First_Name_Normalized="JAN1",
            Second_Name_Normalized=None,
            Last_Name_Normalized="KOWALSKI",
            Family_Name_Normalized=None,
        )

        results = build_validation_results(staging_record, preprocessed_record, "PERSON")
        failed = {result["Rule_Code"]: result for result in results if result["Status"] == "ERROR"}

        self.assertEqual(failed["PERSON_PESEL_CHECKSUM"]["Message"], "ERR_CHECKSUM_PESEL")
        self.assertEqual(failed["PERSON_EMAIL_SYNTAX"]["Message"], "ERR_EMAIL_INVALID")
        self.assertEqual(failed["PERSON_ID_CARD_CHECKSUM"]["Message"], "ERR_CHECKSUM_ID_CARD")
        self.assertEqual(
            failed["PERSON_FIRST_NAME_NORMALIZED_STRING"]["Message"],
            "ERR_FIRST_NAME_NORMALIZED_TYPE",
        )

    def test_marks_pesel_birth_date_and_sex_mismatches(self) -> None:
        staging_record = SimpleNamespace(
            ImportBatch_ID=1,
            RawFile_ID=2,
            Staging_ID=3,
            Serial_Number_ID_Card=None,
            Birth_Date=date(1990, 1, 30),
            Sex=False,
        )
        preprocessed_record = SimpleNamespace(
            Preprocessed_ID=4,
            PESEL_Normalized="90013106842",
            Email_Normalized="anna.kowalska@example.com",
            First_Name_Normalized="ANNA",
            Second_Name_Normalized=None,
            Last_Name_Normalized="KOWALSKA",
            Family_Name_Normalized=None,
        )

        results = build_validation_results(staging_record, preprocessed_record, "PERSON")
        failed = {result["Rule_Code"]: result for result in results if result["Status"] == "ERROR"}

        self.assertEqual(
            failed["PERSON_PESEL_BIRTH_DATE_MATCH"]["Message"],
            "ERR_PESEL_BIRTH_DATE_MISMATCH",
        )
        self.assertEqual(failed["PERSON_PESEL_SEX_MATCH"]["Message"], "ERR_PESEL_SEX_MISMATCH")

    def test_uses_raw_record_sex_when_database_boolean_conversion_is_wrong(self) -> None:
        staging_record = SimpleNamespace(
            ImportBatch_ID=1,
            RawFile_ID=2,
            Staging_ID=3,
            Serial_Number_ID_Card=None,
            Birth_Date=date(1973, 12, 15),
            Sex=True,
            Raw_Record_JSON='{"Plec": "M"}',
        )
        preprocessed_record = SimpleNamespace(
            Preprocessed_ID=4,
            PESEL_Normalized="73121508230",
            Email_Normalized="t.nowacki@example.com",
            First_Name_Normalized="TOMASZ",
            Second_Name_Normalized="ROBERT",
            Last_Name_Normalized="NOWACKI",
            Family_Name_Normalized=None,
        )

        results = build_validation_results(staging_record, preprocessed_record, "PERSON")
        passed = {result["Rule_Code"]: result for result in results if result["Status"] == "PASS"}

        self.assertFalse(get_staging_sex_value(staging_record))
        self.assertEqual(passed["PERSON_PESEL_SEX_MATCH"]["Checked_Value"], "False")

    def test_marks_invalid_party_identifiers(self) -> None:
        staging_record = SimpleNamespace(
            ImportBatch_ID=1,
            RawFile_ID=2,
            Staging_ID=3,
            Name="Example Sp. z o.o.",
        )
        preprocessed_record = SimpleNamespace(
            Preprocessed_ID=4,
            NIP_Normalized="8567346214",
            REGON_Normalized="590096453",
            KRS_Normalized="12345",
            LEI_Normalized="529900T8BM49AURSDO54",
            Email_Normalized="kontakt@example.com",
        )

        results = build_validation_results(staging_record, preprocessed_record, "PARTY")
        failed = {result["Rule_Code"]: result for result in results if result["Status"] == "ERROR"}
        passed = {result["Rule_Code"]: result for result in results if result["Status"] == "PASS"}

        self.assertEqual(failed["PARTY_NIP_CHECKSUM"]["Message"], "ERR_CHECKSUM_NIP")
        self.assertEqual(failed["PARTY_NIP_CHECKSUM"]["Severity"], "ERROR")
        self.assertEqual(failed["PARTY_REGON_CHECKSUM"]["Message"], "ERR_CHECKSUM_REGON")
        self.assertEqual(failed["PARTY_KRS_FORMAT"]["Message"], "ERR_FORMAT_KRS")
        self.assertEqual(failed["PARTY_LEI_CHECKSUM"]["Message"], "ERR_CHECKSUM_LEI")
        self.assertEqual(passed["PARTY_EMAIL_SYNTAX"]["Severity"], "INFO")


if __name__ == "__main__":
    unittest.main()
