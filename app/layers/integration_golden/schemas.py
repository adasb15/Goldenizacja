from pydantic import BaseModel


class LayerStatus(BaseModel):
    layer: str
    status: str


class MatchCandidateResponse(BaseModel):
    left_preprocessed_id: int
    right_preprocessed_id: int
    left_staging_id: int
    right_staging_id: int
    left_raw_file_id: int
    right_raw_file_id: int
    left_source_record_id: str | None
    right_source_record_id: str | None
    score: float
    decision: str
    strong_match_fields: list[str]
    conflict_fields: list[str]


class MatchingRunResponse(BaseModel):
    entity_type: str
    raw_file_id: int | None
    records_in_scope: int
    records_compared_against: int
    pairs_evaluated: int
    candidates_out: int
    min_score: float
    candidates: list[MatchCandidateResponse]


class JaroWinklerCandidateResponse(BaseModel):
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
    decision: str
    strong_match_fields: list[str]
    conflict_fields: list[str]
    text_match_fields: list[str]


class JaroWinklerRunResponse(BaseModel):
    entity_type: str
    raw_file_id: int | None
    candidates_in_scope: int
    candidates_out: int
    min_score: float
    candidates: list[JaroWinklerCandidateResponse]


class EntityGroupResponse(BaseModel):
    group_key: str
    member_preprocessed_ids: list[int]


class EntityGroupingRunResponse(BaseModel):
    entity_type: str
    auto_merge_pairs_in_scope: int
    groups_out: int
    members_out: int
    groups: list[EntityGroupResponse]


class GoldenDimensionLoadResponse(BaseModel):
    entity_type: str
    entity_group_id: int
    member_preprocessed_ids: list[int]
    dimension_id: int | None
    dimension_action: str
    address_id: int | None
    address_action: str
    address_link_action: str
    party_identities_saved: int


class GoldenLoadRunResponse(BaseModel):
    entity_type: str
    entity_group_id: int | None
    groups_in_scope: int
    groups_processed: int
    results: list[GoldenDimensionLoadResponse]
