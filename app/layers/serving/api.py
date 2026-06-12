from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.sql import get_db
from app.layers.serving.schemas import (
    ChangeHistoryResponse,
    GoldenRecordListResponse,
    LayerStatus,
    LineageResponse,
    MatchCandidateListResponse,
    MatchComparisonDetailResponse,
    PartyDetailResponse,
    PersonDetailResponse,
    StageCountResponse,
    ValidationResultListResponse,
)
from app.layers.serving.service import (
    GoldenRecordNotFoundError,
    get_change_history,
    get_lineage,
    get_match_comparison,
    get_party_detail,
    get_person_detail,
    get_stage_counts,
    list_golden_records,
    list_jaro_winkler_candidates,
    list_levenshtein_candidates,
    list_validation_results,
    search_parties,
    search_person_by_pesel,
)

router = APIRouter(prefix="/serving", tags=["serving"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="serving", status="ready")


@router.get("/golden-records", response_model=GoldenRecordListResponse)
def golden_records(
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> GoldenRecordListResponse:
    try:
        return list_golden_records(db, entity_type=entity_type, limit=limit, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/persons/{person_id}", response_model=PersonDetailResponse)
def person_detail(person_id: int, db: Session = Depends(get_db)) -> PersonDetailResponse:
    try:
        return get_person_detail(db, person_id=person_id)
    except GoldenRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/persons/search/by-pesel", response_model=PersonDetailResponse)
def person_search_by_pesel(
    pesel: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> PersonDetailResponse:
    try:
        return search_person_by_pesel(db, pesel=pesel)
    except GoldenRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/parties/search", response_model=GoldenRecordListResponse)
def party_search(
    nip: str | None = Query(default=None),
    regon: str | None = Query(default=None),
    krs: str | None = Query(default=None),
    lei: str | None = Query(default=None),
    name: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> GoldenRecordListResponse:
    return search_parties(
        db,
        nip=nip,
        regon=regon,
        krs=krs,
        lei=lei,
        name=name,
        limit=limit,
        offset=offset,
    )


@router.get("/parties/{party_id}", response_model=PartyDetailResponse)
def party_detail(party_id: int, db: Session = Depends(get_db)) -> PartyDetailResponse:
    try:
        return get_party_detail(db, party_id=party_id)
    except GoldenRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/lineage/{entity_type}/{record_id}", response_model=LineageResponse)
def lineage(
    entity_type: str,
    record_id: int,
    db: Session = Depends(get_db),
) -> LineageResponse:
    try:
        return get_lineage(db, entity_type=entity_type, record_id=record_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/history/{entity_type}/{record_id}", response_model=ChangeHistoryResponse)
def history(
    entity_type: str,
    record_id: int,
    db: Session = Depends(get_db),
) -> ChangeHistoryResponse:
    try:
        return get_change_history(db, entity_type=entity_type, record_id=record_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/validation-results", response_model=ValidationResultListResponse)
def validation_results(
    entity_type: str | None = Query(default=None),
    source_system_code: str | None = Query(default=None),
    rule_code: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ValidationResultListResponse:
    try:
        return list_validation_results(
            db,
            entity_type=entity_type,
            source_system_code=source_system_code,
            rule_code=rule_code,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/match-results/levenshtein", response_model=MatchCandidateListResponse)
def levenshtein_results(
    entity_type: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> MatchCandidateListResponse:
    try:
        return list_levenshtein_candidates(
            db,
            entity_type=entity_type,
            decision=decision,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/match-results/jaro-winkler", response_model=MatchCandidateListResponse)
def jaro_winkler_results(
    entity_type: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> MatchCandidateListResponse:
    try:
        return list_jaro_winkler_candidates(
            db,
            entity_type=entity_type,
            decision=decision,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/match-results/comparison", response_model=MatchComparisonDetailResponse)
def match_comparison(
    entity_type: str = Query(...),
    left_preprocessed_id: int = Query(...),
    right_preprocessed_id: int = Query(...),
    db: Session = Depends(get_db),
) -> MatchComparisonDetailResponse:
    try:
        return get_match_comparison(
            db,
            entity_type=entity_type,
            left_preprocessed_id=left_preprocessed_id,
            right_preprocessed_id=right_preprocessed_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/counts", response_model=StageCountResponse)
def counts(db: Session = Depends(get_db)) -> StageCountResponse:
    return get_stage_counts(db)
