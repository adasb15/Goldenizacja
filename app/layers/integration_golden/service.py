"""Matching i scoring dla warstwy integration_golden."""

from __future__ import annotations

import hashlib
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
