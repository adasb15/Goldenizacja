from datetime import date, datetime
import csv
import json
import os
from pathlib import Path
import re
import socket
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.layers.staging_validation.mapper import normalize_entity_type


try:
    import dns.exception
    import dns.resolver
except ImportError:
    dns = None

try:
    from email_validator import EmailNotValidError, validate_email
except ImportError:
    EmailNotValidError = ValueError
    validate_email = None

try:
    from stdnum.pl import nip, pesel, regon
except ImportError:
    nip = None
    pesel = None
    regon = None

try:
    from stdnum import lei
except ImportError:
    lei = None


EMAIL_FALLBACK_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EMAIL_DNS_TIMEOUT_SECONDS = 0.5
PERSON_NAME_RE = re.compile(r"^[A-ZĄĆĘŁŃÓŚŹŻ][A-ZĄĆĘŁŃÓŚŹŻ '\-]*$")
KRS_RE = re.compile(r"^\d{10}$")
POLISH_ID_CARD_RE = re.compile(r"^[A-Z]{3}\d{6}$")
POLISH_ID_CARD_LETTER_VALUES = {chr(code): code - 55 for code in range(ord("A"), ord("Z") + 1)}
FEMALE_SEX_VALUES = {"1", "k", "kobieta", "female", "f"}
MALE_SEX_VALUES = {"0", "m", "mezczyzna", "mężczyzna", "male"}
SEX_SOURCE_FIELD_NAMES = {"sex", "plec", "płeć", "gender"}
PESEL_MONTH_CENTURY_OFFSETS = (
    (80, 1800),
    (0, 1900),
    (20, 2000),
    (40, 2100),
    (60, 2200),
)


class RecordsForValidationNotFoundError(ValueError):
    pass


TERYT_DIR_ENV = "TERYT_DIR"
FILESTREAM_PATH_ENV = "FILESTREAM_PATH"


@dataclass
class ValidationLoadResult:
    import_batch_id: int
    raw_file_id: int
    entity_type: str
    records_in: int
    validation_results: int
    passed: int
    failed: int
    process_status: str


def create_repository(db: Any) -> Any:
    from app.layers.validation.repository import ValidationRepository

    return ValidationRepository(db)


def load_validation_results(
    db: Any,
    raw_file_id: int,
    entity_type: str,
    check_email_dns: bool = True,
    repo: Any | None = None,
) -> ValidationLoadResult:
    entity_type = normalize_entity_type(entity_type)
    repo = repo or create_repository(db)
    process_log = None

    try:
        records = repo.get_records_for_validation(raw_file_id, entity_type)
        if not records:
            raise RecordsForValidationNotFoundError(
                f"No preprocessed {entity_type} records for RawFile_ID={raw_file_id}."
            )

        import_batch_id = records[0][0].ImportBatch_ID
        repo.delete_validation_results_for_raw_file(raw_file_id, entity_type)
        process_log = repo.create_validation_process_log(
            import_batch_id=import_batch_id,
            raw_file_id=raw_file_id,
        )

        validation_results: list[dict[str, Any]] = []
        for staging_record, preprocessed_record in records:
            validation_results.extend(
                build_validation_results(
                    staging_record=staging_record,
                    preprocessed_record=preprocessed_record,
                    entity_type=entity_type,
                    check_email_dns=check_email_dns,
                )
            )

        records_out = repo.insert_validation_results(validation_results)
        failed = sum(1 for result in validation_results if result["Status"] == "ERROR")
        passed = sum(1 for result in validation_results if result["Status"] == "PASS")
        repo.finish_process_log(
            process_log,
            status="SUCCESS",
            records_in=len(records),
            records_out=records_out,
        )

        return ValidationLoadResult(
            import_batch_id=import_batch_id,
            raw_file_id=raw_file_id,
            entity_type=entity_type,
            records_in=len(records),
            validation_results=records_out,
            passed=passed,
            failed=failed,
            process_status="SUCCESS",
        )
    except Exception as exc:
        if hasattr(repo, "rollback"):
            repo.rollback()
        if process_log is not None:
            repo.finish_process_log(process_log, status="FAILED", error_message=str(exc))
        raise


def build_validation_results(
    staging_record: Any,
    preprocessed_record: Any,
    entity_type: str,
    check_email_dns: bool = True,
) -> list[dict[str, Any]]:
    entity_type = normalize_entity_type(entity_type)
    base = {
        "ImportBatch_ID": staging_record.ImportBatch_ID,
        "RawFile_ID": staging_record.RawFile_ID,
        "Entity_Type": entity_type,
        "Staging_ID": staging_record.Staging_ID,
        "Preprocessed_ID": preprocessed_record.Preprocessed_ID,
    }

    if entity_type == "PERSON":
        return build_person_validation_results(
            base=base,
            staging_record=staging_record,
            preprocessed_record=preprocessed_record,
            check_email_dns=check_email_dns,
        )

    return build_party_validation_results(
        base=base,
        staging_record=staging_record,
        preprocessed_record=preprocessed_record,
        check_email_dns=check_email_dns,
    )


def build_person_validation_results(
    base: dict[str, Any],
    staging_record: Any,
    preprocessed_record: Any,
    check_email_dns: bool,
) -> list[dict[str, Any]]:
    staging_sex = get_staging_sex_value(staging_record)
    birth_date = getattr(staging_record, "Birth_Date", None)
    results = [
        make_result(
            base,
            level="PREPROCESSING",
            rule_code="PERSON_PESEL_CHECKSUM",
            field_name="PESEL_Normalized",
            value=preprocessed_record.PESEL_Normalized,
            is_valid=validate_polish_identifier("PESEL", preprocessed_record.PESEL_Normalized),
            error_message="ERR_CHECKSUM_PESEL",
        ),
        make_result(
            base,
            level="STAGING",
            rule_code="PERSON_PESEL_BIRTH_DATE_MATCH",
            field_name="Birth_Date",
            value=getattr(staging_record, "Birth_Date", None),
            is_valid=validate_pesel_birth_date_match(
                preprocessed_record.PESEL_Normalized,
                getattr(staging_record, "Birth_Date", None),
            ),
            error_message="ERR_PESEL_BIRTH_DATE_MISMATCH",
        ),
        make_result(
            base,
            level="STAGING",
            rule_code="PERSON_PESEL_SEX_MATCH",
            field_name="Sex",
            value=staging_sex,
            is_valid=validate_pesel_sex_match(
                preprocessed_record.PESEL_Normalized,
                staging_sex,
            ),
            error_message="ERR_PESEL_SEX_MISMATCH",
        ),
        make_result(
            base,
            level="PREPROCESSING",
            rule_code="PERSON_PESEL_BIRTH_DATE_NOT_FUTURE",
            field_name="PESEL_Normalized",
            value=preprocessed_record.PESEL_Normalized,
            is_valid=validate_pesel_birth_date_not_future(preprocessed_record.PESEL_Normalized),
            error_message="ERR_PESEL_BIRTH_DATE_IN_FUTURE",
        ),
        make_result(
            base,
            level="STAGING",
            rule_code="PERSON_BIRTH_DATE_NOT_FUTURE",
            field_name="Birth_Date",
            value=birth_date,
            is_valid=validate_date_not_in_future(birth_date),
            error_message="ERR_BIRTH_DATE_IN_FUTURE",
        ),
        make_result(
            base,
            level="PREPROCESSING",
            rule_code="PERSON_EMAIL_SYNTAX",
            field_name="Email_Normalized",
            value=preprocessed_record.Email_Normalized,
            is_valid=validate_email_value(preprocessed_record.Email_Normalized, check_email_dns),
            error_message="ERR_EMAIL_INVALID",
        ),
        make_result(
            base,
            level="STAGING",
            rule_code="PERSON_ID_CARD_CHECKSUM",
            field_name="Serial_Number_ID_Card",
            value=getattr(staging_record, "Serial_Number_ID_Card", None),
            is_valid=validate_optional_id_card(getattr(staging_record, "Serial_Number_ID_Card", None)),
            error_message="ERR_CHECKSUM_ID_CARD",
        ),
    ]

    results.extend(build_address_teryt_validation_results(base=base, preprocessed_record=preprocessed_record))

    for field_name in (
        "First_Name_Normalized",
        "Second_Name_Normalized",
        "Last_Name_Normalized",
        "Family_Name_Normalized",
    ):
        value = getattr(preprocessed_record, field_name)
        if value is not None:
            results.append(
                make_result(
                    base,
                    level="PREPROCESSING",
                    rule_code=f"PERSON_{field_name.upper()}_STRING",
                    field_name=field_name,
                    value=value,
                    is_valid=validate_person_name(value),
                    error_message=f"ERR_{field_name.upper()}_TYPE",
                )
            )

    return results


def build_party_validation_results(
    base: dict[str, Any],
    staging_record: Any,
    preprocessed_record: Any,
    check_email_dns: bool,
) -> list[dict[str, Any]]:
    establishment_date = getattr(staging_record, "Establishment_Date", None)
    registration_date = getattr(staging_record, "Registration_Date", None)
    deregistration_date = getattr(staging_record, "Deregistration_Date", None)
    last_update_date = getattr(staging_record, "Last_Update_Date", None)
    next_renewal_date = getattr(staging_record, "Next_Renewal_Date", None)
    direct_parent_start_date = getattr(staging_record, "Direct_Parent_Relationship_Start_Date", None)
    direct_parent_end_date = getattr(staging_record, "Direct_Parent_Relationship_End_Date", None)
    ultimate_parent_start_date = getattr(staging_record, "Ultimate_Parent_Relationship_Start_Date", None)
    ultimate_parent_end_date = getattr(staging_record, "Ultimate_Parent_Relationship_End_Date", None)

    results = [
        make_result(
            base,
            level="PREPROCESSING",
            rule_code="PARTY_NIP_CHECKSUM",
            field_name="NIP_Normalized",
            value=preprocessed_record.NIP_Normalized,
            is_valid=validate_optional_identifier("NIP", preprocessed_record.NIP_Normalized),
            error_message="ERR_CHECKSUM_NIP",
        ),
        make_result(
            base,
            level="PREPROCESSING",
            rule_code="PARTY_REGON_CHECKSUM",
            field_name="REGON_Normalized",
            value=preprocessed_record.REGON_Normalized,
            is_valid=validate_optional_identifier("REGON", preprocessed_record.REGON_Normalized),
            error_message="ERR_CHECKSUM_REGON",
        ),
        make_result(
            base,
            level="PREPROCESSING",
            rule_code="PARTY_KRS_FORMAT",
            field_name="KRS_Normalized",
            value=preprocessed_record.KRS_Normalized,
            is_valid=validate_optional_krs(preprocessed_record.KRS_Normalized),
            error_message="ERR_FORMAT_KRS",
        ),
        make_result(
            base,
            level="PREPROCESSING",
            rule_code="PARTY_LEI_CHECKSUM",
            field_name="LEI_Normalized",
            value=preprocessed_record.LEI_Normalized,
            is_valid=validate_optional_lei(preprocessed_record.LEI_Normalized),
            error_message="ERR_CHECKSUM_LEI",
        ),
        make_result(
            base,
            level="PREPROCESSING",
            rule_code="PARTY_EMAIL_SYNTAX",
            field_name="Email_Normalized",
            value=preprocessed_record.Email_Normalized,
            is_valid=validate_email_value(preprocessed_record.Email_Normalized, check_email_dns),
            error_message="ERR_EMAIL_INVALID",
        ),
        make_result(
            base,
            level="STAGING",
            rule_code="PARTY_NAME_STRING",
            field_name="Name",
            value=staging_record.Name,
            is_valid=is_non_empty_string(staging_record.Name),
            error_message="ERR_PARTY_NAME_TYPE",
        ),
        make_result(
            base,
            level="STAGING",
            rule_code="PARTY_ESTABLISHMENT_DEREGISTRATION_DATE_RANGE",
            field_name="Establishment_Date,Deregistration_Date",
            value=format_date_range_checked_value(
                establishment_date,
                deregistration_date,
            ),
            is_valid=validate_date_order(establishment_date, deregistration_date),
            error_message="ERR_ESTABLISHMENT_AFTER_DEREGISTRATION",
        ),
        make_result(
            base,
            level="STAGING",
            rule_code="PARTY_REGISTRATION_DEREGISTRATION_DATE_RANGE",
            field_name="Registration_Date,Deregistration_Date",
            value=format_date_range_checked_value(
                registration_date,
                deregistration_date,
            ),
            is_valid=validate_date_order(registration_date, deregistration_date),
            error_message="ERR_REGISTRATION_AFTER_DEREGISTRATION",
        ),
        make_result(
            base,
            level="STAGING",
            rule_code="PARTY_NEXT_RENEWAL_AFTER_LAST_UPDATE",
            field_name="Last_Update_Date,Next_Renewal_Date",
            value=format_date_range_checked_value(
                last_update_date,
                next_renewal_date,
            ),
            is_valid=validate_date_order(last_update_date, next_renewal_date),
            error_message="ERR_NEXT_RENEWAL_BEFORE_LAST_UPDATE",
        ),
        make_result(
            base,
            level="STAGING",
            rule_code="PARTY_DIRECT_PARENT_RELATIONSHIP_DATE_RANGE",
            field_name="Direct_Parent_Relationship_Start_Date,Direct_Parent_Relationship_End_Date",
            value=format_date_range_checked_value(
                direct_parent_start_date,
                direct_parent_end_date,
            ),
            is_valid=validate_date_order(direct_parent_start_date, direct_parent_end_date),
            error_message="ERR_DIRECT_PARENT_RELATIONSHIP_START_AFTER_END",
        ),
        make_result(
            base,
            level="STAGING",
            rule_code="PARTY_ULTIMATE_PARENT_RELATIONSHIP_DATE_RANGE",
            field_name="Ultimate_Parent_Relationship_Start_Date,Ultimate_Parent_Relationship_End_Date",
            value=format_date_range_checked_value(
                ultimate_parent_start_date,
                ultimate_parent_end_date,
            ),
            is_valid=validate_date_order(ultimate_parent_start_date, ultimate_parent_end_date),
            error_message="ERR_ULTIMATE_PARENT_RELATIONSHIP_START_AFTER_END",
        ),
    ]

    results.extend(build_address_teryt_validation_results(base=base, preprocessed_record=preprocessed_record))
    return results


def build_address_teryt_validation_results(
    base: dict[str, Any],
    preprocessed_record: Any,
) -> list[dict[str, Any]]:
    if not teryt_enabled():
        return []

    city = getattr(preprocessed_record, "City_Normalized", None)
    street = getattr(preprocessed_record, "Street_Normalized", None)

    city_exists = validate_teryt_city_exists(city)
    street_exists = validate_teryt_street_exists(city, street)

    return [
        make_result(
            base,
            level="PREPROCESSING",
            rule_code="ADDR_TERYT_CITY_EXISTS",
            field_name="City_Normalized",
            value=city,
            is_valid=city_exists,
            error_message="ERR_TERYT_CITY_NOT_FOUND",
        ),
        make_result(
            base,
            level="PREPROCESSING",
            rule_code="ADDR_TERYT_STREET_EXISTS",
            field_name="Street_Normalized",
            value=street,
            is_valid=street_exists if city_exists else False,
            error_message="ERR_TERYT_STREET_NOT_FOUND",
        ),
    ]


def make_result(
    base: dict[str, Any],
    level: str,
    rule_code: str,
    field_name: str,
    value: Any,
    is_valid: bool,
    error_message: str,
) -> dict[str, Any]:
    status = "PASS" if is_valid else "ERROR"
    return {
        **base,
        "Validation_Level": level,
        "Rule_Code": rule_code,
        "Field_Name": field_name,
        "Severity": "INFO" if is_valid else "ERROR",
        "Status": status,
        "Message": "OK" if is_valid else error_message,
        "Checked_Value": None if value is None else str(value),
    }


def teryt_enabled() -> bool:
    return teryt_files_exist(resolve_teryt_dir())


def resolve_default_teryt_dir() -> Path:
    # Prefer a local `data/teryt` next to the codebase, but be resilient to different working
    # directories / installation layouts (Airflow, editable install, etc.).
    candidates: list[Path] = []

    filestream_base = os.getenv(FILESTREAM_PATH_ENV, "/data/filestream")
    candidates.append(Path(filestream_base) / "teryt")

    cwd = Path.cwd()
    candidates.append(cwd / "data" / "teryt")

    current = Path(__file__).resolve()
    for parent in (current.parent, *current.parents):
        candidates.append(parent / "data" / "teryt")

    for candidate in candidates:
        if teryt_files_exist(candidate):
            return candidate

    return candidates[0]


def resolve_teryt_dir() -> Path:
    override = os.getenv(TERYT_DIR_ENV, "").strip()
    if override:
        return Path(override)
    return resolve_default_teryt_dir()


def teryt_files_exist(teryt_dir: Path) -> bool:
    if not teryt_dir.is_dir():
        return False

    simc = find_file_case_insensitive(teryt_dir, "SIMC.csv")
    ulic = find_file_case_insensitive(teryt_dir, "ULIC.csv")
    return simc is not None and ulic is not None


def find_file_case_insensitive(directory: Path, filename: str) -> Path | None:
    direct = directory / filename
    if direct.is_file():
        return direct

    target = filename.casefold()
    try:
        for entry in directory.iterdir():
            if entry.is_file() and entry.name.casefold() == target:
                return entry
    except OSError:
        return None
    return None


def get_teryt_index() -> tuple[dict[str, set[str]], dict[str, set[str]], set[str]]:
    teryt_dir = str(resolve_teryt_dir().resolve())
    return load_teryt_index(teryt_dir)


@lru_cache(maxsize=8)
def load_teryt_index(teryt_dir: str) -> tuple[dict[str, set[str]], dict[str, set[str]], set[str]]:
    teryt_dir_path = Path(teryt_dir)
    simc_path = find_file_case_insensitive(teryt_dir_path, "SIMC.csv")
    ulic_path = find_file_case_insensitive(teryt_dir_path, "ULIC.csv")
    if simc_path is None or ulic_path is None:
        return {}, {}, set()

    city_to_syms: dict[str, set[str]] = {}
    with simc_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            name = normalize_teryt_key(row.get("NAZWA"))
            sym = normalize_teryt_key(row.get("SYM"))
            if not name or not sym:
                continue
            city_to_syms.setdefault(name, set()).add(sym)

    streets_by_sym: dict[str, set[str]] = {}
    streets_anywhere: set[str] = set()
    with ulic_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            sym = normalize_teryt_key(row.get("SYM"))
            if not sym:
                continue
            variants = build_teryt_street_key_variants(
                cecha=row.get("CECHA"),
                nazwa_1=row.get("NAZWA_1"),
                nazwa_2=row.get("NAZWA_2"),
            )
            for street_key in variants:
                streets_by_sym.setdefault(sym, set()).add(street_key)
                streets_anywhere.add(street_key)

    return city_to_syms, streets_by_sym, streets_anywhere


def normalize_teryt_key(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return re.sub(r"\s+", " ", str(value).strip().upper()) or None


def canonicalize_street_prefix(value: str | None) -> str | None:
    if not value:
        return None
    raw = str(value).strip().casefold().removesuffix(".")
    if raw in {"ul", "ulica"}:
        return "UL"
    if raw in {"al", "aleja"}:
        return "AL"
    if raw in {"os", "osiedle"}:
        return "OS"
    if raw in {"pl", "plac"}:
        return "PL"
    return None


def build_teryt_street_key(cecha: Any, nazwa_1: Any, nazwa_2: Any) -> str | None:
    prefix = canonicalize_street_prefix(None if cecha is None else str(cecha))
    name_1 = normalize_teryt_key(nazwa_1)
    name_2 = normalize_teryt_key(nazwa_2)
    if not prefix or not name_1:
        return None
    name = name_1 if not name_2 else f"{name_1} {name_2}"
    return f"{prefix} {name}".strip()


def build_teryt_street_key_variants(cecha: Any, nazwa_1: Any, nazwa_2: Any) -> set[str]:
    prefix = canonicalize_street_prefix(None if cecha is None else str(cecha))
    name_1 = normalize_teryt_key(nazwa_1)
    name_2 = normalize_teryt_key(nazwa_2)
    if not prefix or not name_1:
        return set()

    variants = {f"{prefix} {name_1}".strip()}
    if name_2:
        variants.add(f"{prefix} {name_1} {name_2}".strip())
    return variants


def split_normalized_street(value: str | None) -> tuple[str | None, str | None]:
    if value in (None, ""):
        return None, None
    normalized = normalize_teryt_key(value)
    if not normalized:
        return None, None
    parts = normalized.split(" ", 1)
    if len(parts) == 1:
        return None, normalized
    prefix = canonicalize_street_prefix(parts[0])
    if not prefix:
        return None, normalized
    return prefix, parts[1].strip() or None


def swap_last_token_to_front(value: str) -> str | None:
    tokens = value.split()
    if len(tokens) < 2:
        return None
    last = tokens[-1]
    rest = tokens[:-1]
    swapped = " ".join([last, *rest]).strip()
    return swapped or None


def validate_teryt_city_exists(city_normalized: str | None) -> bool:
    if city_normalized in (None, ""):
        return True
    city_to_syms, _, _ = get_teryt_index()
    key = normalize_teryt_key(city_normalized)
    return bool(key and key in city_to_syms)


def validate_teryt_street_exists(city_normalized: str | None, street_normalized: str | None) -> bool:
    if street_normalized in (None, ""):
        return True

    prefix, name = split_normalized_street(street_normalized)
    if not prefix or not name:
        return False
    street_key = f"{prefix} {name}".strip()
    swapped_name = swap_last_token_to_front(name)
    swapped_key = f"{prefix} {swapped_name}".strip() if swapped_name else None

    city_to_syms, streets_by_sym, streets_anywhere = get_teryt_index()
    if city_normalized not in (None, ""):
        city_key = normalize_teryt_key(city_normalized)
        if not city_key:
            return False
        syms = city_to_syms.get(city_key)
        if not syms:
            return False
        return any(
            street_key in streets_by_sym.get(sym, set())
            or (swapped_key is not None and swapped_key in streets_by_sym.get(sym, set()))
            for sym in syms
        )

    return street_key in streets_anywhere or (swapped_key is not None and swapped_key in streets_anywhere)


def validate_optional_identifier(identifier_type: str, value: str | None) -> bool:
    if value in (None, ""):
        return True
    return validate_polish_identifier(identifier_type, value)


def validate_optional_krs(value: str | None) -> bool:
    if value in (None, ""):
        return True
    return KRS_RE.match(str(value)) is not None


def validate_optional_lei(value: str | None) -> bool:
    if value in (None, ""):
        return True
    return validate_lei_checksum(str(value))


def validate_optional_id_card(value: str | None) -> bool:
    if value in (None, ""):
        return True
    return validate_polish_id_card_checksum(str(value))


def validate_polish_identifier(identifier_type: str, value: str | None) -> bool:
    if value in (None, ""):
        return False

    normalized_value = str(value)
    if identifier_type == "PESEL":
        if pesel is not None:
            return pesel.is_valid(normalized_value)
        return validate_pesel_checksum(normalized_value)
    if identifier_type == "NIP":
        if nip is not None:
            return nip.is_valid(normalized_value)
        return validate_nip_checksum(normalized_value)
    if identifier_type == "REGON":
        if regon is not None:
            return regon.is_valid(normalized_value)
        return validate_regon_checksum(normalized_value)
    return False


def validate_email_value(value: str | None, check_dns: bool = True) -> bool:
    if value in (None, ""):
        return True

    normalized_value = str(value).strip()
    if validate_email is None:
        if EMAIL_FALLBACK_RE.match(normalized_value) is None:
            return False
        domain = normalized_value.rsplit("@", 1)[1].lower()
    else:
        try:
            email_info = validate_email(normalized_value, check_deliverability=False)
        except EmailNotValidError:
            return False
        domain = email_info.domain.lower()

    if not check_dns:
        return True
    return email_domain_exists(domain)


@lru_cache(maxsize=1024)
def email_domain_exists(domain: str) -> bool:
    normalized_domain = domain.strip().rstrip(".").lower()
    if "." not in normalized_domain:
        return False

    if domain_address_exists(normalized_domain):
        return True

    if dns is None:
        return False

    for resolver in email_dns_resolvers():
        if dns_record_exists(resolver, normalized_domain, "MX"):
            return True
    return False


def domain_address_exists(domain: str) -> bool:
    try:
        socket.getaddrinfo(domain, None, type=socket.SOCK_STREAM)
        return True
    except OSError:
        return False


def email_dns_resolvers() -> list[Any]:
    resolvers = [dns.resolver.Resolver()]
    for resolver in resolvers:
        resolver.timeout = EMAIL_DNS_TIMEOUT_SECONDS
        resolver.lifetime = EMAIL_DNS_TIMEOUT_SECONDS
    return resolvers


def dns_record_exists(resolver: Any, domain: str, record_type: str) -> bool:
    try:
        resolver.resolve(domain, record_type)
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
        return False
    except dns.exception.DNSException:
        return False


def validate_person_name(value: str | None) -> bool:
    if value in (None, ""):
        return True
    return PERSON_NAME_RE.match(str(value)) is not None


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_pesel_checksum(value: str) -> bool:
    if not value.isdigit() or len(value) != 11:
        return False
    weights = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
    checksum = sum(int(value[index]) * weight for index, weight in enumerate(weights))
    control_digit = (10 - checksum % 10) % 10
    return control_digit == int(value[-1])


def validate_pesel_birth_date_match(pesel_value: str | None, birth_date_value: Any) -> bool:
    pesel_birth_date = extract_pesel_birth_date(pesel_value)
    if pesel_birth_date is None:
        return False
    if birth_date_value in (None, ""):
        return True

    birth_date = normalize_date_value(birth_date_value)
    if birth_date is None:
        return False

    return pesel_birth_date == birth_date


def validate_pesel_sex_match(pesel_value: str | None, sex_value: Any) -> bool:
    sex = normalize_sex_value(sex_value)
    if sex is None:
        return True

    pesel_sex = extract_pesel_sex(pesel_value)
    if pesel_sex is None:
        return False
    return pesel_sex == sex


def validate_pesel_birth_date_not_future(pesel_value: str | None) -> bool:
    pesel_birth_date = extract_pesel_birth_date(pesel_value)
    if pesel_birth_date is None:
        return True
    return pesel_birth_date <= date.today()


def validate_date_not_in_future(value: Any) -> bool:
    normalized_date = normalize_date_value(value)
    if normalized_date is None:
        return True
    return normalized_date <= date.today()


def validate_date_order(start_value: Any, end_value: Any) -> bool:
    start_date = normalize_date_value(start_value)
    end_date = normalize_date_value(end_value)
    if start_value not in (None, "") and start_date is None:
        return False
    if end_value not in (None, "") and end_date is None:
        return False
    if start_date is None or end_date is None:
        return True
    return start_date <= end_date


def format_date_range_checked_value(start_value: Any, end_value: Any) -> str | None:
    if start_value in (None, "") and end_value in (None, ""):
        return None
    return f"start={start_value}; end={end_value}"


def extract_pesel_birth_date(value: str | None) -> date | None:
    if value in (None, ""):
        return None

    normalized_value = str(value)
    if not normalized_value.isdigit() or len(normalized_value) != 11:
        return None

    year = int(normalized_value[0:2])
    encoded_month = int(normalized_value[2:4])
    day = int(normalized_value[4:6])

    for month_offset, century in PESEL_MONTH_CENTURY_OFFSETS:
        month = encoded_month - month_offset
        if 1 <= month <= 12:
            try:
                return date(century + year, month, day)
            except ValueError:
                return None
    return None


def extract_pesel_sex(value: str | None) -> bool | None:
    if value in (None, ""):
        return None

    normalized_value = str(value)
    if not normalized_value.isdigit() or len(normalized_value) != 11:
        return None

    return int(normalized_value[9]) % 2 == 0


def normalize_date_value(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        normalized_value = value.strip()
        if not normalized_value:
            return None
        try:
            return date.fromisoformat(normalized_value[:10])
        except ValueError:
            return None
    return None


def get_staging_sex_value(staging_record: Any) -> bool | None:
    raw_record_sex = extract_raw_record_sex_value(getattr(staging_record, "Raw_Record_JSON", None))
    if raw_record_sex is not None:
        return raw_record_sex
    return normalize_sex_value(getattr(staging_record, "Sex", None))


def extract_raw_record_sex_value(raw_record_json: str | None) -> bool | None:
    if raw_record_json in (None, ""):
        return None

    try:
        raw_record = json.loads(str(raw_record_json))
    except json.JSONDecodeError:
        return None

    if not isinstance(raw_record, dict):
        return None

    for field_name, value in raw_record.items():
        if str(field_name).strip().casefold() in SEX_SOURCE_FIELD_NAMES:
            sex = normalize_sex_value(value)
            if sex is not None:
                return sex
    return None


def normalize_sex_value(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False

    normalized_value = str(value).strip().casefold()
    if normalized_value in FEMALE_SEX_VALUES:
        return True
    if normalized_value in MALE_SEX_VALUES:
        return False
    return None


def validate_nip_checksum(value: str) -> bool:
    if not value.isdigit() or len(value) != 10:
        return False
    weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    checksum = sum(int(value[index]) * weight for index, weight in enumerate(weights)) % 11
    return checksum != 10 and checksum == int(value[-1])


def validate_regon_checksum(value: str) -> bool:
    if not value.isdigit() or len(value) not in (9, 14):
        return False
    if len(value) == 9:
        return validate_regon_9_checksum(value)
    return validate_regon_9_checksum(value[:9]) and validate_regon_14_checksum(value)


def validate_regon_9_checksum(value: str) -> bool:
    weights = [8, 9, 2, 3, 4, 5, 6, 7]
    checksum = sum(int(value[index]) * weight for index, weight in enumerate(weights)) % 11
    checksum = 0 if checksum == 10 else checksum
    return checksum == int(value[8])


def validate_regon_14_checksum(value: str) -> bool:
    weights = [2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8]
    checksum = sum(int(value[index]) * weight for index, weight in enumerate(weights)) % 11
    checksum = 0 if checksum == 10 else checksum
    return checksum == int(value[13])


def validate_lei_checksum(value: str) -> bool:
    normalized_value = value.strip().upper()
    if lei is not None:
        return lei.is_valid(normalized_value)
    if not re.match(r"^[0-9A-Z]{20}$", normalized_value):
        return False
    expanded = "".join(
        str(ord(character) - 55) if character.isalpha() else character
        for character in normalized_value
    )
    return int(expanded) % 97 == 1


def validate_polish_id_card_checksum(value: str) -> bool:
    normalized_value = value.strip().upper()
    if POLISH_ID_CARD_RE.match(normalized_value) is None:
        return False

    values = [
        POLISH_ID_CARD_LETTER_VALUES[normalized_value[0]],
        POLISH_ID_CARD_LETTER_VALUES[normalized_value[1]],
        POLISH_ID_CARD_LETTER_VALUES[normalized_value[2]],
        int(normalized_value[4]),
        int(normalized_value[5]),
        int(normalized_value[6]),
        int(normalized_value[7]),
        int(normalized_value[8]),
    ]
    weights = [7, 3, 1, 7, 3, 1, 7, 3]
    checksum = sum(value * weight for value, weight in zip(values, weights)) % 10
    return checksum == int(normalized_value[3])
