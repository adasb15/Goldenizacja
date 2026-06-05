"""Matching i scoring dla warstwy integration_golden."""

from __future__ import annotations

import hashlib
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from rapidfuzz.distance import JaroWinkler, Levenshtein

from app.layers.staging_validation.mapper import normalize_entity_type

FUZZY_AUTO_MERGE_THRESHOLD = 0.95
AUTO_MERGE_THRESHOLD = 0.90
REVIEW_THRESHOLD = 0.70
LEVENSHTEIN_CANDIDATE_THRESHOLD = 0.50
JARO_WINKLER_CANDIDATE_THRESHOLD = 0.78
JARO_WINKLER_REVIEW_THRESHOLD = 0.86
JARO_WINKLER_AUTO_MERGE_THRESHOLD = 0.94
DEFAULT_MATCHING_MAX_PAIRS = 2_000_000
STABLE_CONFLICT_SIMILARITY_THRESHOLD = 0.60
BLOCKING_CONFLICT_FIELD_COUNT = 3

FALLBACK_SOURCE_TRUST_LEVELS = {
    "CEIDG": 80,
    "KRS": 90,
    "REGON": 85,
    "VAT": 85,
    "PESEL": 90,
    "KNF_AGENT": 80,
    "KNF_PRACOWNIK_AGENTA": 80,
    "KNF_FIRMY_INWESTYCYJNE": 80,
    "KNF_PIENIADZ_ELEKTRONICZNY": 80,
    "GLEIF": 75,
    "INSURANCE_CORE": 70,
    "WWW_FORM": 50,
}

PERSON_DEFAULT_SOURCE_PRIORITY = (
    "PESEL",
    "CEIDG",
    "INSURANCE_CORE",
    "KNF_AGENT",
    "KNF_PRACOWNIK_AGENTA",
    "KNF_FIRMY_INWESTYCYJNE",
)

PARTY_DEFAULT_SOURCE_PRIORITY = (
    "KRS",
    "REGON",
    "VAT",
    "GLEIF",
    "CEIDG",
    "KNF_FIRMY_INWESTYCYJNE",
    "KNF_PIENIADZ_ELEKTRONICZNY",
    "KNF_AGENT",
    "KNF_PRACOWNIK_AGENTA",
    "INSURANCE_CORE",
)

PERSON_SOURCE_PRIORITY_BY_FIELD = {
    "PESEL": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Serial_Number_ID_Card": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Serial_Number_Passport": PERSON_DEFAULT_SOURCE_PRIORITY,
    "First_Name": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Second_Name": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Last_Name": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Family_Name": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Birth_Date": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Place_Of_Birth": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Sex": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Citizenship": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Phone_Number": (
        "CEIDG",
        "INSURANCE_CORE",
        "PESEL",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
    "Email_Address": (
        "CEIDG",
        "INSURANCE_CORE",
        "PESEL",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
    "Street": (
        "CEIDG",
        "PESEL",
        "INSURANCE_CORE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
    "Building_Number": (
        "CEIDG",
        "PESEL",
        "INSURANCE_CORE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
    "Apartment_Number": (
        "CEIDG",
        "PESEL",
        "INSURANCE_CORE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
    "City": (
        "CEIDG",
        "PESEL",
        "INSURANCE_CORE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
    "Postal_City": (
        "CEIDG",
        "PESEL",
        "INSURANCE_CORE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
    "Postal_Code": (
        "CEIDG",
        "PESEL",
        "INSURANCE_CORE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
    "District": (
        "CEIDG",
        "PESEL",
        "INSURANCE_CORE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
    "Province": (
        "CEIDG",
        "PESEL",
        "INSURANCE_CORE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
    "Country": PERSON_DEFAULT_SOURCE_PRIORITY,
    "Full_Address": (
        "CEIDG",
        "PESEL",
        "INSURANCE_CORE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "KNF_FIRMY_INWESTYCYJNE",
    ),
}

PARTY_SOURCE_PRIORITY_BY_FIELD = {
    "NIP": (
        "VAT",
        "REGON",
        "CEIDG",
        "KRS",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_PIENIADZ_ELEKTRONICZNY",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "INSURANCE_CORE",
        "GLEIF",
    ),
    "REGON": (
        "REGON",
        "VAT",
        "CEIDG",
        "KRS",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "INSURANCE_CORE",
        "GLEIF",
    ),
    "KRS": (
        "KRS",
        "REGON",
        "VAT",
        "CEIDG",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "INSURANCE_CORE",
        "GLEIF",
    ),
    "LEI": (
        "GLEIF",
        "KRS",
        "REGON",
        "VAT",
        "CEIDG",
        "INSURANCE_CORE",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_PIENIADZ_ELEKTRONICZNY",
    ),
    "Name": (
        "KRS",
        "REGON",
        "GLEIF",
        "VAT",
        "CEIDG",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_PIENIADZ_ELEKTRONICZNY",
        "KNF_AGENT",
        "KNF_PRACOWNIK_AGENTA",
        "INSURANCE_CORE",
    ),
    "Short_Name": (
        "CEIDG",
        "KRS",
        "REGON",
        "GLEIF",
        "VAT",
        "KNF_FIRMY_INWESTYCYJNE",
        "INSURANCE_CORE",
    ),
    "Legal_Entity_Type": (
        "KRS",
        "GLEIF",
        "REGON",
        "CEIDG",
        "KNF_PIENIADZ_ELEKTRONICZNY",
        "INSURANCE_CORE",
        "VAT",
    ),
    "Registration_Country": (
        "GLEIF",
        "KRS",
        "REGON",
        "CEIDG",
        "VAT",
        "INSURANCE_CORE",
    ),
    "Establishment_Date": (
        "KRS",
        "CEIDG",
        "REGON",
        "VAT",
        "GLEIF",
        "KNF_PIENIADZ_ELEKTRONICZNY",
        "INSURANCE_CORE",
    ),
    "Street": (
        "REGON",
        "VAT",
        "CEIDG",
        "KRS",
        "KNF_AGENT",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_PIENIADZ_ELEKTRONICZNY",
        "GLEIF",
        "INSURANCE_CORE",
    ),
    "Building_Number": (
        "REGON",
        "VAT",
        "CEIDG",
        "KRS",
        "KNF_AGENT",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_PIENIADZ_ELEKTRONICZNY",
        "GLEIF",
        "INSURANCE_CORE",
    ),
    "Apartment_Number": (
        "REGON",
        "VAT",
        "CEIDG",
        "KRS",
        "KNF_AGENT",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_PIENIADZ_ELEKTRONICZNY",
        "GLEIF",
        "INSURANCE_CORE",
    ),
    "City": (
        "REGON",
        "VAT",
        "CEIDG",
        "KRS",
        "KNF_AGENT",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_PIENIADZ_ELEKTRONICZNY",
        "GLEIF",
        "INSURANCE_CORE",
    ),
    "Postal_City": (
        "VAT",
        "REGON",
        "CEIDG",
        "KRS",
        "KNF_AGENT",
        "GLEIF",
        "INSURANCE_CORE",
    ),
    "Postal_Code": (
        "REGON",
        "VAT",
        "CEIDG",
        "KRS",
        "KNF_AGENT",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_PIENIADZ_ELEKTRONICZNY",
        "GLEIF",
        "INSURANCE_CORE",
    ),
    "District": ("REGON", "CEIDG", "KRS", "GLEIF", "INSURANCE_CORE"),
    "Province": ("REGON", "CEIDG", "KRS", "GLEIF", "INSURANCE_CORE"),
    "Country": ("GLEIF", "REGON", "KRS", "CEIDG", "VAT", "INSURANCE_CORE"),
    "Full_Address": (
        "REGON",
        "VAT",
        "CEIDG",
        "KRS",
        "KNF_AGENT",
        "KNF_FIRMY_INWESTYCYJNE",
        "KNF_PIENIADZ_ELEKTRONICZNY",
        "GLEIF",
        "INSURANCE_CORE",
    ),
    "Register_Status": ("KRS", "VAT", "CEIDG", "KNF_PIENIADZ_ELEKTRONICZNY", "GLEIF", "INSURANCE_CORE"),
    "Registration_Date": ("KRS", "VAT", "CEIDG", "KNF_FIRMY_INWESTYCYJNE", "KNF_AGENT", "GLEIF", "INSURANCE_CORE"),
    "Deregistration_Date": ("KRS", "VAT", "CEIDG", "KNF_AGENT", "KNF_PIENIADZ_ELEKTRONICZNY", "GLEIF", "INSURANCE_CORE"),
    "Decision_Date": ("KNF_FIRMY_INWESTYCYJNE", "KNF_PIENIADZ_ELEKTRONICZNY", "KRS", "INSURANCE_CORE"),
    "Decision_Number": ("KNF_FIRMY_INWESTYCYJNE", "KNF_PIENIADZ_ELEKTRONICZNY", "KRS", "INSURANCE_CORE"),
    "Register_Number": ("KNF_AGENT", "KNF_PRACOWNIK_AGENTA", "KNF_PIENIADZ_ELEKTRONICZNY", "KRS", "INSURANCE_CORE"),
    "Bank_Accounts_JSON": ("VAT", "INSURANCE_CORE", "CEIDG", "KRS", "REGON"),
    "Has_Virtual_Accounts": ("VAT", "INSURANCE_CORE"),
    "Business_Scope": ("REGON", "CEIDG", "KNF_FIRMY_INWESTYCYJNE", "KRS", "INSURANCE_CORE"),
    "Ownership_Form": ("REGON", "KRS", "CEIDG", "INSURANCE_CORE"),
    "Municipality": ("REGON", "CEIDG", "KRS", "INSURANCE_CORE"),
    "Phone_Number": ("REGON", "CEIDG", "INSURANCE_CORE", "KRS", "KNF_AGENT", "GLEIF"),
    "Email_Address": ("REGON", "CEIDG", "INSURANCE_CORE", "KRS", "KNF_AGENT", "GLEIF"),
    "Website": ("REGON", "CEIDG", "INSURANCE_CORE", "KRS", "GLEIF"),
    "Agent_Type": ("KNF_AGENT", "KNF_PRACOWNIK_AGENTA", "INSURANCE_CORE"),
    "Insurance_Company": ("KNF_AGENT", "KNF_PRACOWNIK_AGENTA", "INSURANCE_CORE"),
    "Related_Persons_JSON": ("KRS", "INSURANCE_CORE"),
    "Related_Parties_JSON": ("KRS", "GLEIF", "INSURANCE_CORE"),
    "Registration_Status": ("GLEIF", "KRS", "REGON", "INSURANCE_CORE"),
    "Last_Update_Date": ("GLEIF", "KRS", "VAT", "INSURANCE_CORE"),
    "Next_Renewal_Date": ("GLEIF", "INSURANCE_CORE"),
    "Managing_LOU": ("GLEIF", "INSURANCE_CORE"),
    "Validation_Sources": ("GLEIF", "KRS", "REGON", "INSURANCE_CORE"),
    "Validation_Authority_ID": ("GLEIF", "KRS", "REGON", "INSURANCE_CORE"),
    "Validation_Authority_Entity_ID": ("GLEIF", "KRS", "REGON", "INSURANCE_CORE"),
    "Direct_Parent_LEI": ("GLEIF", "INSURANCE_CORE"),
    "Direct_Parent_Name": ("GLEIF", "INSURANCE_CORE"),
    "Direct_Parent_Relationship_Type": ("GLEIF", "INSURANCE_CORE"),
    "Direct_Parent_Relationship_Status": ("GLEIF", "INSURANCE_CORE"),
    "Direct_Parent_Relationship_Start_Date": ("GLEIF", "INSURANCE_CORE"),
    "Direct_Parent_Relationship_End_Date": ("GLEIF", "INSURANCE_CORE"),
    "Ultimate_Parent_LEI": ("GLEIF", "INSURANCE_CORE"),
    "Ultimate_Parent_Name": ("GLEIF", "INSURANCE_CORE"),
    "Ultimate_Parent_Relationship_Type": ("GLEIF", "INSURANCE_CORE"),
    "Ultimate_Parent_Relationship_Status": ("GLEIF", "INSURANCE_CORE"),
    "Ultimate_Parent_Relationship_Start_Date": ("GLEIF", "INSURANCE_CORE"),
    "Ultimate_Parent_Relationship_End_Date": ("GLEIF", "INSURANCE_CORE"),
}


class MatchDecision(str, Enum):
    AUTO_MERGE = "AUTO_MERGE"
    REVIEW = "REVIEW"
    CANDIDATE = "CANDIDATE"
    NO_MATCH = "NO_MATCH"


class FieldRole(str, Enum):
    STRONG = "STRONG"
    FIXED = "FIXED"
    SEMI_FIXED = "SEMI_FIXED"
    DYNAMIC = "DYNAMIC"
    CONTEXT = "CONTEXT"


@dataclass(frozen=True)
class FieldRule:
    name: str
    weight: float
    role: FieldRole
    comparator: str = "levenshtein"
    aliases: tuple[str, ...] = ()
    decisive: bool = False


@dataclass(frozen=True)
class FieldScore:
    field: str
    role: FieldRole
    left_value: str | None
    right_value: str | None
    similarity: float | None
    weight: float
    contribution: float
    matched: bool


@dataclass(frozen=True)
class MatchResult:
    entity_type: str
    score: float
    decision: MatchDecision
    strong_match_fields: tuple[str, ...]
    conflict_fields: tuple[str, ...]
    field_scores: tuple[FieldScore, ...]


@dataclass(frozen=True)
class MatchCandidate:
    left_preprocessed_id: int
    right_preprocessed_id: int
    left_staging_id: int
    right_staging_id: int
    left_raw_file_id: int
    right_raw_file_id: int
    left_source_record_id: str | None
    right_source_record_id: str | None
    score: float
    decision: MatchDecision
    strong_match_fields: tuple[str, ...]
    conflict_fields: tuple[str, ...]


@dataclass(frozen=True)
class JaroWinklerCandidate:
    levenshtein_candidate_id: int
    left_preprocessed_id: int
    right_preprocessed_id: int
    left_staging_id: int
    right_staging_id: int
    left_raw_file_id: int
    right_raw_file_id: int
    left_source_record_id: str | None
    right_source_record_id: str | None
    levenshtein_score: float
    jaro_winkler_score: float
    decision: MatchDecision
    strong_match_fields: tuple[str, ...]
    conflict_fields: tuple[str, ...]
    text_match_fields: tuple[str, ...]


@dataclass(frozen=True)
class MatchingRunResult:
    entity_type: str
    raw_file_id: int | None
    records_in_scope: int
    records_compared_against: int
    pairs_evaluated: int
    candidates_out: int
    min_score: float
    candidates: tuple[MatchCandidate, ...]


@dataclass(frozen=True)
class JaroWinklerRunResult:
    entity_type: str
    raw_file_id: int | None
    candidates_in_scope: int
    candidates_out: int
    min_score: float
    candidates: tuple[JaroWinklerCandidate, ...]


@dataclass(frozen=True)
class EntityGroup:
    group_key: str
    member_preprocessed_ids: tuple[int, ...]


@dataclass(frozen=True)
class EntityGroupingRunResult:
    entity_type: str
    auto_merge_pairs_in_scope: int
    groups_out: int
    members_out: int
    groups: tuple[EntityGroup, ...]


@dataclass(frozen=True)
class SurvivorValueCandidate:
    value: Any
    source_system_code: str | None = None
    trust_level: int | float | None = None
    validation_status: str | bool | None = None
    import_started_at: datetime | None = None
    teryt_confirmed: bool | None = None


@dataclass(frozen=True)
class SurvivorValueSelection:
    value: Any
    source_system_code: str | None
    selected_by_rule: str
    trust_level: int | float | None
    validation_status: str | bool | None
    import_started_at: datetime | None
    teryt_confirmed: bool | None


@dataclass(frozen=True)
class GoldenDimensionLoadResult:
    entity_type: str
    entity_group_id: int
    member_preprocessed_ids: tuple[int, ...]
    dimension_id: int | None
    dimension_action: str
    address_id: int | None
    address_action: str
    address_link_action: str = "SKIPPED"
    party_identities_saved: int = 0


@dataclass(frozen=True)
class GoldenLoadRunResult:
    entity_type: str
    raw_file_id: int | None
    entity_group_id: int | None
    groups_in_scope: int
    groups_processed: int
    results: tuple[GoldenDimensionLoadResult, ...]


PERSON_FIELD_RULES = (
    FieldRule("PESEL", 1.0, FieldRole.STRONG, aliases=("PESEL_Normalized",), decisive=True),
    FieldRule(
        "Serial_Number_ID_Card",
        0.95,
        FieldRole.STRONG,
        aliases=("Serial_Number_ID_Card_Normalized",),
        decisive=True,
    ),
    FieldRule(
        "Serial_Number_Passport",
        0.95,
        FieldRole.STRONG,
        aliases=("Serial_Number_Passport_Normalized",),
        decisive=True,
    ),
    FieldRule("Birth_Date", 0.9, FieldRole.FIXED),
    FieldRule("First_Name", 0.65, FieldRole.SEMI_FIXED, aliases=("First_Name_Normalized",)),
    FieldRule("Second_Name", 0.55, FieldRole.SEMI_FIXED, aliases=("Second_Name_Normalized",)),
    FieldRule("Last_Name", 0.65, FieldRole.SEMI_FIXED, aliases=("Last_Name_Normalized",)),
    FieldRule("Family_Name", 0.55, FieldRole.SEMI_FIXED, aliases=("Family_Name_Normalized",)),
    FieldRule("Full_Name", 0.75, FieldRole.SEMI_FIXED, aliases=("Full_Name_Normalized",)),
    FieldRule("Place_Of_Birth", 0.6, FieldRole.FIXED, aliases=("Place_Of_Birth_Normalized",)),
    FieldRule("Sex", 0.2, FieldRole.SEMI_FIXED),
    FieldRule("Citizenship", 0.15, FieldRole.SEMI_FIXED, aliases=("Citizenship_Normalized",)),
    FieldRule("Phone_Number", 0.1, FieldRole.DYNAMIC, aliases=("Phone_Normalized",)),
    FieldRule("Email_Address", 0.12, FieldRole.DYNAMIC, aliases=("Email_Normalized",)),
    FieldRule("Street", 0.15, FieldRole.DYNAMIC, aliases=("Street_Normalized",)),
    FieldRule("Building_Number", 0.15, FieldRole.DYNAMIC, aliases=("Building_Number_Normalized",)),
    FieldRule("Apartment_Number", 0.08, FieldRole.DYNAMIC, aliases=("Apartment_Number_Normalized",)),
    FieldRule("City", 0.12, FieldRole.DYNAMIC, aliases=("City_Normalized",)),
    FieldRule("Postal_City", 0.12, FieldRole.DYNAMIC, aliases=("Postal_City_Normalized",)),
    FieldRule("Postal_Code", 0.18, FieldRole.DYNAMIC, aliases=("Postal_Code_Normalized",)),
    FieldRule("District", 0.08, FieldRole.DYNAMIC, aliases=("District_Normalized",)),
    FieldRule("Province", 0.06, FieldRole.DYNAMIC, aliases=("Province_Normalized",)),
    FieldRule("Country", 0.08, FieldRole.FIXED, aliases=("Country_Normalized",)),
    FieldRule("Full_Address", 0.12, FieldRole.DYNAMIC, aliases=("Full_Address_Normalized",)),
)

PARTY_FIELD_RULES = (
    FieldRule("NIP", 1.0, FieldRole.STRONG, aliases=("NIP_Normalized",), decisive=True),
    FieldRule("REGON", 0.95, FieldRole.STRONG, aliases=("REGON_Normalized",), decisive=True),
    FieldRule("KRS", 0.95, FieldRole.STRONG, aliases=("KRS_Normalized",), decisive=True),
    FieldRule("LEI", 1.0, FieldRole.STRONG, aliases=("LEI_Normalized",), decisive=True),
    FieldRule("Name", 0.75, FieldRole.SEMI_FIXED, aliases=("Name_Normalized",)),
    FieldRule("Short_Name", 0.55, FieldRole.SEMI_FIXED, aliases=("Short_Name_Normalized",)),
    FieldRule("Legal_Entity_Type", 0.2, FieldRole.SEMI_FIXED, aliases=("Legal_Entity_Type_Normalized",)),
    FieldRule("Registration_Country", 0.08, FieldRole.FIXED, aliases=("Registration_Country_Normalized",)),
    FieldRule("Establishment_Date", 0.55, FieldRole.FIXED),
    FieldRule("Street", 0.15, FieldRole.DYNAMIC, aliases=("Street_Normalized",)),
    FieldRule("Building_Number", 0.15, FieldRole.DYNAMIC, aliases=("Building_Number_Normalized",)),
    FieldRule("Apartment_Number", 0.08, FieldRole.DYNAMIC, aliases=("Apartment_Number_Normalized",)),
    FieldRule("City", 0.12, FieldRole.DYNAMIC, aliases=("City_Normalized",)),
    FieldRule("Postal_City", 0.12, FieldRole.DYNAMIC, aliases=("Postal_City_Normalized",)),
    FieldRule("Postal_Code", 0.18, FieldRole.DYNAMIC, aliases=("Postal_Code_Normalized",)),
    FieldRule("District", 0.08, FieldRole.DYNAMIC, aliases=("District_Normalized",)),
    FieldRule("Province", 0.06, FieldRole.DYNAMIC, aliases=("Province_Normalized",)),
    FieldRule("Country", 0.08, FieldRole.FIXED, aliases=("Country_Normalized",)),
    FieldRule("Full_Address", 0.12, FieldRole.DYNAMIC, aliases=("Full_Address_Normalized",)),
    FieldRule("Register_Status", 0.1, FieldRole.SEMI_FIXED, aliases=("Register_Status_Normalized",)),
    FieldRule("Registration_Date", 0.45, FieldRole.FIXED),
    FieldRule("Deregistration_Date", 0.25, FieldRole.SEMI_FIXED),
    FieldRule("Decision_Date", 0.35, FieldRole.FIXED),
    FieldRule("Decision_Number", 0.75, FieldRole.STRONG, aliases=("Decision_Number_Normalized",), decisive=True),
    FieldRule("Register_Number", 0.75, FieldRole.STRONG, aliases=("Register_Number_Normalized",), decisive=True),
    FieldRule("Bank_Accounts_JSON", 0.15, FieldRole.DYNAMIC, aliases=("Bank_Accounts_Normalized_JSON",)),
    FieldRule("Has_Virtual_Accounts", 0.05, FieldRole.CONTEXT),
    FieldRule("Business_Scope", 0.08, FieldRole.CONTEXT, aliases=("Business_Scope_Normalized",)),
    FieldRule("Ownership_Form", 0.08, FieldRole.CONTEXT, aliases=("Ownership_Form_Normalized",)),
    FieldRule("Municipality", 0.08, FieldRole.DYNAMIC, aliases=("Municipality_Normalized",)),
    FieldRule("Phone_Number", 0.1, FieldRole.DYNAMIC, aliases=("Phone_Normalized",)),
    FieldRule("Email_Address", 0.12, FieldRole.DYNAMIC, aliases=("Email_Normalized",)),
    FieldRule("Website", 0.12, FieldRole.DYNAMIC, aliases=("Website_Normalized",)),
    FieldRule("Agent_Type", 0.7, FieldRole.SEMI_FIXED, aliases=("Agent_Type_Normalized",)),
    FieldRule("Insurance_Company", 0.7, FieldRole.SEMI_FIXED, aliases=("Insurance_Company_Normalized",)),
    FieldRule("Related_Persons_JSON", 0.2, FieldRole.CONTEXT, aliases=("Related_Persons_Normalized_JSON",)),
    FieldRule("Related_Parties_JSON", 0.2, FieldRole.CONTEXT, aliases=("Related_Parties_Normalized_JSON",)),
    FieldRule("Registration_Status", 0.1, FieldRole.SEMI_FIXED, aliases=("Registration_Status_Normalized",)),
    FieldRule("Last_Update_Date", 0.05, FieldRole.CONTEXT),
    FieldRule("Next_Renewal_Date", 0.05, FieldRole.CONTEXT),
    FieldRule("Managing_LOU", 0.15, FieldRole.CONTEXT, aliases=("Managing_LOU_Normalized",)),
    FieldRule("Validation_Sources", 0.15, FieldRole.CONTEXT, aliases=("Validation_Sources_Normalized",)),
    FieldRule("Validation_Authority_ID", 0.7, FieldRole.SEMI_FIXED, aliases=("Validation_Authority_ID_Normalized",)),
    FieldRule(
        "Validation_Authority_Entity_ID",
        0.85,
        FieldRole.STRONG,
        aliases=("Validation_Authority_Entity_ID_Normalized",),
        decisive=True,
    ),
    FieldRule("Direct_Parent_LEI", 0.95, FieldRole.FIXED, aliases=("Direct_Parent_LEI_Normalized",)),
    FieldRule("Direct_Parent_Name", 0.6, FieldRole.SEMI_FIXED, aliases=("Direct_Parent_Name_Normalized",)),
    FieldRule(
        "Direct_Parent_Relationship_Type",
        0.2,
        FieldRole.CONTEXT,
        aliases=("Direct_Parent_Relationship_Type_Normalized",),
    ),
    FieldRule(
        "Direct_Parent_Relationship_Status",
        0.1,
        FieldRole.CONTEXT,
        aliases=("Direct_Parent_Relationship_Status_Normalized",),
    ),
    FieldRule("Direct_Parent_Relationship_Start_Date", 0.7, FieldRole.SEMI_FIXED),
    FieldRule("Direct_Parent_Relationship_End_Date", 0.1, FieldRole.CONTEXT),
    FieldRule("Ultimate_Parent_LEI", 0.95, FieldRole.FIXED, aliases=("Ultimate_Parent_LEI_Normalized",)),
    FieldRule("Ultimate_Parent_Name", 0.6, FieldRole.SEMI_FIXED, aliases=("Ultimate_Parent_Name_Normalized",)),
    FieldRule(
        "Ultimate_Parent_Relationship_Type",
        0.2,
        FieldRole.CONTEXT,
        aliases=("Ultimate_Parent_Relationship_Type_Normalized",),
    ),
    FieldRule(
        "Ultimate_Parent_Relationship_Status",
        0.1,
        FieldRole.CONTEXT,
        aliases=("Ultimate_Parent_Relationship_Status_Normalized",),
    ),
    FieldRule("Ultimate_Parent_Relationship_Start_Date", 0.7, FieldRole.SEMI_FIXED),
    FieldRule("Ultimate_Parent_Relationship_End_Date", 0.1, FieldRole.CONTEXT),
)


FIELD_RULES_BY_ENTITY_TYPE = {
    "PERSON": PERSON_FIELD_RULES,
    "PARTY": PARTY_FIELD_RULES,
}

JARO_WINKLER_RULES_BY_ENTITY_TYPE = {
    "PERSON": tuple(
        rule
        for rule in PERSON_FIELD_RULES
        if rule.name
        in {
            "First_Name",
            "Second_Name",
            "Last_Name",
            "Family_Name",
            "Full_Name",
            "Place_Of_Birth",
            "Street",
            "City",
            "Postal_City",
            "Full_Address",
        }
    ),
    "PARTY": tuple(
        rule
        for rule in PARTY_FIELD_RULES
        if rule.name
        in {
            "Name",
            "Short_Name",
            "Legal_Entity_Type",
            "Street",
            "City",
            "Postal_City",
            "Full_Address",
            "Business_Scope",
            "Ownership_Form",
            "Agent_Type",
            "Insurance_Company",
            "Direct_Parent_Name",
            "Ultimate_Parent_Name",
        }
    ),
}

COMPARATORS: dict[str, Callable[[Any, Any], float]] = {
    "levenshtein": lambda left, right: Levenshtein.normalized_similarity(
        normalize_value(left),
        normalize_value(right),
    ),
    "jaro_winkler": lambda left, right: JaroWinkler.similarity(
        normalize_value(left),
        normalize_value(right),
    ),
}


class PreprocessedRecordsNotFoundError(ValueError):
    pass


class MatchingPairLimitExceededError(ValueError):
    pass


class LevenshteinCandidatesNotFoundError(ValueError):
    pass


def create_repository(db: Any) -> Any:
    from app.layers.integration_golden.repository import IntegrationGoldenRepository

    return IntegrationGoldenRepository(db)


def get_source_priority_order(entity_type: str, field_name: str) -> tuple[str, ...]:
    entity_type = normalize_entity_type(entity_type)
    if entity_type == "PERSON":
        return PERSON_SOURCE_PRIORITY_BY_FIELD.get(field_name, PERSON_DEFAULT_SOURCE_PRIORITY)
    return PARTY_SOURCE_PRIORITY_BY_FIELD.get(field_name, PARTY_DEFAULT_SOURCE_PRIORITY)


def get_source_priority_rank(entity_type: str, field_name: str, source_system_code: str | None) -> int:
    priority_order = get_source_priority_order(entity_type, field_name)
    normalized_code = str(source_system_code or "").upper()
    try:
        return priority_order.index(normalized_code)
    except ValueError:
        return len(priority_order)


def select_survivor_value(
    entity_type: str,
    field_name: str,
    candidates: list[SurvivorValueCandidate | dict[str, Any] | Any],
) -> SurvivorValueSelection:
    normalized_candidates = [normalize_survivor_candidate(candidate) for candidate in candidates]
    if not normalized_candidates:
        return SurvivorValueSelection(
            value=None,
            source_system_code=None,
            selected_by_rule="NO_CANDIDATES",
            trust_level=None,
            validation_status=None,
            import_started_at=None,
            teryt_confirmed=None,
        )

    present_candidates = [candidate for candidate in normalized_candidates if not is_blank(candidate.value)]
    if not present_candidates:
        return SurvivorValueSelection(
            value=None,
            source_system_code=None,
            selected_by_rule="NO_NON_BLANK_VALUE",
            trust_level=None,
            validation_status=None,
            import_started_at=None,
            teryt_confirmed=None,
        )
    if len(present_candidates) == 1:
        return build_survivor_selection(present_candidates[0], "NON_EMPTY_VALUE")

    validated_candidates = [candidate for candidate in present_candidates if is_successful_validation(candidate.validation_status)]
    if validated_candidates:
        if len(validated_candidates) == 1:
            return build_survivor_selection(validated_candidates[0], "PASSED_VALIDATION")
        present_candidates = validated_candidates

    if is_address_field(field_name):
        teryt_confirmed_candidates = [
            candidate for candidate in present_candidates if candidate.teryt_confirmed is True
        ]
        if teryt_confirmed_candidates:
            if len(teryt_confirmed_candidates) == 1:
                return build_survivor_selection(teryt_confirmed_candidates[0], "TERYT_CONFIRMED_ADDRESS")
            present_candidates = teryt_confirmed_candidates

    best_source_rank = min(
        get_source_priority_rank(entity_type, field_name, candidate.source_system_code)
        for candidate in present_candidates
    )
    prioritized_candidates = [
        candidate
        for candidate in present_candidates
        if get_source_priority_rank(entity_type, field_name, candidate.source_system_code) == best_source_rank
    ]
    if len(prioritized_candidates) == 1:
        return build_survivor_selection(prioritized_candidates[0], "SOURCE_PRIORITY")
    present_candidates = prioritized_candidates

    best_trust_level = max(normalize_trust_level(candidate.trust_level) for candidate in present_candidates)
    trusted_candidates = [
        candidate
        for candidate in present_candidates
        if normalize_trust_level(candidate.trust_level) == best_trust_level
    ]
    if len(trusted_candidates) == 1:
        return build_survivor_selection(trusted_candidates[0], "TRUST_LEVEL")
    present_candidates = trusted_candidates

    candidates_with_import_timestamp = [
        candidate for candidate in present_candidates if candidate.import_started_at is not None
    ]
    if candidates_with_import_timestamp:
        newest_timestamp = max(candidate.import_started_at for candidate in candidates_with_import_timestamp)
        newest_candidates = [
            candidate
            for candidate in candidates_with_import_timestamp
            if candidate.import_started_at == newest_timestamp
        ]
        if len(newest_candidates) == 1:
            return build_survivor_selection(newest_candidates[0], "NEWEST_IMPORT")
        present_candidates = newest_candidates

    return build_survivor_selection(present_candidates[0], "INPUT_ORDER_FALLBACK")


PERSON_DIMENSION_FIELD_ALIASES = {
    "PESEL": ("PESEL_Normalized", "PESEL"),
    "Serial_Number_ID_Card": ("Serial_Number_ID_Card_Normalized", "Serial_Number_ID_Card"),
    "Serial_Number_Passport": ("Serial_Number_Passport_Normalized", "Serial_Number_Passport"),
    "First_Name": ("First_Name_Normalized", "First_Name"),
    "Second_Name": ("Second_Name_Normalized", "Second_Name"),
    "Last_Name": ("Last_Name_Normalized", "Last_Name"),
    "Family_Name": ("Family_Name_Normalized", "Family_Name"),
    "Birth_Date": ("Birth_Date",),
    "Place_Of_Birth": ("Place_Of_Birth_Normalized", "Place_Of_Birth"),
    "Sex": ("Sex",),
    "Citizenship": ("Citizenship_Normalized", "Citizenship"),
    "Phone_Number": ("Phone_Normalized", "Phone_Number"),
    "Email_Address": ("Email_Normalized", "Email_Address"),
}

PARTY_DIMENSION_FIELD_ALIASES = {
    "Name": ("Name_Normalized", "Name"),
    "Short_Name": ("Short_Name_Normalized", "Short_Name"),
    "Legal_Entity_Type": ("Legal_Entity_Type_Normalized", "Legal_Entity_Type"),
    "Registration_Country": (
        "Registration_Country_Normalized",
        "Country_Normalized",
        "Registration_Country",
        "Country",
    ),
    "Establishment_Date": ("Establishment_Date",),
}

ADDRESS_FIELD_ALIASES = {
    "Street": ("Street_Normalized", "Street"),
    "Building_Number": ("Building_Number_Normalized", "Building_Number"),
    "Apartment_Number": ("Apartment_Number_Normalized", "Apartment_Number"),
    "City": ("City_Normalized", "City"),
    "Postal_City": ("Postal_City_Normalized", "Postal_City"),
    "Postal_Code": ("Postal_Code_Normalized", "Postal_Code"),
    "District": ("District_Normalized", "District"),
    "Province": ("Province_Normalized", "Province"),
    "Country": ("Country_Normalized", "Country"),
}


def create_or_update_golden_person(
    db: Any,
    entity_group_id: int,
    repo: Any | None = None,
) -> GoldenDimensionLoadResult:
    repo = repo or create_repository(db)
    records, member_ids = get_group_preprocessed_records(repo, "PERSON", entity_group_id)
    if not records:
        raise ValueError(f"No PERSON preprocessed records for Entity_Group_ID={entity_group_id}.")

    person_values = build_survivor_values(repo, "PERSON", records, PERSON_DIMENSION_FIELD_ALIASES)
    existing = repo.find_person_by_identity(
        pesel=person_values.get("PESEL"),
        serial_number_id_card=person_values.get("Serial_Number_ID_Card"),
        serial_number_passport=person_values.get("Serial_Number_Passport"),
    )
    if existing is None:
        person = repo.create_person(**person_values)
        dimension_action = "CREATED"
    else:
        person = repo.update_person(existing, **person_values)
        dimension_action = "UPDATED"

    address, address_action = create_golden_address_for_records(
        repo=repo,
        entity_type="PERSON",
        records=records,
    )
    address_link_action = "SKIPPED"
    if address is not None:
        address_link_action = ensure_golden_address_link(
            repo=repo,
            entity_type="PERSON",
            dimension_id=get_int_record_value(person, "Person_ID"),
            address_id=get_int_record_value(address, "Address_ID"),
        )
    repo.commit()
    return GoldenDimensionLoadResult(
        entity_type="PERSON",
        entity_group_id=entity_group_id,
        member_preprocessed_ids=member_ids,
        dimension_id=get_record_value(person, "Person_ID"),
        dimension_action=dimension_action,
        address_id=get_record_value(address, "Address_ID") if address is not None else None,
        address_action=address_action,
        address_link_action=address_link_action,
    )


def golden_load_dimensions(
    db: Any,
    entity_type: str,
    raw_file_id: int | None = None,
    entity_group_id: int | None = None,
    repo: Any | None = None,
) -> GoldenLoadRunResult:
    entity_type = normalize_entity_type(entity_type)
    repo = repo or create_repository(db)
    process_log = None
    if raw_file_id is not None and hasattr(repo, "create_golden_load_process_log"):
        import_batch_id = repo.get_import_batch_id_for_raw_file(int(raw_file_id))
        process_log = repo.create_golden_load_process_log(import_batch_id, int(raw_file_id))

    groups_in_scope = 0
    try:
        if raw_file_id is not None and hasattr(repo, "get_entity_groups_for_raw_file"):
            groups = list(repo.get_entity_groups_for_raw_file(entity_type, int(raw_file_id)))
        else:
            groups = list(repo.get_entity_groups(entity_type))
        if entity_group_id is not None:
            groups = [
                group
                for group in groups
                if get_int_record_value(group, "Entity_Group_ID") == int(entity_group_id)
            ]
        groups_in_scope = len(groups)
        if not groups:
            scope = (
                f"Entity_Group_ID={entity_group_id}"
                if entity_group_id is not None
                else (
                    f"entity type {entity_type} and RawFile_ID={raw_file_id}"
                    if raw_file_id is not None
                    else f"entity type {entity_type}"
                )
            )
            raise ValueError(f"No entity groups found for {scope}.")

        results: list[GoldenDimensionLoadResult] = []
        for group in groups:
            current_group_id = get_int_record_value(group, "Entity_Group_ID")
            if entity_type == "PERSON":
                results.append(
                    create_or_update_golden_person(
                        db=db,
                        entity_group_id=current_group_id,
                        repo=repo,
                    )
                )
            else:
                results.append(
                    create_or_update_golden_party(
                        db=db,
                        entity_group_id=current_group_id,
                        repo=repo,
                    )
                )

        if process_log is not None:
            repo.finish_process_log(
                process_log,
                "SUCCESS",
                records_in=groups_in_scope,
                records_out=len(results),
            )
        return GoldenLoadRunResult(
            entity_type=entity_type,
            raw_file_id=raw_file_id,
            entity_group_id=entity_group_id,
            groups_in_scope=groups_in_scope,
            groups_processed=len(results),
            results=tuple(results),
        )
    except Exception as exc:
        if process_log is not None:
            repo.finish_process_log(
                process_log,
                "FAILED",
                records_in=groups_in_scope,
                records_out=0,
                error_message=str(exc),
            )
        raise


def create_or_update_golden_party(
    db: Any,
    entity_group_id: int,
    repo: Any | None = None,
) -> GoldenDimensionLoadResult:
    repo = repo or create_repository(db)
    records, member_ids = get_group_preprocessed_records(repo, "PARTY", entity_group_id)
    if not records:
        raise ValueError(f"No PARTY preprocessed records for Entity_Group_ID={entity_group_id}.")

    party_values = build_survivor_values(repo, "PARTY", records, PARTY_DIMENSION_FIELD_ALIASES)
    existing = repo.find_party_by_identity(
        NIP=select_survivor_scalar(repo, "PARTY", "NIP", records, ("NIP_Normalized", "NIP")),
        REGON=select_survivor_scalar(repo, "PARTY", "REGON", records, ("REGON_Normalized", "REGON")),
        KRS=select_survivor_scalar(repo, "PARTY", "KRS", records, ("KRS_Normalized", "KRS")),
        LEI=select_survivor_scalar(repo, "PARTY", "LEI", records, ("LEI_Normalized", "LEI")),
    )
    if existing is None:
        party = repo.create_party(**party_values)
        dimension_action = "CREATED"
    else:
        party = repo.update_party(existing, **party_values)
        dimension_action = "UPDATED"

    address, address_action = create_golden_address_for_records(
        repo=repo,
        entity_type="PARTY",
        records=records,
    )
    address_link_action = "SKIPPED"
    if address is not None:
        address_link_action = ensure_golden_address_link(
            repo=repo,
            entity_type="PARTY",
            dimension_id=get_int_record_value(party, "Party_ID"),
            address_id=get_int_record_value(address, "Address_ID"),
        )
    party_identities_saved = persist_party_identities(repo, party, records)
    repo.commit()
    return GoldenDimensionLoadResult(
        entity_type="PARTY",
        entity_group_id=entity_group_id,
        member_preprocessed_ids=member_ids,
        dimension_id=get_record_value(party, "Party_ID"),
        dimension_action=dimension_action,
        address_id=get_record_value(address, "Address_ID") if address is not None else None,
        address_action=address_action,
        address_link_action=address_link_action,
        party_identities_saved=party_identities_saved,
    )


def create_golden_address_for_records(
    *,
    repo: Any,
    entity_type: str,
    records: list[Any],
) -> tuple[Any | None, str]:
    address_values = build_survivor_values(repo, entity_type, records, ADDRESS_FIELD_ALIASES)
    if not any(not is_blank(value) for value in address_values.values()):
        return None, "SKIPPED"

    existing = repo.find_address(
        street=address_values.get("Street"),
        building_number=address_values.get("Building_Number"),
        apartment_number=address_values.get("Apartment_Number"),
        city=address_values.get("City"),
        postal_city=address_values.get("Postal_City"),
        postal_code=address_values.get("Postal_Code"),
        district=address_values.get("District"),
        province=address_values.get("Province"),
        country=address_values.get("Country"),
    )
    address = repo.get_or_create_address(
        street=address_values.get("Street"),
        building_number=address_values.get("Building_Number"),
        apartment_number=address_values.get("Apartment_Number"),
        city=address_values.get("City"),
        postal_city=address_values.get("Postal_City"),
        postal_code=address_values.get("Postal_Code"),
        district=address_values.get("District"),
        province=address_values.get("Province"),
        country=address_values.get("Country"),
    )
    return address, "CREATED" if existing is None and address is not None else "REUSED"


def ensure_golden_address_link(
    *,
    repo: Any,
    entity_type: str,
    dimension_id: int,
    address_id: int,
) -> str:
    entity_type = normalize_entity_type(entity_type)
    address_type_name = "RESIDENCE" if entity_type == "PERSON" else "REGISTERED"
    address_type = repo.get_address_type_by_name(address_type_name)
    if address_type is None:
        raise ValueError(f"Address type {address_type_name} not found in gold.DimAddressType.")

    existing_count_before = _count_repo_links(repo, entity_type)

    if entity_type == "PERSON":
        repo.ensure_person_address_link(
            person_id=dimension_id,
            address_id=address_id,
            address_type_id=get_int_record_value(address_type, "AddressType_ID"),
        )
    else:
        repo.ensure_party_address_link(
            party_id=dimension_id,
            address_id=address_id,
            address_type_id=get_int_record_value(address_type, "AddressType_ID"),
        )

    existing_count_after = _count_repo_links(repo, entity_type)
    if existing_count_before is not None and existing_count_after == existing_count_before:
        return "REUSED"
    return "CREATED"


PARTY_IDENTITY_FIELD_MAP = {
    "NIP": ("NIP_Normalized", "NIP"),
    "REGON": ("REGON_Normalized", "REGON"),
    "KRS": ("KRS_Normalized", "KRS"),
    "LEI": ("LEI_Normalized", "LEI"),
    "KNF_REGISTER_NUMBER": ("Register_Number_Normalized", "Register_Number"),
    "DECISION_NUMBER": ("Decision_Number_Normalized", "Decision_Number"),
}


def persist_party_identities(repo: Any, party: Any, records: list[Any]) -> int:
    party_id = get_int_record_value(party, "Party_ID")
    saved = 0
    for identity_type_name, aliases in PARTY_IDENTITY_FIELD_MAP.items():
        identity_value = select_survivor_scalar(repo, "PARTY", identity_type_name, records, aliases)
        if is_blank(identity_value):
            continue
        identity_type = repo.get_identity_type_by_name(identity_type_name)
        if identity_type is None:
            raise ValueError(
                f"Identity type {identity_type_name} not found in gold.DimIdentityType."
            )
        repo.ensure_party_identity(
            party_id=party_id,
            identity_type_id=get_int_record_value(identity_type, "IdentityType_ID"),
            identity_value=stringify_value(identity_value),
            is_valid=None,
            match_confidence=None,
        )
        saved += 1
    return saved


def _count_repo_links(repo: Any, entity_type: str) -> int | None:
    entity_type = normalize_entity_type(entity_type)
    if entity_type == "PERSON" and hasattr(repo, "person_address_links"):
        return len(repo.person_address_links)
    if entity_type == "PARTY" and hasattr(repo, "party_address_links"):
        return len(repo.party_address_links)
    return None


def get_group_preprocessed_records(
    repo: Any,
    entity_type: str,
    entity_group_id: int,
) -> tuple[list[Any], tuple[int, ...]]:
    members = repo.get_entity_group_members(entity_type, entity_group_id)
    member_ids = tuple(
        sorted(get_int_record_value(member, "Preprocessed_ID") for member in members)
    )
    records = list(repo.get_preprocessed_records_by_ids(entity_type, list(member_ids)))
    return records, member_ids


def build_survivor_values(
    repo: Any,
    entity_type: str,
    records: list[Any],
    field_aliases: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    return {
        target_field: select_survivor_scalar(repo, entity_type, target_field, records, aliases)
        for target_field, aliases in field_aliases.items()
    }


def select_survivor_scalar(
    repo: Any,
    entity_type: str,
    field_name: str,
    records: list[Any],
    aliases: tuple[str, ...],
) -> Any:
    candidates = build_survivor_candidates(repo, records, aliases)
    return select_survivor_value(entity_type, field_name, candidates).value


def build_survivor_candidates(
    repo: Any,
    records: list[Any],
    aliases: tuple[str, ...],
) -> list[SurvivorValueCandidate]:
    candidates: list[SurvivorValueCandidate] = []
    for record in records:
        value = get_first_present_alias_value(record, aliases)
        source_system_code = None
        trust_level = None
        import_started_at = None
        if hasattr(repo, "get_source_metadata_for_import_batch"):
            (
                source_system_code,
                trust_level,
                import_started_at,
            ) = repo.get_source_metadata_for_import_batch(get_int_record_value(record, "ImportBatch_ID"))
        candidates.append(
            SurvivorValueCandidate(
                value=value,
                source_system_code=source_system_code,
                trust_level=trust_level,
                import_started_at=import_started_at,
            )
        )
    return candidates


def get_first_present_alias_value(record: Any, aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        value = get_record_value(record, alias)
        if not is_blank(value):
            return value
    return None


def find_match_candidates(
    db: Any,
    entity_type: str,
    raw_file_id: int | None = None,
    min_score: float = LEVENSHTEIN_CANDIDATE_THRESHOLD,
    max_pairs: int = DEFAULT_MATCHING_MAX_PAIRS,
    repo: Any | None = None,
) -> MatchingRunResult:
    entity_type = normalize_entity_type(entity_type)
    repo = repo or create_repository(db)
    scoped_records = repo.get_preprocessed_records(entity_type, raw_file_id=raw_file_id)
    if not scoped_records:
        scope = f"RawFile_ID={raw_file_id}" if raw_file_id is not None else "all raw files"
        raise PreprocessedRecordsNotFoundError(
            f"No {entity_type} preprocessed records for {scope}."
        )

    if not hasattr(repo, "get_candidate_records_for_match"):
        candidate_pool = repo.get_preprocessed_records(entity_type, raw_file_id=None)
        records_compared_against = len(candidate_pool)
    else:
        candidate_pool = []
        records_compared_against = get_records_compared_against(repo, entity_type)

    if records_compared_against == 0:
        raise PreprocessedRecordsNotFoundError(f"No {entity_type} preprocessed records.")

    pairs_evaluated = 0
    candidates: list[MatchCandidate] = []
    seen_pairs: set[tuple[int, int]] = set()

    for left_record in scoped_records:
        left_id = get_record_identity(left_record)
        candidate_records = get_candidate_records(repo, entity_type, left_record, candidate_pool)
        for right_record in candidate_records:
            right_id = get_record_identity(right_record)
            if left_id == right_id:
                continue

            pair_key = tuple(sorted((left_id, right_id)))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            pair_left_record = left_record
            pair_right_record = right_record
            pair_left_id = left_id
            pair_right_id = right_id
            if left_id > right_id:
                pair_left_record, pair_right_record = right_record, left_record
                pair_left_id, pair_right_id = pair_key

            pairs_evaluated += 1
            if max_pairs > 0 and pairs_evaluated > max_pairs:
                raise MatchingPairLimitExceededError(
                    f"Pair limit exceeded ({max_pairs}). Raise matching_max_pairs or use 0 to disable the safety limit."
                )

            match_result = score_match(pair_left_record, pair_right_record, entity_type)
            if match_result.score < min_score:
                continue
            if match_result.decision == MatchDecision.NO_MATCH:
                continue

            candidates.append(
                MatchCandidate(
                    left_preprocessed_id=pair_left_id,
                    right_preprocessed_id=pair_right_id,
                    left_staging_id=get_int_record_value(pair_left_record, "Staging_ID"),
                    right_staging_id=get_int_record_value(pair_right_record, "Staging_ID"),
                    left_raw_file_id=get_int_record_value(pair_left_record, "RawFile_ID"),
                    right_raw_file_id=get_int_record_value(pair_right_record, "RawFile_ID"),
                    left_source_record_id=get_optional_string_value(pair_left_record, "Source_Record_ID"),
                    right_source_record_id=get_optional_string_value(pair_right_record, "Source_Record_ID"),
                    score=match_result.score,
                    decision=match_result.decision,
                    strong_match_fields=match_result.strong_match_fields,
                    conflict_fields=match_result.conflict_fields,
                )
            )

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    persisted_candidates = persist_match_candidates(
        repo,
        entity_type,
        raw_file_id,
        candidates,
    )
    return MatchingRunResult(
        entity_type=entity_type,
        raw_file_id=raw_file_id,
        records_in_scope=len(scoped_records),
        records_compared_against=records_compared_against,
        pairs_evaluated=pairs_evaluated,
        candidates_out=persisted_candidates,
        min_score=min_score,
        candidates=tuple(candidates),
    )


def refine_match_candidates_with_jaro_winkler(
    db: Any,
    entity_type: str,
    raw_file_id: int | None = None,
    min_score: float = JARO_WINKLER_CANDIDATE_THRESHOLD,
    repo: Any | None = None,
) -> JaroWinklerRunResult:
    entity_type = normalize_entity_type(entity_type)
    repo = repo or create_repository(db)
    if not hasattr(repo, "get_levenshtein_candidates"):
        raise LevenshteinCandidatesNotFoundError("Repository does not expose Levenshtein candidates.")

    levenshtein_candidates = list(repo.get_levenshtein_candidates(entity_type, raw_file_id))
    if not levenshtein_candidates:
        persisted_candidates = persist_jaro_winkler_candidates(repo, entity_type, raw_file_id, [])
        return JaroWinklerRunResult(
            entity_type=entity_type,
            raw_file_id=raw_file_id,
            candidates_in_scope=0,
            candidates_out=persisted_candidates,
            min_score=min_score,
            candidates=(),
        )

    refined_candidates: list[JaroWinklerCandidate] = []
    for candidate_record in levenshtein_candidates:
        left_record = repo.get_preprocessed_record_by_id(
            entity_type,
            get_int_record_value(candidate_record, "Left_Preprocessed_ID"),
        )
        right_record = repo.get_preprocessed_record_by_id(
            entity_type,
            get_int_record_value(candidate_record, "Right_Preprocessed_ID"),
        )
        if left_record is None or right_record is None:
            continue

        score_result = score_jaro_winkler_match(
            left_record,
            right_record,
            entity_type,
            original_strong_fields=parse_candidate_json_field(candidate_record, "Strong_Match_Fields_JSON"),
            original_conflict_fields=parse_candidate_json_field(candidate_record, "Conflict_Fields_JSON"),
            levenshtein_decision=get_optional_string_value(candidate_record, "Decision"),
        )
        if score_result.decision == MatchDecision.NO_MATCH:
            continue
        if score_result.score < min_score and not score_result.strong_match_fields:
            continue

        refined_candidates.append(
            JaroWinklerCandidate(
                levenshtein_candidate_id=get_int_record_value(
                    candidate_record,
                    "Match_Candidate_Levenshtein_ID",
                ),
                left_preprocessed_id=get_int_record_value(candidate_record, "Left_Preprocessed_ID"),
                right_preprocessed_id=get_int_record_value(candidate_record, "Right_Preprocessed_ID"),
                left_staging_id=get_int_record_value(candidate_record, "Left_Staging_ID"),
                right_staging_id=get_int_record_value(candidate_record, "Right_Staging_ID"),
                left_raw_file_id=get_int_record_value(candidate_record, "Left_RawFile_ID"),
                right_raw_file_id=get_int_record_value(candidate_record, "Right_RawFile_ID"),
                left_source_record_id=get_optional_string_value(candidate_record, "Left_Source_Record_ID"),
                right_source_record_id=get_optional_string_value(candidate_record, "Right_Source_Record_ID"),
                levenshtein_score=float(get_record_value(candidate_record, "Score")),
                jaro_winkler_score=score_result.score,
                decision=score_result.decision,
                strong_match_fields=score_result.strong_match_fields,
                conflict_fields=score_result.conflict_fields,
                text_match_fields=tuple(
                    field_score.field
                    for field_score in score_result.field_scores
                    if field_score.similarity is not None
                ),
            )
        )

    refined_candidates.sort(key=lambda candidate: candidate.jaro_winkler_score, reverse=True)
    persisted_candidates = persist_jaro_winkler_candidates(
        repo,
        entity_type,
        raw_file_id,
        refined_candidates,
    )
    return JaroWinklerRunResult(
        entity_type=entity_type,
        raw_file_id=raw_file_id,
        candidates_in_scope=len(levenshtein_candidates),
        candidates_out=persisted_candidates,
        min_score=min_score,
        candidates=tuple(refined_candidates),
    )


def get_records_compared_against(repo: Any, entity_type: str) -> int:
    if hasattr(repo, "count_preprocessed_records"):
        return int(repo.count_preprocessed_records(entity_type))
    return len(repo.get_preprocessed_records(entity_type, raw_file_id=None))


def get_candidate_records(
    repo: Any,
    entity_type: str,
    left_record: Any,
    fallback_candidate_pool: list[Any],
) -> list[Any]:
    if hasattr(repo, "get_candidate_records_for_match"):
        return list(repo.get_candidate_records_for_match(entity_type, left_record))
    return fallback_candidate_pool


def persist_match_candidates(
    repo: Any,
    entity_type: str,
    raw_file_id: int | None,
    candidates: list[MatchCandidate],
) -> int:
    if hasattr(repo, "replace_match_candidates"):
        return int(repo.replace_match_candidates(entity_type, raw_file_id, candidates))
    return len(candidates)


def persist_jaro_winkler_candidates(
    repo: Any,
    entity_type: str,
    raw_file_id: int | None,
    candidates: list[JaroWinklerCandidate],
) -> int:
    if hasattr(repo, "replace_jaro_winkler_candidates"):
        return int(repo.replace_jaro_winkler_candidates(entity_type, raw_file_id, candidates))
    return len(candidates)


def group_auto_merge_candidates(
    db: Any,
    entity_type: str,
    repo: Any | None = None,
) -> EntityGroupingRunResult:
    entity_type = normalize_entity_type(entity_type)
    repo = repo or create_repository(db)
    if not hasattr(repo, "get_jaro_winkler_candidates"):
        raise ValueError("Repository does not expose Jaro-Winkler candidates.")

    candidates = [
        candidate
        for candidate in repo.get_jaro_winkler_candidates(entity_type)
        if get_optional_string_value(candidate, "Decision") == MatchDecision.AUTO_MERGE.value
    ]
    groups = build_entity_groups(candidates)
    groups_out, members_out = persist_entity_groups(repo, entity_type, groups)
    return EntityGroupingRunResult(
        entity_type=entity_type,
        auto_merge_pairs_in_scope=len(candidates),
        groups_out=groups_out,
        members_out=members_out,
        groups=tuple(groups),
    )


def build_entity_groups(candidates: list[Any]) -> list[EntityGroup]:
    parents: dict[int, int] = {}

    def find(member_id: int) -> int:
        parents.setdefault(member_id, member_id)
        if parents[member_id] != member_id:
            parents[member_id] = find(parents[member_id])
        return parents[member_id]

    def union(left_id: int, right_id: int) -> None:
        left_root = find(left_id)
        right_root = find(right_id)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    seen_pairs: set[tuple[int, int]] = set()
    for candidate in candidates:
        left_id = get_int_record_value(candidate, "Left_Preprocessed_ID")
        right_id = get_int_record_value(candidate, "Right_Preprocessed_ID")
        if left_id == right_id:
            continue
        pair_key = tuple(sorted((left_id, right_id)))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        union(*pair_key)

    members_by_root: dict[int, list[int]] = {}
    for member_id in parents:
        members_by_root.setdefault(find(member_id), []).append(member_id)

    groups = []
    for member_ids in members_by_root.values():
        sorted_member_ids = tuple(sorted(member_ids))
        groups.append(
            EntityGroup(
                group_key=build_group_key(sorted_member_ids),
                member_preprocessed_ids=sorted_member_ids,
            )
        )
    return sorted(groups, key=lambda group: group.member_preprocessed_ids)


def build_group_key(member_preprocessed_ids: tuple[int, ...]) -> str:
    serialized_ids = ",".join(str(member_id) for member_id in member_preprocessed_ids)
    return hashlib.sha256(serialized_ids.encode("ascii")).hexdigest()


def persist_entity_groups(
    repo: Any,
    entity_type: str,
    groups: list[EntityGroup],
) -> tuple[int, int]:
    if hasattr(repo, "replace_entity_groups"):
        groups_out, members_out = repo.replace_entity_groups(entity_type, groups)
        return int(groups_out), int(members_out)
    return len(groups), sum(len(group.member_preprocessed_ids) for group in groups)


def score_match(left_record: Any, right_record: Any, entity_type: str) -> MatchResult:
    entity_type = normalize_entity_type(entity_type)
    rules = FIELD_RULES_BY_ENTITY_TYPE[entity_type]
    field_scores: list[FieldScore] = []
    strong_match_fields: list[str] = []
    conflict_fields: list[str] = []
    blocking_conflict_fields: list[str] = []
    weighted_score = 0.0
    total_weight = 0.0

    for rule in rules:
        left_value = get_first_present_value(left_record, rule)
        right_value = get_first_present_value(right_record, rule)
        if is_blank(left_value) or is_blank(right_value):
            continue

        similarity = COMPARATORS[rule.comparator](left_value, right_value)
        contribution = similarity * rule.weight
        total_weight += rule.weight
        weighted_score += contribution

        if rule.decisive and similarity == 1.0:
            strong_match_fields.append(rule.name)
        elif rule.role == FieldRole.STRONG and similarity < 1.0:
            conflict_fields.append(rule.name)
            blocking_conflict_fields.append(rule.name)
        elif is_stable_conflict(rule, similarity):
            conflict_fields.append(rule.name)
            if rule.role in {FieldRole.FIXED, FieldRole.SEMI_FIXED}:
                blocking_conflict_fields.append(rule.name)

        field_scores.append(
            FieldScore(
                field=rule.name,
                role=rule.role,
                left_value=stringify_value(left_value),
                right_value=stringify_value(right_value),
                similarity=round(similarity, 4),
                weight=rule.weight,
                contribution=round(contribution, 4),
                matched=similarity == 1.0,
            )
        )

    rounded_score = round(weighted_score / total_weight if total_weight else 0.0, 4)
    return MatchResult(
        entity_type=entity_type,
        score=rounded_score,
        decision=classify_match(
            rounded_score,
            strong_match_fields,
            conflict_fields,
            blocking_conflict_fields,
        ),
        strong_match_fields=tuple(strong_match_fields),
        conflict_fields=tuple(conflict_fields),
        field_scores=tuple(field_scores),
    )


def score_jaro_winkler_match(
    left_record: Any,
    right_record: Any,
    entity_type: str,
    original_strong_fields: tuple[str, ...] = (),
    original_conflict_fields: tuple[str, ...] = (),
    levenshtein_decision: str | None = None,
) -> MatchResult:
    entity_type = normalize_entity_type(entity_type)
    rules = JARO_WINKLER_RULES_BY_ENTITY_TYPE[entity_type]
    field_scores: list[FieldScore] = []
    conflict_fields = list(original_conflict_fields)
    weighted_score = 0.0
    total_weight = 0.0

    for rule in rules:
        left_value = get_first_present_value(left_record, rule)
        right_value = get_first_present_value(right_record, rule)
        if is_blank(left_value) or is_blank(right_value):
            continue

        similarity = COMPARATORS["jaro_winkler"](left_value, right_value)
        contribution = similarity * rule.weight
        total_weight += rule.weight
        weighted_score += contribution

        if rule.role in {FieldRole.FIXED, FieldRole.SEMI_FIXED} and similarity < 0.82:
            conflict_fields.append(rule.name)

        field_scores.append(
            FieldScore(
                field=rule.name,
                role=rule.role,
                left_value=stringify_value(left_value),
                right_value=stringify_value(right_value),
                similarity=round(similarity, 4),
                weight=rule.weight,
                contribution=round(contribution, 4),
                matched=similarity == 1.0,
            )
        )

    rounded_score = round(weighted_score / total_weight if total_weight else 0.0, 4)
    decision = classify_jaro_winkler_match(
        rounded_score,
        original_strong_fields,
        conflict_fields,
        levenshtein_decision,
    )
    return MatchResult(
        entity_type=entity_type,
        score=rounded_score,
        decision=decision,
        strong_match_fields=tuple(original_strong_fields),
        conflict_fields=tuple(dict.fromkeys(conflict_fields)),
        field_scores=tuple(field_scores),
    )


def classify_match(
    score: float,
    strong_match_fields: list[str],
    conflict_fields: list[str],
    blocking_conflict_fields: list[str] | None = None,
) -> MatchDecision:
    blocking_conflict_fields = blocking_conflict_fields or []
    CRITICAL_IDENTIFIERS = {"pesel", "nip", "regon", "krs", "id_card", "passport"}
    has_critical_id_conflict = any(
        field.lower() in CRITICAL_IDENTIFIERS for field in blocking_conflict_fields
    )
    if (
        not strong_match_fields
        and len(set(blocking_conflict_fields)) >= BLOCKING_CONFLICT_FIELD_COUNT
    ):
        return MatchDecision.NO_MATCH
    if score >= FUZZY_AUTO_MERGE_THRESHOLD and not has_critical_id_conflict:
        return MatchDecision.AUTO_MERGE
    if strong_match_fields and not conflict_fields:
        return MatchDecision.AUTO_MERGE
    if score >= AUTO_MERGE_THRESHOLD and not conflict_fields:
        return MatchDecision.AUTO_MERGE
    if score >= REVIEW_THRESHOLD:
        return MatchDecision.REVIEW
    if score >= LEVENSHTEIN_CANDIDATE_THRESHOLD:
        return MatchDecision.CANDIDATE
    return MatchDecision.NO_MATCH


def classify_jaro_winkler_match(
    score: float,
    strong_match_fields: tuple[str, ...],
    conflict_fields: list[str],
    levenshtein_decision: str | None,
) -> MatchDecision:
    if score >= JARO_WINKLER_AUTO_MERGE_THRESHOLD and not conflict_fields:
        return MatchDecision.AUTO_MERGE
    if strong_match_fields and not conflict_fields and score >= JARO_WINKLER_REVIEW_THRESHOLD:
        return MatchDecision.AUTO_MERGE
    if score >= JARO_WINKLER_REVIEW_THRESHOLD:
        return MatchDecision.REVIEW
    if score >= JARO_WINKLER_CANDIDATE_THRESHOLD:
        return MatchDecision.CANDIDATE
    if levenshtein_decision == MatchDecision.AUTO_MERGE.value and strong_match_fields:
        return MatchDecision.REVIEW
    return MatchDecision.NO_MATCH


def is_stable_conflict(rule: FieldRule, similarity: float) -> bool:
    if rule.role == FieldRole.FIXED:
        return similarity < 1.0
    if rule.role == FieldRole.SEMI_FIXED:
        return similarity < STABLE_CONFLICT_SIMILARITY_THRESHOLD
    return False


def choose_trusted_value(candidates: list[tuple[str | None, Any]]) -> Any:
    present_candidates = [
        (source_system_code, value)
        for source_system_code, value in candidates
        if not is_blank(value)
    ]
    if not present_candidates:
        return None

    return max(
        present_candidates,
        key=lambda item: normalize_trust_level(
            FALLBACK_SOURCE_TRUST_LEVELS.get(str(item[0]).upper(), 0)
        ),
    )[1]


def normalize_survivor_candidate(candidate: SurvivorValueCandidate | dict[str, Any] | Any) -> SurvivorValueCandidate:
    if isinstance(candidate, SurvivorValueCandidate):
        return candidate
    if isinstance(candidate, dict):
        return SurvivorValueCandidate(
            value=candidate.get("value"),
            source_system_code=candidate.get("source_system_code"),
            trust_level=candidate.get("trust_level"),
            validation_status=candidate.get("validation_status"),
            import_started_at=candidate.get("import_started_at"),
            teryt_confirmed=candidate.get("teryt_confirmed"),
        )
    return SurvivorValueCandidate(
        value=getattr(candidate, "value", None),
        source_system_code=getattr(candidate, "source_system_code", None),
        trust_level=getattr(candidate, "trust_level", None),
        validation_status=getattr(candidate, "validation_status", None),
        import_started_at=getattr(candidate, "import_started_at", None),
        teryt_confirmed=getattr(candidate, "teryt_confirmed", None),
    )


def build_survivor_selection(
    candidate: SurvivorValueCandidate,
    selected_by_rule: str,
) -> SurvivorValueSelection:
    return SurvivorValueSelection(
        value=candidate.value,
        source_system_code=candidate.source_system_code,
        selected_by_rule=selected_by_rule,
        trust_level=candidate.trust_level,
        validation_status=candidate.validation_status,
        import_started_at=candidate.import_started_at,
        teryt_confirmed=candidate.teryt_confirmed,
    )


def is_successful_validation(validation_status: str | bool | None) -> bool:
    if isinstance(validation_status, bool):
        return validation_status
    if validation_status is None:
        return False
    return str(validation_status).strip().upper() == "PASS"


def is_address_field(field_name: str) -> bool:
    return field_name in {
        "Street",
        "Building_Number",
        "Apartment_Number",
        "City",
        "Postal_City",
        "Postal_Code",
        "District",
        "Province",
        "Country",
        "Full_Address",
    }


def get_first_present_value(record: Any, rule: FieldRule) -> Any:
    for field_name in (*rule.aliases, rule.name):
        value = get_record_value(record, field_name)
        if not is_blank(value):
            return value
    return None


def get_record_value(record: Any, field_name: str) -> Any:
    if isinstance(record, dict):
        return record.get(field_name)
    return getattr(record, field_name, None)


def normalize_value(value: Any) -> str:
    return stringify_value(value).casefold()


def stringify_value(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def is_blank(value: Any) -> bool:
    return stringify_value(value) == ""


def normalize_trust_level(value: int | float | None) -> float:
    if value is None:
        return 0.0
    return float(value) / 100 if value > 1 else float(value)


def get_record_identity(record: Any) -> int:
    return get_int_record_value(record, "Preprocessed_ID")


def get_int_record_value(record: Any, field_name: str) -> int:
    value = get_record_value(record, field_name)
    if value is None:
        raise ValueError(f"Record has no {field_name}.")
    return int(value)


def get_optional_string_value(record: Any, field_name: str) -> str | None:
    value = get_record_value(record, field_name)
    return None if is_blank(value) else stringify_value(value)


def parse_candidate_json_field(record: Any, field_name: str) -> tuple[str, ...]:
    import json

    value = get_record_value(record, field_name)
    if is_blank(value):
        return ()
    parsed = json.loads(str(value))
    if not isinstance(parsed, list):
        return ()
    return tuple(str(item) for item in parsed)
