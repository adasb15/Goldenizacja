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
    "Raw_Record_JSON",
}

CANONICAL_COLUMNS_BY_ENTITY_TYPE = {
    "PERSON": PERSON_CANONICAL_COLUMNS,
    "PARTY": PARTY_CANONICAL_COLUMNS,
}

IDENTIFIER_KEY_ALIASES = {
    "nip": "NIP",
    "numernip": "NIP",
    "numernipagenta": "NIP",
    "regon": "REGON",
    "krs": "KRS",
    "numerkrs": "KRS",
    "numerkrsagenta": "KRS",
    "lei": "LEI",
}


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
    last_path_part = source_column.split(".")[-1]
    compact = re.sub(r"[^0-9a-zA-Z]+", "", last_path_part).casefold()
    if compact in IDENTIFIER_KEY_ALIASES:
        return IDENTIFIER_KEY_ALIASES[compact]

    compact_full_name = re.sub(r"[^0-9a-zA-Z]+", "", source_column).casefold()
    if compact_full_name in IDENTIFIER_KEY_ALIASES:
        return IDENTIFIER_KEY_ALIASES[compact_full_name]

    return last_path_part.strip().upper()


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

    for source_column, canonical_column in mapping.items():
        exists, value = get_source_value(source_record, source_column)
        if not exists:
            missing_columns.append(source_column)
            continue

        if value in (None, ""):
            continue

        if entity_type == "PARTY" and canonical_column == "Identifiers_JSON":
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
