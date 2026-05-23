import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

MISSING_COLUMNS_KEY = "_missing_columns"
UNRECOGNIZED_COLUMNS_KEY = "_unrecognized_columns"
SUPPORTED_ENTITY_TYPES = {"PERSON", "PARTY"}

PERSON_CANONICAL_COLUMNS = {
    "Source_Record_ID",
    "PESEL",
    "Serial_Number_ID_Card",
    "Serial_Number_Passport",
    "First_Name",
    "Second_Name",
    "Last_Name",
    "Family_Name",
    "Birth_Date",
    "Place_Of_Birth",
    "Sex",
    "Citizenship",
    "Phone_Number",
    "Email_Address",
    "Street",
    "Building_Number",
    "Apartment_Number",
    "City",
    "Postal_City",
    "Postal_Code",
    "District",
    "Province",
    "Country",
    "Raw_Record_JSON",
}

# Definiujemy szeroki model PARTY, żeby staging miał dane pod rejestry, relacje i lineage golden
PARTY_CANONICAL_COLUMNS = {
    "Source_Record_ID",
    "Name",
    "Short_Name",
    "Legal_Entity_Type",
    "Registration_Country",
    "Establishment_Date",
    "Identifiers_JSON",
    "Street",
    "Building_Number",
    "Apartment_Number",
    "City",
    "Postal_City",
    "Postal_Code",
    "District",
    "Province",
    "Country",
    "Register_Status",
    "Registration_Date",
    "Deregistration_Date",
    "Decision_Date",
    "Decision_Number",
    "Register_Number",
    "Bank_Accounts_JSON",
    "Has_Virtual_Accounts",
    "Business_Scope",
    "Ownership_Form",
    "Municipality",
    "Phone_Number",
    "Email_Address",
    "Website",
    "Agent_Type",
    "Insurance_Company",
    "Related_Persons_JSON",
    "Related_Parties_JSON",
    "Registration_Status",
    "Last_Update_Date",
    "Next_Renewal_Date",
    "Managing_LOU",
    "Validation_Sources",
    "Validation_Authority_ID",
    "Validation_Authority_Entity_ID",
    "Direct_Parent_LEI",
    "Direct_Parent_Name",
    "Direct_Parent_Relationship_Type",
    "Direct_Parent_Relationship_Status",
    "Direct_Parent_Relationship_Start_Date",
    "Direct_Parent_Relationship_End_Date",
    "Ultimate_Parent_LEI",
    "Ultimate_Parent_Name",
    "Ultimate_Parent_Relationship_Type",
    "Ultimate_Parent_Relationship_Status",
    "Ultimate_Parent_Relationship_Start_Date",
    "Ultimate_Parent_Relationship_End_Date",
    "Raw_Record_JSON",
}

CANONICAL_COLUMNS_BY_ENTITY_TYPE = {
    "PERSON": PERSON_CANONICAL_COLUMNS,
    "PARTY": PARTY_CANONICAL_COLUMNS,
}

# Ujednolicamy nazwy identyfikatorów, żeby NIP/KRS/REGON trafiały do jednego JSON
IDENTIFIER_KEY_ALIASES = {
    "nip": "NIP",
    "taxnumber": "NIP",
    "taxref": "NIP",
    "numernip": "NIP",
    "numernipagenta": "NIP",
    "regon": "REGON",
    "nationalregistryno": "REGON",
    "statregref": "REGON",
    "krs": "KRS",
    "legalregisterno": "KRS",
    "courtref": "KRS",
    "numerkrs": "KRS",
    "numerkrsagenta": "KRS",
    "numeruknf": "UKNF",
    "lei": "LEI",
}

# Rozpoznajemy sloty KRS regexami, żeby później złożyć je do JSON relacji zamiast setek kolumn
KRS_RELATED_PERSON_COLUMN_RE = re.compile(
    r"^(CzlonekZarzadu|Prokurent|WspolnikOsoba|Likwidator|CzlonekRadyNadzorczej)"
    r"(\d+)_(Imie|DrugieImie|Nazwisko|PESEL|Funkcja|DataOd|DataDo)$"
)
KRS_RELATED_PARTY_COLUMN_RE = re.compile(
    r"^WspolnikPodmiot\d+_(Nazwa|KRS|NIP|DataOd|DataDo)$"
)
KRS_RELATED_COUNT_COLUMN_RE = re.compile(
    r"^Liczba(CzlonekZarzadu|Prokurent|WspolnikOsoba|Likwidator|"
    r"CzlonekRadyNadzorczej|WspolnikPodmiot)$"
)


class UnsupportedEntityTypeError(ValueError):
    pass


def normalize_entity_type(entity_type: str) -> str:
    normalized = entity_type.strip().upper()
    if normalized not in SUPPORTED_ENTITY_TYPES:
        raise UnsupportedEntityTypeError(
            f"Unsupported entity type '{entity_type}'. Supported types: PERSON, PARTY."
        )
    return normalized


def normalize_column_name(name: str) -> str:
    return name.strip().casefold()


def get_source_value(source_record: Mapping[str, Any], source_column: str) -> tuple[bool, Any]:
    # Szukamy wartości po nazwie i ścieżce, żeby ten sam mapping działał dla CSV oraz JSON/XML
    lookup = {
        normalize_column_name(str(column_name)): column_name
        for column_name in source_record.keys()
    }
    actual_key = lookup.get(normalize_column_name(source_column))
    if actual_key is not None:
        return True, source_record[actual_key]

    if "." not in source_column:
        return False, None

    current: Any = source_record
    for part in source_column.split("."):
        if not isinstance(current, Mapping):
            return False, None

        nested_lookup = {
            normalize_column_name(str(column_name)): column_name
            for column_name in current.keys()
        }
        actual_key = nested_lookup.get(normalize_column_name(part))
        if actual_key is None:
            return False, None

        current = current[actual_key]

    return True, current


def identifier_key_from_source_column(source_column: str) -> str:
    # Wyciągamy typ identyfikatora z kolumny źródłowej, żeby wartości trafiły do poprawnego klucza JSON
    last_path_part = source_column.split(".")[-1]
    compact = re.sub(r"[^0-9a-zA-Z]+", "", last_path_part).casefold()
    if compact in IDENTIFIER_KEY_ALIASES:
        return IDENTIFIER_KEY_ALIASES[compact]

    compact_full_name = re.sub(r"[^0-9a-zA-Z]+", "", source_column).casefold()
    if compact_full_name in IDENTIFIER_KEY_ALIASES:
        return IDENTIFIER_KEY_ALIASES[compact_full_name]

    return last_path_part.strip().upper()


def is_structured_related_column(source_column: str) -> bool:
    # Oznaczamy kolumny relacyjne jako obsłużone, żeby raport unrecognized nie zgłaszał danych KRS
    column = source_column.strip()
    return bool(
        KRS_RELATED_PERSON_COLUMN_RE.match(column)
        or KRS_RELATED_PARTY_COLUMN_RE.match(column)
        or KRS_RELATED_COUNT_COLUMN_RE.match(column)
    )


def krs_related_person_key(source_column: str) -> tuple[str, int] | None:
    match = KRS_RELATED_PERSON_COLUMN_RE.match(source_column.strip())
    if not match:
        return None
    prefix, slot, _field_name = match.groups()
    return prefix, int(slot)


def select_person_related_group(
    source_record: Mapping[str, Any],
    mapping: Mapping[str, str],
) -> tuple[str, int] | None:
    groups: dict[tuple[str, int], set[str]] = {}
    for source_column, canonical_column in mapping.items():
        if canonical_column not in {"First_Name", "Second_Name", "Last_Name", "PESEL"}:
            continue
        related_key = krs_related_person_key(source_column)
        if related_key is None:
            continue
        exists, value = get_source_value(source_record, source_column)
        if exists and value not in (None, ""):
            groups.setdefault(related_key, set()).add(canonical_column)

    for source_column in mapping.keys():
        related_key = krs_related_person_key(source_column)
        if related_key is None:
            continue
        present_columns = groups.get(related_key, set())
        if "PESEL" in present_columns and {"First_Name", "Last_Name"}.issubset(present_columns):
            return related_key

    for source_column in mapping.keys():
        related_key = krs_related_person_key(source_column)
        if related_key is not None and related_key in groups:
            return related_key

    return None


def map_record_to_canonical(
    source_record: Mapping[str, Any],
    mapping: Mapping[str, str],
    entity_type: str,
) -> dict[str, Any]:
    entity_type = normalize_entity_type(entity_type)
    canonical_columns = CANONICAL_COLUMNS_BY_ENTITY_TYPE[entity_type]
    canonical_record: dict[str, Any] = {
        column: None
        for column in canonical_columns
    }
    missing_columns: list[str] = []
    identifiers: dict[str, Any] = {}
    selected_related_person_key = (
        select_person_related_group(source_record, mapping)
        if entity_type == "PERSON"
        else None
    )

    for source_column, canonical_column in mapping.items():
        related_person_key = krs_related_person_key(source_column)
        if (
            entity_type == "PERSON"
            and selected_related_person_key is not None
            and related_person_key is not None
            and related_person_key != selected_related_person_key
        ):
            continue

        exists, value = get_source_value(source_record, source_column)
        if not exists:
            missing_columns.append(source_column)
            continue

        if value in (None, ""):
            continue

        if entity_type == "PARTY" and canonical_column == "Identifiers_JSON":
            # Składamy identyfikatory z JSON albo pojedynczych kolumn, żeby PARTY miało jeden format wyjścia
            identifier_values: Mapping[str, Any] | None = None

            if isinstance(value, Mapping):
                identifier_values = value
            elif isinstance(value, str):
                stripped = value.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    try:
                        parsed = json.loads(stripped)
                    except json.JSONDecodeError:
                        parsed = None

                    if isinstance(parsed, Mapping):
                        identifier_values = parsed

            if identifier_values is not None:
                for identifier_key, identifier_value in identifier_values.items():
                    if identifier_value not in (None, ""):
                        identifiers[str(identifier_key).upper()] = identifier_value
            else:
                identifiers[identifier_key_from_source_column(source_column)] = value

            continue

        if canonical_column in canonical_columns and canonical_record.get(canonical_column) in (None, ""):
            canonical_record[canonical_column] = value

    if entity_type == "PARTY":
        canonical_record["Identifiers_JSON"] = (
            json.dumps(identifiers, ensure_ascii=False, default=str)
            if identifiers
            else None
        )

    mapped_columns = {
        normalize_column_name(source_column)
        for source_column in mapping.keys()
    }
    mapped_top_level_columns = {
        normalize_column_name(source_column.split(".")[0])
        for source_column in mapping.keys()
    }
    canonical_record["Raw_Record_JSON"] = json.dumps(
        dict(source_record),
        ensure_ascii=False,
        default=str,
    )
    canonical_record[MISSING_COLUMNS_KEY] = missing_columns
    canonical_record[UNRECOGNIZED_COLUMNS_KEY] = [
        str(source_column)
        for source_column in source_record.keys()
        if normalize_column_name(str(source_column)) not in mapped_columns
        and normalize_column_name(str(source_column)) not in mapped_top_level_columns
        and not is_structured_related_column(str(source_column))
    ]
    return canonical_record


def map_records_to_canonical(
    source_records: Iterable[Mapping[str, Any]],
    mapping: Mapping[str, str],
    entity_type: str,
) -> list[dict[str, Any]]:
    return [
        map_record_to_canonical(source_record, mapping, entity_type)
        for source_record in source_records
    ]
