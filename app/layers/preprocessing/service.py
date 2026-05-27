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
STREET_CITY_LINE_RE = re.compile(r"^\s*(?P<street_part>.+?),\s*(?P<city>[^,]+?)\s*$")
POSTAL_CITY_LINE_RE = re.compile(r"^\s*(?P<postal_code>\d{2}-\d{3})\s+(?P<city>.+?)\s*$")
STREET_BUILDING_LINE_RE = re.compile(
    r"^\s*(?P<street>.+?)\s+(?P<building>\d+[A-Za-z]?(?:[-/]\d+[A-Za-z]?)?)\s*$"
)
BUILDING_ONLY_RE = re.compile(r"^\s*(?P<building>\d+[A-Za-z]?(?:[-/]\d+[A-Za-z]?)?)\s*$")
POSTAL_CODE_IN_TEXT_RE = re.compile(r"\b\d{2}-\d{3}\b")
NON_DIGIT_RE = re.compile(r"\D+")
NON_ALNUM_RE = re.compile(r"[^0-9A-Z]+")
MULTISPACE_RE = re.compile(r"\s+")
SHORT_NAME_EDGE_SEPARATOR_RE = re.compile(r"^[\s,.;:-]+|[\s,.;:-]+$")

LEGAL_FORM_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bS\.?\s*A\.?\b", re.IGNORECASE), "S.A."),
    (re.compile(r"\bSPÓŁKA\s+AKCYJNA\b", re.IGNORECASE), "S.A."),
    (re.compile(r"\bSPOLKA\s+AKCYJNA\b", re.IGNORECASE), "S.A."),
    (
        re.compile(r"\bSP(?:ÓŁKA)?\.?\s*Z\.?\s*O\.?\s*O\.?\b", re.IGNORECASE),
        "SP. Z O.O.",
    ),
    (
        re.compile(r"\bSPÓŁKA\s+Z\s+OGRANICZONĄ\s+ODPOWIEDZIALNOŚCIĄ\b", re.IGNORECASE),
        "SP. Z O.O.",
    ),
    (
        re.compile(r"\bSPOLKA\s+Z\s+OGRANICZONA\s+ODPOWIEDZIALNOSCIA\b", re.IGNORECASE),
        "SP. Z O.O.",
    ),
    (re.compile(r"\bSP\.?\s*J\.?\b", re.IGNORECASE), "SP. J."),
    (re.compile(r"\bSP\.?\s*K\.?\b", re.IGNORECASE), "SP. K."),
    (re.compile(r"\bS\.?\s*K\.?\s*A\.?\b", re.IGNORECASE), "S.K.A."),
    (re.compile(r"\bS\.?\s*C\.?\b", re.IGNORECASE), "S.C."),
    (re.compile(r"\bFUNDACJ[AE]\b", re.IGNORECASE), "FUNDACJA"),
    (re.compile(r"\bSTOWARZYSZENI[EA]\b", re.IGNORECASE), "STOWARZYSZENIE"),
]

LEGAL_ENTITY_TYPE_ALIASES = {
    "LLCPL": "SP. Z O.O.",
    "JSCPL": "S.A.",
}


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
    postal_city: str | None = None
    postal_code: str | None = None
    district: str | None = None
    province: str | None = None
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
    street_normalized = normalize_text_key(address_parts.street)
    building_number_normalized = normalize_identifier(address_parts.building_number)
    apartment_number_normalized = normalize_identifier(address_parts.apartment_number)
    postal_code_normalized = normalize_postal_code(address_parts.postal_code)
    city_normalized = normalize_city_text(address_parts.city)
    postal_city_normalized = normalize_city_text(address_parts.postal_city)
    country_normalized = normalize_text_key(address_parts.country)
    full_address_normalized = build_full_address_normalized(
        street_normalized,
        building_number_normalized,
        apartment_number_normalized,
        postal_code_normalized,
        city_normalized,
        country_normalized,
    )
    base = {
        "Staging_ID": staging_record.Staging_ID,
        "ImportBatch_ID": staging_record.ImportBatch_ID,
        "RawFile_ID": staging_record.RawFile_ID,
        "Source_Record_ID": empty_to_none(staging_record.Source_Record_ID),
        "Street_Normalized": street_normalized,
        "Building_Number_Normalized": building_number_normalized,
        "Apartment_Number_Normalized": apartment_number_normalized,
        "City_Normalized": city_normalized,
        "Postal_City_Normalized": postal_city_normalized,
        "Postal_Code_Normalized": postal_code_normalized,
        "District_Normalized": normalize_text_key(address_parts.district),
        "Province_Normalized": normalize_text_key(address_parts.province),
        "Country_Normalized": country_normalized,
        "Full_Address_Normalized": full_address_normalized,
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
                "Serial_Number_ID_Card_Normalized": normalize_identifier(
                    getattr(staging_record, "Serial_Number_ID_Card", None)
                ),
                "Serial_Number_Passport_Normalized": normalize_identifier(
                    getattr(staging_record, "Serial_Number_Passport", None)
                ),
                "First_Name_Normalized": first_name,
                "Second_Name_Normalized": second_name,
                "Last_Name_Normalized": last_name,
                "Family_Name_Normalized": family_name,
                "Full_Name_Normalized": compact_text(
                    " ".join(part for part in (first_name, second_name, last_name) if part)
                ),
                "Birth_Date": getattr(staging_record, "Birth_Date", None),
                "Place_Of_Birth_Normalized": normalize_text_key(
                    getattr(staging_record, "Place_Of_Birth", None)
                ),
                "Sex": getattr(staging_record, "Sex", None),
                "Citizenship_Normalized": normalize_text_key(
                    getattr(staging_record, "Citizenship", None)
                ),
                "Phone_Normalized": normalize_phone(staging_record.Phone_Number),
                "Email_Normalized": normalize_email(staging_record.Email_Address),
            }
        )
        return base

    identifiers = parse_identifiers_json(staging_record.Identifiers_JSON)
    name_value = empty_to_none(staging_record.Name)
    short_name_value = empty_to_none(staging_record.Short_Name)
    legal_entity_type_value = empty_to_none(staging_record.Legal_Entity_Type)
    registration_identifier_type = infer_registration_identifier_type(
        getattr(staging_record, "Validation_Authority_ID", None)
    )
    registration_identifier_value = normalize_identifier(
        getattr(staging_record, "Validation_Authority_Entity_ID", None)
    )
    regon_value = normalize_identifier(identifiers.get("REGON"))
    krs_value = normalize_identifier(identifiers.get("KRS"))
    if registration_identifier_type == "REGON" and regon_value is None:
        regon_value = registration_identifier_value
    elif registration_identifier_type == "KRS" and krs_value is None:
        krs_value = registration_identifier_value

    inferred_short_name, inferred_legal_type = split_party_name_and_legal_form(name_value)
    if short_name_value is None:
        short_name_value = inferred_short_name
    if legal_entity_type_value is None:
        legal_entity_type_value = inferred_legal_type
    base.update(
        {
            "Name_Normalized": normalize_text_key(name_value),
            "Short_Name_Normalized": normalize_text_key(short_name_value),
            "Legal_Entity_Type_Normalized": normalize_legal_entity_type(
                legal_entity_type_value
            ),
            "Registration_Country_Normalized": normalize_text_key(
                getattr(staging_record, "Registration_Country", None)
            ),
            "Establishment_Date": getattr(staging_record, "Establishment_Date", None),
            "NIP_Normalized": normalize_identifier(identifiers.get("NIP")),
            "REGON_Normalized": regon_value,
            "KRS_Normalized": krs_value,
            "LEI_Normalized": normalize_identifier(identifiers.get("LEI")),
            "Register_Status_Normalized": normalize_text_key(
                getattr(staging_record, "Register_Status", None)
            ),
            "Registration_Date": getattr(staging_record, "Registration_Date", None),
            "Deregistration_Date": getattr(staging_record, "Deregistration_Date", None),
            "Decision_Date": getattr(staging_record, "Decision_Date", None),
            "Decision_Number_Normalized": normalize_identifier(
                getattr(staging_record, "Decision_Number", None)
            ),
            "Register_Number_Normalized": normalize_identifier(
                getattr(staging_record, "Register_Number", None)
            ),
            "Bank_Accounts_Normalized_JSON": normalize_json_text(
                getattr(staging_record, "Bank_Accounts_JSON", None)
            ),
            "Has_Virtual_Accounts": getattr(staging_record, "Has_Virtual_Accounts", None),
            "Business_Scope_Normalized": normalize_text_key(
                getattr(staging_record, "Business_Scope", None)
            ),
            "Ownership_Form_Normalized": normalize_text_key(
                getattr(staging_record, "Ownership_Form", None)
            ),
            "Municipality_Normalized": normalize_city_text(
                getattr(staging_record, "Municipality", None)
            ),
            "Phone_Normalized": normalize_phone(staging_record.Phone_Number),
            "Email_Normalized": normalize_email(staging_record.Email_Address),
            "Website_Normalized": normalize_website(staging_record.Website),
            "Agent_Type_Normalized": normalize_text_key(getattr(staging_record, "Agent_Type", None)),
            "Insurance_Company_Normalized": normalize_text_key(
                getattr(staging_record, "Insurance_Company", None)
            ),
            "Related_Persons_Normalized_JSON": normalize_json_text(
                getattr(staging_record, "Related_Persons_JSON", None)
            ),
            "Related_Parties_Normalized_JSON": normalize_json_text(
                getattr(staging_record, "Related_Parties_JSON", None)
            ),
            "Registration_Status_Normalized": normalize_text_key(
                getattr(staging_record, "Registration_Status", None)
            ),
            "Last_Update_Date": getattr(staging_record, "Last_Update_Date", None),
            "Next_Renewal_Date": getattr(staging_record, "Next_Renewal_Date", None),
            "Managing_LOU_Normalized": normalize_identifier(
                getattr(staging_record, "Managing_LOU", None)
            ),
            "Validation_Sources_Normalized": normalize_text_key(
                getattr(staging_record, "Validation_Sources", None)
            ),
            "Validation_Authority_ID_Normalized": normalize_text_key(
                getattr(staging_record, "Validation_Authority_ID", None)
            ),
            "Validation_Authority_Entity_ID_Normalized": normalize_identifier(
                getattr(staging_record, "Validation_Authority_Entity_ID", None)
            ),
            "Direct_Parent_LEI_Normalized": normalize_identifier(
                getattr(staging_record, "Direct_Parent_LEI", None)
            ),
            "Direct_Parent_Name_Normalized": normalize_text_key(
                getattr(staging_record, "Direct_Parent_Name", None)
            ),
            "Direct_Parent_Relationship_Type_Normalized": normalize_text_key(
                getattr(staging_record, "Direct_Parent_Relationship_Type", None)
            ),
            "Direct_Parent_Relationship_Status_Normalized": normalize_text_key(
                getattr(staging_record, "Direct_Parent_Relationship_Status", None)
            ),
            "Direct_Parent_Relationship_Start_Date": getattr(
                staging_record, "Direct_Parent_Relationship_Start_Date", None
            ),
            "Direct_Parent_Relationship_End_Date": getattr(
                staging_record, "Direct_Parent_Relationship_End_Date", None
            ),
            "Ultimate_Parent_LEI_Normalized": normalize_identifier(
                getattr(staging_record, "Ultimate_Parent_LEI", None)
            ),
            "Ultimate_Parent_Name_Normalized": normalize_text_key(
                getattr(staging_record, "Ultimate_Parent_Name", None)
            ),
            "Ultimate_Parent_Relationship_Type_Normalized": normalize_text_key(
                getattr(staging_record, "Ultimate_Parent_Relationship_Type", None)
            ),
            "Ultimate_Parent_Relationship_Status_Normalized": normalize_text_key(
                getattr(staging_record, "Ultimate_Parent_Relationship_Status", None)
            ),
            "Ultimate_Parent_Relationship_Start_Date": getattr(
                staging_record, "Ultimate_Parent_Relationship_Start_Date", None
            ),
            "Ultimate_Parent_Relationship_End_Date": getattr(
                staging_record, "Ultimate_Parent_Relationship_End_Date", None
            ),
        }
    )
    return base


def split_address_from_staging(staging_record: Any) -> AddressParts:
    parts = AddressParts(
        street=empty_to_none(staging_record.Street),
        building_number=empty_to_none(staging_record.Building_Number),
        apartment_number=empty_to_none(staging_record.Apartment_Number),
        city=empty_to_none(staging_record.City),
        postal_city=empty_to_none(staging_record.Postal_City),
        postal_code=empty_to_none(staging_record.Postal_Code),
        district=empty_to_none(getattr(staging_record, "District", None)),
        province=empty_to_none(getattr(staging_record, "Province", None)),
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
            street_part = full_match.group("street_part")
            parts.postal_code = parts.postal_code or full_match.group("postal_code")
            parts.city = parts.city or normalize_city_text(full_match.group("city"))
            split_street_line(parts, street_part)
            if (
                BUILDING_ONLY_RE.match(normalize_street_line(street_part)) is not None
                and not looks_like_street_line(street_part)
                and parts.street == address_line
            ):
                parts.street = None
            return True

    street_city_match = STREET_CITY_LINE_RE.match(address_line)
    if street_city_match and (
        looks_like_street_line(street_city_match.group("street_part"))
        or BUILDING_ONLY_RE.match(normalize_street_line(street_city_match.group("street_part"))) is not None
    ):
        street_part = street_city_match.group("street_part")
        parsed_city = normalize_city_text(street_city_match.group("city"))
        parts.city = parsed_city if parts.city == address_line else parts.city or parsed_city
        split_street_line(parts, street_part)
        if (
            BUILDING_ONLY_RE.match(normalize_street_line(street_part)) is not None
            and not looks_like_street_line(street_part)
            and parts.street == address_line
        ):
            parts.street = None
        return True

    city_street_match = CITY_STREET_LINE_RE.match(address_line)
    if city_street_match and looks_like_street_line(city_street_match.group("street_part")):
        parsed_city = normalize_city_text(city_street_match.group("city"))
        parts.city = parsed_city if parts.city == address_line else parts.city or parsed_city
        split_street_line(parts, city_street_match.group("street_part"))
        return True

    postal_city_match = POSTAL_CITY_LINE_RE.match(address_line)
    if postal_city_match:
        parts.postal_code = parts.postal_code or postal_city_match.group("postal_code")
        parsed_city = normalize_city_text(postal_city_match.group("city"))
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

    building_only_match = BUILDING_ONLY_RE.match(normalized_line)
    if building_only_match and not looks_like_street_line(normalized_line):
        building_number, apartment_number = split_building_and_apartment(
            building_only_match.group("building")
        )
        parts.building_number = parts.building_number or building_number
        parts.apartment_number = parts.apartment_number or apartment_number
        if parts.street == street_line:
            parts.street = None
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


def normalize_city_text(value: Any) -> str | None:
    value = empty_to_none(value)
    if value is None:
        return None
    text = compact_text(str(value).upper())
    if text is None:
        return None
    # Zdarza się, że do pola miasta trafia powtórzony fragment z kodem (np. "TCZEW 83-110 TCZEW").
    without_postal = compact_text(POSTAL_CODE_IN_TEXT_RE.sub(" ", text))
    if without_postal is None:
        return None
    return dedupe_repeated_tokens(without_postal)


def infer_legal_entity_type_from_name(value: Any) -> str | None:
    value = empty_to_none(value)
    if value is None:
        return None
    text = str(value)
    for pattern, label in LEGAL_FORM_PATTERNS:
        if pattern.search(text):
            return label
    return None


def normalize_legal_entity_type(value: Any) -> str | None:
    normalized = normalize_text_key(value)
    if normalized is None:
        return None

    # Kody z systemow zrodlowych tlumaczymy na wspolny slownik form prawnych
    alias_key = NON_ALNUM_RE.sub("", normalized)
    if alias_key in LEGAL_ENTITY_TYPE_ALIASES:
        return normalize_text_key(LEGAL_ENTITY_TYPE_ALIASES[alias_key])

    inferred = infer_legal_entity_type_from_name(normalized)
    if inferred is not None:
        return normalize_text_key(inferred)
    return normalized


def infer_registration_identifier_type(value: Any) -> str | None:
    normalized = normalize_text_key(value)
    if normalized is None:
        return None
    if "RA000466" in normalized or "KRS" in normalized or "COURT REGISTER" in normalized:
        return "KRS"
    if "RA000484" in normalized or "REGON" in normalized or "BUSINESS REGISTER" in normalized:
        return "REGON"
    return None


def split_party_name_and_legal_form(value: Any) -> tuple[str | None, str | None]:
    value = empty_to_none(value)
    if value is None:
        return None, None

    text = str(value)
    for pattern, label in LEGAL_FORM_PATTERNS:
        if pattern.search(text):
            short_name = clean_party_short_name(pattern.sub(" ", text))
            return short_name, label

    return compact_text(text), None


def clean_party_short_name(value: Any) -> str | None:
    value = empty_to_none(value)
    if value is None:
        return None

    text = SHORT_NAME_EDGE_SEPARATOR_RE.sub("", value)
    return compact_text(text)


def build_full_address_normalized(
    street: str | None,
    building_number: str | None,
    apartment_number: str | None,
    postal_code: str | None,
    city: str | None,
    country: str | None,
) -> str | None:
    parts: list[str] = []
    if street:
        parts.append(street)

    building_part: str | None = None
    if building_number and apartment_number:
        building_part = f"{building_number}/{apartment_number}"
    elif building_number:
        building_part = building_number
    elif apartment_number:
        building_part = apartment_number

    if building_part:
        parts.append(building_part)

    if postal_code:
        parts.append(postal_code)
    if city:
        parts.append(city)
    if country:
        parts.append(country)
    return compact_text(" ".join(parts))


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


def normalize_json_text(value: Any) -> str | None:
    value = empty_to_none(value)
    if value is None:
        return None
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return normalize_text_key(value)
    return normalize_text_key(json.dumps(parsed, ensure_ascii=False, sort_keys=True, default=str))


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


def dedupe_repeated_tokens(value: str) -> str:
    tokens = value.split()
    if len(tokens) >= 2 and len(tokens) % 2 == 0:
        half = len(tokens) // 2
        if tokens[:half] == tokens[half:]:
            return " ".join(tokens[:half])
    return value
