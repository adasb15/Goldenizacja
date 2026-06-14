from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class LayerStatus(BaseModel):
    layer: str
    status: str


class PageMeta(BaseModel):
    limit: int
    offset: int
    total: int


class AddressResponse(BaseModel):
    address_id: int
    address_type: str | None = None
    street: str | None = None
    building_number: str | None = None
    apartment_number: str | None = None
    city: str | None = None
    postal_city: str | None = None
    postal_code: str | None = None
    district: str | None = None
    province: str | None = None
    country: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class PartyIdentityResponse(BaseModel):
    party_identity_id: int
    identity_type: str
    identity_value: str
    is_valid: bool | None = None
    match_confidence: float | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class GoldenRecordSummary(BaseModel):
    entity_type: str
    record_id: int
    display_name: str | None = None
    primary_identifier: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GoldenRecordListResponse(BaseModel):
    items: list[GoldenRecordSummary]
    page: PageMeta


class PersonDetailResponse(BaseModel):
    person_id: int
    pesel: str | None = None
    serial_number_id_card: str | None = None
    serial_number_passport: str | None = None
    first_name: str | None = None
    second_name: str | None = None
    last_name: str | None = None
    family_name: str | None = None
    birth_date: date | None = None
    place_of_birth: str | None = None
    sex: bool | None = None
    citizenship: str | None = None
    phone_number: str | None = None
    email_address: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    addresses: list[AddressResponse] = Field(default_factory=list)


class PartyDetailResponse(BaseModel):
    party_id: int
    name: str
    short_name: str | None = None
    legal_entity_type: str | None = None
    registration_country: str | None = None
    establishment_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    identities: list[PartyIdentityResponse] = Field(default_factory=list)
    addresses: list[AddressResponse] = Field(default_factory=list)


class LineageEntry(BaseModel):
    lineage_type: str
    lineage_id: int
    attribute_name: str | None = None
    source_system_id: int
    source_system_code: str | None = None
    source_record_id: str | None = None
    import_batch_id: int
    selection_rule: str | None = None
    trust_score: float | None = None
    quality_score: float | None = None
    validation_status: str | None = None
    recorded_at: datetime | None = None


class LineageResponse(BaseModel):
    entity_type: str
    record_id: int
    items: list[LineageEntry]


class ChangeHistoryEntry(BaseModel):
    change_id: int
    entity_type: str
    attribute_name: str
    old_value: str | None = None
    new_value: str | None = None
    import_batch_id: int | None = None
    change_date: datetime | None = None


class ChangeHistoryResponse(BaseModel):
    entity_type: str
    record_id: int
    items: list[ChangeHistoryEntry]


class ValidationResultResponse(BaseModel):
    validation_id: int
    import_batch_id: int
    raw_file_id: int
    source_system_code: str | None = None
    entity_type: str
    staging_id: int
    preprocessed_id: int | None = None
    validation_level: str
    rule_code: str
    field_name: str
    severity: str
    status: str
    message: str
    checked_value: str | None = None
    created_at: datetime | None = None


class ValidationResultListResponse(BaseModel):
    items: list[ValidationResultResponse]
    page: PageMeta


class MatchCandidateListItem(BaseModel):
    candidate_id: int
    entity_type: str
    raw_file_id: int | None = None
    left_preprocessed_id: int
    right_preprocessed_id: int
    left_staging_id: int
    right_staging_id: int
    left_raw_file_id: int
    right_raw_file_id: int
    left_source_record_id: str | None = None
    right_source_record_id: str | None = None
    levenshtein_score: float | None = None
    jaro_winkler_score: float | None = None
    decision: str
    strong_match_fields: list[str]
    conflict_fields: list[str]
    text_match_fields: list[str] = Field(default_factory=list)
    passed_to_second_stage: bool = False
    created_at: datetime | None = None


class MatchCandidateListResponse(BaseModel):
    items: list[MatchCandidateListItem]
    page: PageMeta


class MatchComparisonDetailResponse(BaseModel):
    entity_type: str
    left_preprocessed_id: int
    right_preprocessed_id: int
    levenshtein: MatchCandidateListItem | None = None
    jaro_winkler: MatchCandidateListItem | None = None
    left_record: dict[str, Any] | None = None
    right_record: dict[str, Any] | None = None


class StageCountResponse(BaseModel):
    raw_files: int
    person_staging: int
    party_staging: int
    person_preprocessed: int
    party_preprocessed: int
    validation_results: int
    levenshtein_candidates: int
    jaro_winkler_candidates: int
    entity_groups: int
    golden_persons: int
    golden_parties: int
