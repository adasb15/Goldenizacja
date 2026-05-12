import re
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
EMAIL_DNS_TIMEOUT_SECONDS = 2.0
PERSON_NAME_RE = re.compile(r"^[A-Z][A-Z '\-]*$")
KRS_RE = re.compile(r"^\d{10}$")
POLISH_ID_CARD_RE = re.compile(r"^[A-Z]{3}\d{6}$")
POLISH_ID_CARD_LETTER_VALUES = {chr(code): code - 55 for code in range(ord("A"), ord("Z") + 1)}


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
    if dns is None:
        return False

    normalized_domain = domain.strip().rstrip(".").lower()
    if "." not in normalized_domain:
        return False

    resolver = dns.resolver.Resolver()
    resolver.timeout = EMAIL_DNS_TIMEOUT_SECONDS
    resolver.lifetime = EMAIL_DNS_TIMEOUT_SECONDS

    if dns_record_exists(resolver, normalized_domain, "MX"):
        return True
    return dns_record_exists(resolver, normalized_domain, "A") or dns_record_exists(
        resolver, normalized_domain, "AAAA"
    )


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
