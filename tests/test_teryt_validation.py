import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.layers.validation.service import build_validation_results


class TerytValidationTests(unittest.TestCase):
    def test_validates_city_and_street_against_teryt_when_enabled(self) -> None:
        staging_record = SimpleNamespace(
            ImportBatch_ID=1,
            RawFile_ID=2,
            Staging_ID=3,
            Name="Example Sp. z o.o.",
        )
        preprocessed_record = SimpleNamespace(
            Preprocessed_ID=4,
            NIP_Normalized=None,
            REGON_Normalized=None,
            KRS_Normalized=None,
            LEI_Normalized=None,
            Email_Normalized=None,
            City_Normalized="SIERADZ",
            Street_Normalized="UL ŻÓŁKIEWSKIEGO STANISŁAWA",
        )

        with patch.dict(
            os.environ,
            {
                "TERYT_DIR": "data/teryt",
            },
            clear=False,
        ):
            results = build_validation_results(
                staging_record,
                preprocessed_record,
                "PARTY",
                check_email_dns=False,
            )

        by_code = {result["Rule_Code"]: result for result in results}
        self.assertEqual(by_code["ADDR_TERYT_CITY_EXISTS"]["Status"], "PASS")
        self.assertEqual(by_code["ADDR_TERYT_STREET_EXISTS"]["Status"], "PASS")

        # Fallback: users often enter "name surname" instead of TERYT's "surname name".
        preprocessed_record.Street_Normalized = "UL STANISŁAWA ŻÓŁKIEWSKIEGO"
        with patch.dict(
            os.environ,
            {
                "TERYT_DIR": "data/teryt",
            },
            clear=False,
        ):
            results_swapped = build_validation_results(
                staging_record,
                preprocessed_record,
                "PARTY",
                check_email_dns=False,
            )

        by_code_swapped = {result["Rule_Code"]: result for result in results_swapped}
        self.assertEqual(by_code_swapped["ADDR_TERYT_STREET_EXISTS"]["Status"], "PASS")

    def test_marks_street_invalid_when_city_unknown(self) -> None:
        staging_record = SimpleNamespace(
            ImportBatch_ID=1,
            RawFile_ID=2,
            Staging_ID=3,
            Name="Example Sp. z o.o.",
        )
        preprocessed_record = SimpleNamespace(
            Preprocessed_ID=4,
            NIP_Normalized=None,
            REGON_Normalized=None,
            KRS_Normalized=None,
            LEI_Normalized=None,
            Email_Normalized=None,
            City_Normalized="NIEISTNIEJACE-MIASTO",
            Street_Normalized="UL DŁUGA",
        )

        with patch.dict(
            os.environ,
            {
                "TERYT_DIR": "data/teryt",
            },
            clear=False,
        ):
            results = build_validation_results(
                staging_record,
                preprocessed_record,
                "PARTY",
                check_email_dns=False,
            )

        failed = {result["Rule_Code"]: result for result in results if result["Status"] == "ERROR"}
        self.assertEqual(failed["ADDR_TERYT_CITY_EXISTS"]["Message"], "ERR_TERYT_CITY_NOT_FOUND")
        self.assertEqual(failed["ADDR_TERYT_STREET_EXISTS"]["Message"], "ERR_TERYT_STREET_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
