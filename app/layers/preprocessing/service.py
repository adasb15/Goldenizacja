import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.layers.staging_validation.mapper import normalize_entity_type


try:
    import phonenumbers
except ImportError:
    phonenumbers = None


ADDRESS_PREFIX_RE = re.compile(r"^(?:ul\.?|ulica|al\.?|aleja)\s+", re.IGNORECASE)
APARTMENT_PREFIX_RE = re.compile(r"\s+(?:m\.?|lok\.?|lokal)\s+", re.IGNORECASE)
FULL_ADDRESS_STREET_FIRST_RE = re.compile(
    r"^\s*(?P<street_part>.+?),\s*(?P<postal_code>\d{2}-\d{3})\s+(?P<city>.+?)\s*$"
)
FULL_ADDRESS_POSTAL_FIRST_RE = re.compile(
    r"^\s*(?P<postal_code>\d{2}-\d{3})\s+(?P<city>[^,]+?),\s*(?P<street_part>.+?)\s*$"
)
CITY_STREET_LINE_RE = re.compile(r"^\s*(?P<city>[^,]+?),\s*(?P<street_part>.+?)\s*$")
POSTAL_CITY_LINE_RE = re.compile(r"^\s*(?P<postal_code>\d{2}-\d{3})\s+(?P<city>.+?)\s*$")
STREET_BUILDING_LINE_RE = re.compile(
    r"^\s*(?P<street>.+?)\s+(?P<building>\d+[A-Za-z]?(?:[-/]\d+[A-Za-z]?)?)\s*$"
)
NON_DIGIT_RE = re.compile(r"\D+")
NON_ALNUM_RE = re.compile(r"[^0-9A-Z]+")
MULTISPACE_RE = re.compile(r"\s+")


class StagingRecordsNotFoundError(ValueError):
    pass


class StagingRecordsAlreadyPreprocessedError(ValueError):
    pass


@dataclass
class PreprocessingLoadResult:
    import_batch_id: int
    raw_file_id: int
    entity_type: str
    records_in: int
    records_out: int
    process_status: str


@dataclass
class AddressParts:
    street: str | None = None
    building_number: str | None = None
    apartment_number: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None

    @property
    def full_address(self) -> str | None:
        parts = [
            self.street,
            self.building_number,
            self.apartment_number,
            self.postal_code,
            self.city,
            self.country,
        ]
        return compact_text(" ".join(part for part in parts if part))


def create_repository(db: Any) -> Any:
    from app.layers.preprocessing.repository import PreprocessingRepository

    return PreprocessingRepository(db)


def load_staging_to_preprocessing(
    db: Any,
    raw_file_id: int,
    entity_type: str,
    repo: Any | None = None,
) -> PreprocessingLoadResult:
    entity_type = normalize_entity_type(entity_type)
    repo = repo or create_repository(db)
    process_log = None
    import_batch_id = None

    try:
        staging_records = repo.get_staging_records(raw_file_id, entity_type)
        if not staging_records:
            raise StagingRecordsNotFoundError(
                f"No {entity_type} staging records for RawFile_ID={raw_file_id}."
            )

        import_batch_id = staging_records[0].ImportBatch_ID
        existing_records = repo.count_preprocessed_records_for_raw_file(raw_file_id, entity_type)
        if existing_records:
            # Preprocessing jest deterministyczny dla raw_file_id, więc nie dokładamy duplikatów
            raise StagingRecordsAlreadyPreprocessedError(
                f"RawFile_ID={raw_file_id} is already preprocessed for {entity_type} "
                f"({existing_records} records)."
            )

        process_log = repo.create_preprocessing_process_log(
            import_batch_id=import_batch_id,
            raw_file_id=raw_file_id,
        )
        records = [
            build_preprocessed_record(staging_record, entity_type)
            for staging_record in staging_records
        ]

        if entity_type == "PERSON":
            records_out = repo.insert_person_preprocessed_records(records)
        else:
            records_out = repo.insert_party_preprocessed_records(records)

        repo.finish_process_log(
            process_log,
            status="SUCCESS",
            records_in=len(staging_records),
            records_out=records_out,
        )

        return PreprocessingLoadResult(
            import_batch_id=import_batch_id,
            raw_file_id=raw_file_id,
            entity_type=entity_type,
            records_in=len(staging_records),
            records_out=records_out,
            process_status="SUCCESS",
        )
    except StagingRecordsAlreadyPreprocessedError:
        if hasattr(repo, "rollback"):
            repo.rollback()
        raise
    except Exception as exc:
        if hasattr(repo, "rollback"):
            repo.rollback()
        if process_log is not None:
            repo.finish_process_log(process_log, status="FAILED", error_message=str(exc))
        raise


def build_preprocessed_record(staging_record: Any, entity_type: str) -> dict[str, Any]:
    entity_type = normalize_entity_type(entity_type)
    address_parts = split_address_from_staging(staging_record)
    base = {
        "Staging_ID": staging_record.Staging_ID,
        "ImportBatch_ID": staging_record.ImportBatch_ID,
        "RawFile_ID": staging_record.RawFile_ID,
        "Source_Record_ID": empty_to_none(staging_record.Source_Record_ID),
        "Street_Normalized": normalize_text_key(address_parts.street),
        "Building_Number_Normalized": normalize_identifier(address_parts.building_number),
        "Apartment_Number_Normalized": normalize_identifier(address_parts.apartment_number),
        "City_Normalized": normalize_text_key(address_parts.city),
        "Postal_Code_Normalized": normalize_postal_code(address_parts.postal_code),
        "Country_Normalized": normalize_text_key(address_parts.country),
        "Full_Address_Normalized": normalize_text_key(address_parts.full_address),
        "Preprocessing_Rules_JSON": build_rules_json(),
    }

    if entity_type == "PERSON":
        first_name = normalize_text_key(staging_record.First_Name)
        second_name = normalize_text_key(staging_record.Second_Name)
        last_name = normalize_text_key(staging_record.Last_Name)
        family_name = normalize_text_key(staging_record.Family_Name)
        base.update(
            {
                "PESEL_Normalized": normalize_identifier(staging_record.PESEL),
                "First_Name_Normalized": first_name,
                "Second_Name_Normalized": second_name,
                "Last_Name_Normalized": last_name,
                "Family_Name_Normalized": family_name,
                "Full_Name_Normalized": compact_text(
                    " ".join(part for part in (first_name, second_name, last_name) if part)
                ),
                "Phone_Normalized": normalize_phone(staging_record.Phone_Number),
                "Email_Normalized": normalize_email(staging_record.Email_Address),
            }
        )
        return base

    identifiers = parse_identifiers_json(staging_record.Identifiers_JSON)
    base.update(
        {
            "Name_Normalized": normalize_text_key(staging_record.Name),
            "Short_Name_Normalized": normalize_text_key(staging_record.Short_Name),
            "Legal_Entity_Type_Normalized": normalize_text_key(staging_record.Legal_Entity_Type),
            "NIP_Normalized": normalize_identifier(identifiers.get("NIP")),
            "REGON_Normalized": normalize_identifier(identifiers.get("REGON")),
            "KRS_Normalized": normalize_identifier(identifiers.get("KRS")),
            "LEI_Normalized": normalize_identifier(identifiers.get("LEI")),
            "Phone_Normalized": normalize_phone(staging_record.Phone_Number),
            "Email_Normalized": normalize_email(staging_record.Email_Address),
            "Website_Normalized": normalize_website(staging_record.Website),
        }
    )
    return base


def split_address_from_staging(staging_record: Any) -> AddressParts:
    parts = AddressParts(
        street=empty_to_none(staging_record.Street),
        building_number=empty_to_none(staging_record.Building_Number),
        apartment_number=empty_to_none(staging_record.Apartment_Number),
        city=empty_to_none(staging_record.City),
        postal_code=empty_to_none(staging_record.Postal_Code),
        country=empty_to_none(staging_record.Country),
    )

    for source_column in ("Street", "Postal_City", "City"):
        address_line = empty_to_none(getattr(staging_record, source_column, None))
        if not address_line:
            continue
        if split_full_address_line(parts, address_line):
            continue
        if source_column == "Street":
            split_street_line(parts, address_line)
        elif source_column == "City":
            split_city_line(parts, address_line)

    return parts


def split_full_address_line(parts: AddressParts, address_line: str) -> bool:
    for pattern in (FULL_ADDRESS_STREET_FIRST_RE, FULL_ADDRESS_POSTAL_FIRST_RE):
        full_match = pattern.match(address_line)
        if full_match:
            # Pełny adres rozbijamy dopiero tutaj, bo to wartość pochodna do matchingu
            parts.postal_code = parts.postal_code or full_match.group("postal_code")
            parts.city = parts.city or full_match.group("city")
            split_street_line(parts, full_match.group("street_part"))
            return True

    city_street_match = CITY_STREET_LINE_RE.match(address_line)
    if city_street_match and looks_like_street_line(city_street_match.group("street_part")):
        parsed_city = city_street_match.group("city")
        parts.city = parsed_city if parts.city == address_line else parts.city or parsed_city
        split_street_line(parts, city_street_match.group("street_part"))
        return True

    postal_city_match = POSTAL_CITY_LINE_RE.match(address_line)
    if postal_city_match:
        parts.postal_code = parts.postal_code or postal_city_match.group("postal_code")
        parsed_city = postal_city_match.group("city")
        parts.city = parsed_city if parts.city == address_line else parts.city or parsed_city
        if parts.street == address_line:
            parts.street = None
        return True

    return False


def split_city_line(parts: AddressParts, city_line: str) -> None:
    if split_full_address_line(parts, city_line):
        return
    parts.city = parts.city or city_line


def split_street_line(parts: AddressParts, street_line: str) -> None:
    normalized_line = normalize_street_line(street_line)
    if not normalized_line:
        return

    street_match = STREET_BUILDING_LINE_RE.match(normalized_line)
    if not street_match:
        parts.street = parts.street or normalized_line
        return

    building_number, apartment_number = split_building_and_apartment(
        street_match.group("building")
    )
    parts.street = street_match.group("street").strip()
    parts.building_number = parts.building_number or building_number
    parts.apartment_number = parts.apartment_number or apartment_number


def normalize_street_line(value: str) -> str:
    without_prefix = ADDRESS_PREFIX_RE.sub("", value).strip()
    return APARTMENT_PREFIX_RE.sub("/", without_prefix).strip()


def looks_like_street_line(value: str) -> bool:
    return STREET_BUILDING_LINE_RE.match(normalize_street_line(value)) is not None


def split_building_and_apartment(value: str) -> tuple[str, str | None]:
    if "/" not in value:
        return value.strip(), None
    building_number, apartment_number = value.split("/", 1)
    return building_number.strip(), apartment_number.strip() or None


def normalize_text_key(value: Any) -> str | None:
    value = empty_to_none(value)
    if value is None:
        return None
    return compact_text(str(value).upper())


def normalize_identifier(value: Any) -> str | None:
    value = empty_to_none(value)
    if value is None:
        return None
    normalized = normalize_text_key(value)
    return NON_ALNUM_RE.sub("", normalized) if normalized is not None else None


def normalize_postal_code(value: Any) -> str | None:
    value = empty_to_none(value)
    if value is None:
        return None
    digits = NON_DIGIT_RE.sub("", str(value))
    if len(digits) == 5:
        return f"{digits[:2]}-{digits[2:]}"
    return compact_text(str(value).upper())


def normalize_phone(value: Any, region: str = "PL") -> str | None:
    value = empty_to_none(value)
    if value is None:
        return None
    if phonenumbers is not None:
        try:
            parsed = phonenumbers.parse(str(value), region)
            if phonenumbers.is_possible_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            pass

    digits = NON_DIGIT_RE.sub("", str(value))
    if not digits:
        return None
    if len(digits) == 9:
        return f"+48{digits}"
    if digits.startswith("48") and len(digits) == 11:
        return f"+{digits}"
    return f"+{digits}" if str(value).strip().startswith("+") else digits


def normalize_email(value: Any) -> str | None:
    value = empty_to_none(value)
    return str(value).casefold() if value is not None else None


def normalize_website(value: Any) -> str | None:
    value = empty_to_none(value)
    if value is None:
        return None
    normalized = str(value).strip().casefold()
    return normalized.removeprefix("https://").removeprefix("http://").removeprefix("www.")


def parse_identifiers_json(value: Any) -> dict[str, Any]:
    value = empty_to_none(value)
    if value is None:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def build_rules_json() -> str:
    return json.dumps(
        {
            "text": "trim_uppercase_ascii",
            "phone": "e164_when_possible",
            "address": "regex_split",
            "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds"),
        },
        ensure_ascii=False,
    )


def empty_to_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    compacted = compact_text(str(value))
    return compacted or None


def compact_text(value: str) -> str | None:
    compacted = MULTISPACE_RE.sub(" ", value).strip()
    return compacted or None
