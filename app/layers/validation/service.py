from datetime import date, datetime
import json
import re
from dataclasses import dataclass
from typing import Any

from app.layers.staging_validation.mapper import normalize_entity_type


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
PERSON_NAME_RE = re.compile(r"^[A-Z][A-Z '\-]*$")
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
    check_email_dns: bool = False,
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
    check_email_dns: bool = False,
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
    return [
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


def validate_email_value(value: str | None, check_dns: bool = False) -> bool:
    if value in (None, ""):
        return True
    if validate_email is None:
        return EMAIL_FALLBACK_RE.match(str(value)) is not None
    try:
        validate_email(str(value), check_deliverability=check_dns)
        return True
    except EmailNotValidError:
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
