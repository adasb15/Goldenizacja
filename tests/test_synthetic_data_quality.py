import csv
import unittest
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "csv"


class SyntheticDataQualityTests(unittest.TestCase):
    def test_pesel_identity_documents_are_not_reused_by_different_people(self) -> None:
        with (DATA_DIR / "pesel.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        for column in ("NumerDowoduOsobistego", "NumerPaszportu"):
            pesels_by_document: dict[str, set[str]] = defaultdict(set)
            for row in rows:
                document_value = (row.get(column) or "").strip()
                pesel = (row.get("PESEL") or "").strip()
                if document_value and pesel:
                    pesels_by_document[document_value].add(pesel)

            conflicts = {
                document_value: sorted(pesels)
                for document_value, pesels in pesels_by_document.items()
                if len(pesels) > 1
            }

            self.assertEqual(conflicts, {}, f"{column} reused by different PESEL values")

    def test_same_pesel_has_at_most_half_percent_hard_name_conflicts(self) -> None:
        person_refs = []
        for source, file_name, pesel_col, first_col, last_col in (
            ("pesel", "pesel.csv", "PESEL", "Imie", "Nazwisko"),
            ("ceidg", "ceidg.csv", "firma.wlasciciel.pesel", "firma.wlasciciel.imie", "firma.wlasciciel.nazwisko"),
            ("knf_agent", "KNF_Rejestr_posrednikow_ubezpieczeniowych_agent.csv", "PESEL", "Imię", "Nazwisko"),
            (
                "knf_worker",
                "KNF_Rejestr_posrednikow_ubezpieczeniowych_pracownik_agenta.csv",
                "PESEL",
                "Imię",
                "Nazwisko",
            ),
        ):
            person_refs.extend(self._person_refs(source, file_name, pesel_col, first_col, last_col))

        refs_by_pesel: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        for ref in person_refs:
            refs_by_pesel[ref[1]].append(ref)

        hard_conflicts = {}
        for pesel, refs in refs_by_pesel.items():
            complete_names = sorted({name for _, _, name in refs if len(name.split()) >= 2})
            if len(complete_names) < 2:
                continue

            baseline = complete_names[0]
            if any(self._name_similarity(baseline, name) < 0.7 for name in complete_names[1:]):
                hard_conflicts[pesel] = complete_names

        max_allowed = max(1, round(len(refs_by_pesel) * 0.005))
        self.assertLessEqual(
            len(hard_conflicts),
            max_allowed,
            f"Too many hard name conflicts for the same PESEL: {hard_conflicts}",
        )

    def test_invalid_pesel_variants_have_valid_counterparts_by_name(self) -> None:
        person_refs = []
        for source, file_name, pesel_col, first_col, last_col in (
            ("pesel", "pesel.csv", "PESEL", "Imie", "Nazwisko"),
            ("ceidg", "ceidg.csv", "firma.wlasciciel.pesel", "firma.wlasciciel.imie", "firma.wlasciciel.nazwisko"),
            ("knf_agent", "KNF_Rejestr_posrednikow_ubezpieczeniowych_agent.csv", "PESEL", "Imię", "Nazwisko"),
            (
                "knf_worker",
                "KNF_Rejestr_posrednikow_ubezpieczeniowych_pracownik_agenta.csv",
                "PESEL",
                "Imię",
                "Nazwisko",
            ),
        ):
            person_refs.extend(self._person_refs(source, file_name, pesel_col, first_col, last_col))

        invalid_refs = [ref for ref in person_refs if not self._is_valid_pesel(ref[1])]
        with_valid_counterpart = [
            ref
            for ref in invalid_refs
            if any(
                other_ref[2] == ref[2]
                and other_ref[1] != ref[1]
                and self._is_valid_pesel(other_ref[1])
                for other_ref in person_refs
            )
        ]

        self.assertGreater(len(invalid_refs), 0)
        self.assertEqual(len(with_valid_counterpart), len(invalid_refs))

    def test_party_identifiers_do_not_point_to_different_companies(self) -> None:
        party_refs = []
        for source, file_name, columns in (
            (
                "ceidg",
                "ceidg.csv",
                {"nip": "firma.nip", "regon": "firma.regon", "krs": "", "name": "firma.nazwa"},
            ),
            (
                "krs",
                "krs.csv",
                {"nip": "nip", "regon": "regon", "krs": "numerKRS", "name": "nazwa"},
            ),
            (
                "regon",
                "regon.csv",
                {"nip": "nip", "regon": "regon", "krs": "krs", "name": "nazwa"},
            ),
            (
                "vat",
                "vat.csv",
                {"nip": "nip", "regon": "regon", "krs": "krs", "name": "name"},
            ),
        ):
            party_refs.extend(self._party_refs(source, file_name, columns))

        for identifier in ("nip", "regon", "krs"):
            refs_by_identifier: dict[str, list[dict[str, str]]] = defaultdict(list)
            for ref in party_refs:
                value = ref[identifier]
                if value:
                    refs_by_identifier[value].append(ref)

            hard_conflicts = {}
            for value, refs in refs_by_identifier.items():
                names = sorted({ref["name"] for ref in refs if ref["name"]})
                if len(names) < 2:
                    continue

                baseline = names[0]
                if any(self._name_similarity(baseline, name) < 0.7 for name in names[1:]):
                    hard_conflicts[value] = names

            max_allowed = max(1, round(len(refs_by_identifier) * 0.005))
            self.assertLessEqual(
                len(hard_conflicts),
                max_allowed,
                f"Too many hard company conflicts for the same {identifier}: {hard_conflicts}",
            )

    def _person_refs(
        self,
        source: str,
        file_name: str,
        pesel_col: str,
        first_col: str,
        last_col: str,
    ) -> list[tuple[str, str, str]]:
        with (DATA_DIR / file_name).open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        refs = []
        for row in rows:
            pesel = (row.get(pesel_col) or "").strip()
            first_name = (row.get(first_col) or "").strip()
            last_name = (row.get(last_col) or "").strip()
            name = " ".join(part for part in (first_name, last_name) if part)
            if pesel and name:
                refs.append((source, pesel, name.casefold()))
        return refs

    def _party_refs(
        self,
        source: str,
        file_name: str,
        columns: dict[str, str],
    ) -> list[dict[str, str]]:
        with (DATA_DIR / file_name).open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        refs = []
        for row in rows:
            refs.append(
                {
                    "source": source,
                    "nip": (row.get(columns["nip"]) or "").strip() if columns["nip"] else "",
                    "regon": (row.get(columns["regon"]) or "").strip() if columns["regon"] else "",
                    "krs": (row.get(columns["krs"]) or "").strip() if columns["krs"] else "",
                    "name": (row.get(columns["name"]) or "").strip().casefold(),
                }
            )
        return refs

    def _name_similarity(self, left: str, right: str) -> float:
        return SequenceMatcher(None, left, right).ratio()

    def _is_valid_pesel(self, value: str) -> bool:
        if not value.isdigit() or len(value) != 11:
            return False
        weights = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
        checksum = sum(int(value[index]) * weights[index] for index in range(10))
        control_digit = (10 - checksum % 10) % 10
        return control_digit == int(value[10])


if __name__ == "__main__":
    unittest.main()
