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
