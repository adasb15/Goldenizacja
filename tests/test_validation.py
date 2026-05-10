import unittest
from types import SimpleNamespace

from app.layers.validation.service import (
    build_validation_results,
    validate_lei_checksum,
    validate_email_value,
    validate_nip_checksum,
    validate_pesel_checksum,
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

    def test_validates_email_syntax_without_dns(self) -> None:
        self.assertTrue(validate_email_value("jan.kowalski@example.test", check_dns=False))
        self.assertFalse(validate_email_value("jan.kowalski.example.test", check_dns=False))

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
            Email_Normalized="kontakt@example.test",
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
