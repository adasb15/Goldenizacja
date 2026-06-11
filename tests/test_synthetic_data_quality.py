import csv
import re
import unittest
from collections import defaultdict
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "csv"


class SyntheticDataQualityTests(unittest.TestCase):
    FEMALE_FIRST_NAMES = {
        "agnieszka",
        "alicja",
        "anna",
        "barbara",
        "beata",
        "danuta",
        "dorota",
        "ewa",
        "ewelina",
        "iwona",
        "izabela",
        "joanna",
        "kamila",
        "karolina",
        "katarzyna",
        "kinga",
        "magdalena",
        "malgorzata",
        "maria",
        "monika",
        "natalia",
        "paulina",
        "renata",
        "sylwia",
        "urszula",
        "weronika",
        "zofia",
    }
    MALE_FIRST_NAMES = {
        "adam",
        "andrzej",
        "artur",
        "bartlomiej",
        "dariusz",
        "dawid",
        "edward",
        "grzegorz",
        "henryk",
        "jacek",
        "jakub",
        "jan",
        "kamil",
        "krzysztof",
        "leszek",
        "lukasz",
        "maciej",
        "marcin",
        "marek",
        "mariusz",
        "mateusz",
        "michal",
        "pawel",
        "piotr",
        "przemyslaw",
        "robert",
        "stanislaw",
        "tomasz",
        "wojciech",
        "zbigniew",
    }

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

    def test_gleif_lei_does_not_point_to_different_companies(self) -> None:
        with (DATA_DIR / "gleif.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        names_by_lei: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            lei = (row.get("LEI") or "").strip()
            name = (row.get("LegalName") or "").strip().casefold()
            if lei and name:
                names_by_lei[lei].add(name)

        hard_conflicts = {}
        for lei, names_set in names_by_lei.items():
            names = sorted(names_set)
            if len(names) < 2:
                continue

            baseline = names[0]
            if any(self._name_similarity(baseline, name) < 0.7 for name in names[1:]):
                hard_conflicts[lei] = names

        self.assertEqual(hard_conflicts, {}, f"LEI reused by different GLEIF companies: {hard_conflicts}")

    def test_generated_business_dates_are_chronological(self) -> None:
        failures = []
        for file_path in sorted(DATA_DIR.glob("*.csv")):
            with file_path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
                headers = handle.seekable() and rows[0].keys() if rows else []

            date_columns = [
                (header, self._date_role(header))
                for header in headers
                if self._date_role(header)
            ]
            if not date_columns:
                continue

            for row_number, row in enumerate(rows, start=2):
                starts = []
                ends = []
                suspensions = []
                resumes = []
                for header, role in date_columns:
                    parsed = self._parse_generated_date(row.get(header))
                    if not parsed:
                        continue
                    if role == "start":
                        starts.append((header, parsed))
                    elif role == "end":
                        ends.append((header, parsed))
                    elif role == "suspension":
                        suspensions.append((header, parsed))
                    elif role == "resume":
                        resumes.append((header, parsed))

                for start_header, start_date in starts:
                    for end_header, end_date in ends:
                        if not self._dates_are_paired(start_header, end_header):
                            continue
                        if start_date > end_date:
                            failures.append(
                                f"{file_path.name}:{row_number} {start_header}={start_date} > {end_header}={end_date}"
                            )

                for suspension_header, suspension_date in suspensions:
                    for start_header, start_date in starts:
                        if suspension_date < start_date:
                            failures.append(
                                f"{file_path.name}:{row_number} {suspension_header}={suspension_date} < {start_header}={start_date}"
                            )
                    for end_header, end_date in ends:
                        if suspension_date > end_date:
                            failures.append(
                                f"{file_path.name}:{row_number} {suspension_header}={suspension_date} > {end_header}={end_date}"
                            )

                for resume_header, resume_date in resumes:
                    for suspension_header, suspension_date in suspensions:
                        if resume_date < suspension_date:
                            failures.append(
                                f"{file_path.name}:{row_number} {resume_header}={resume_date} < {suspension_header}={suspension_date}"
                            )
                    for end_header, end_date in ends:
                        if resume_date > end_date:
                            failures.append(
                                f"{file_path.name}:{row_number} {resume_header}={resume_date} > {end_header}={end_date}"
                            )

        self.assertEqual(failures[:20], [], f"Invalid generated date chronology: {failures[:20]}")

    def test_second_names_match_first_name_gender(self) -> None:
        failures = []
        for file_path in sorted(DATA_DIR.glob("*.csv")):
            with file_path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))

            first_by_prefix = {}
            second_by_prefix = {}
            for header in rows[0].keys() if rows else []:
                role, prefix = self._person_name_role(header)
                if role == "first":
                    first_by_prefix[prefix] = header
                elif role == "second":
                    second_by_prefix[prefix] = header

            for prefix, second_header in second_by_prefix.items():
                first_header = first_by_prefix.get(prefix)
                if not first_header:
                    continue
                for row_number, row in enumerate(rows, start=2):
                    first_gender = self._first_name_gender(row.get(first_header))
                    second_gender = self._first_name_gender(row.get(second_header))
                    if first_gender and second_gender and first_gender != second_gender:
                        failures.append(
                            f"{file_path.name}:{row_number} {first_header}={row.get(first_header)} "
                            f"{second_header}={row.get(second_header)}"
                        )

        self.assertEqual(failures[:20], [], f"Second name gender mismatches: {failures[:20]}")

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

    def _date_role(self, value: str) -> str:
        normalized = self._key_id(value)
        if any(token in normalized for token in ("wykresl", "wyrejest", "deregistration", "termination")):
            return "end"
        if normalized.endswith("datado") or normalized.endswith("validto"):
            return "end"
        if "wznow" in normalized:
            return "resume"
        if "zawies" in normalized:
            return "suspension"
        if any(
            token in normalized
            for token in (
                "wpis",
                "rejestr",
                "powstania",
                "rozpoczecia",
                "registrationlegaldate",
                "initialregistrationdate",
            )
        ):
            return "start"
        if normalized.endswith("dataod") or normalized.endswith("validfrom"):
            return "start"
        return ""

    def _dates_are_paired(self, start_header: str, end_header: str) -> bool:
        start_id = self._key_id(start_header)
        end_id = self._key_id(end_header)
        if start_id.endswith("dataod") and end_id.endswith("datado"):
            return start_id[: -len("dataod")] == end_id[: -len("datado")]
        if start_id.endswith("validfrom") and end_id.endswith("validto"):
            return start_id[: -len("validfrom")] == end_id[: -len("validto")]
        return not (
            start_id.endswith("dataod")
            or start_id.endswith("validfrom")
            or end_id.endswith("datado")
            or end_id.endswith("validto")
        )

    def _parse_generated_date(self, value: str | None) -> date | None:
        raw = (value or "").strip()
        if not raw:
            return None
        text = raw.split("T", 1)[0].split(" ", 1)[0]
        year_dash_order = ("year", "month", "day") if "T" in raw else ("year", "day", "month")
        patterns = (
            (r"^(\d{4})-(\d{2})-(\d{2})$", year_dash_order),
            (r"^(\d{2})-(\d{2})-(\d{4})$", ("day", "month", "year")),
            (r"^(\d{4})/(\d{2})/(\d{2})$", ("year", "day", "month")),
            (r"^(\d{2})/(\d{2})/(\d{4})$", ("day", "month", "year")),
            (r"^(\d{8})(?:\d{4}|\d{6})?$", ("compact",)),
        )
        for pattern, order in patterns:
            match = re.match(pattern, text)
            if not match:
                continue
            try:
                if order == ("compact",):
                    return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
                values = {name: int(group) for name, group in zip(order, match.groups())}
                return date(values["year"], values["month"], values["day"])
            except ValueError:
                return None
        return None

    def _key_id(self, value: str) -> str:
        translation = str.maketrans(
            "ąćęłńóśżźĄĆĘŁŃÓŚŻŹ",
            "acelnoszzACELNOSZZ",
        )
        return re.sub(r"[^a-z0-9]", "", value.translate(translation).casefold())

    def _person_name_role(self, value: str) -> tuple[str, str]:
        normalized = self._key_id(value)
        if "ojca" in normalized or "matki" in normalized:
            return "", ""
        for token in ("drugieimie", "secondname", "middlename"):
            if normalized.endswith(token):
                return "second", normalized[: -len(token)]
            if normalized.startswith(token):
                return "second", normalized[len(token) :]
        for token in ("imie", "firstname"):
            if normalized.endswith(token):
                return "first", normalized[: -len(token)]
            if normalized.startswith(token):
                return "first", normalized[len(token) :]
        return "", ""

    def _first_name_gender(self, value: str | None) -> str:
        normalized = self._key_id(value or "")
        if normalized in self.FEMALE_FIRST_NAMES:
            return "female"
        if normalized in self.MALE_FIRST_NAMES:
            return "male"
        return ""


if __name__ == "__main__":
    unittest.main()
