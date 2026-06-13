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


@router.get(
    "/status",
    response_model=LayerStatus,
    summary="Layer Status",
    description="Zwraca prosty status warstwy serving.",
)
def status() -> LayerStatus:
    return LayerStatus(layer="serving", status="ready")


@router.get(
    "/golden-records",
    response_model=GoldenRecordListResponse,
    summary="Golden Records",
    description=(
        "Zwraca listÄ™ golden recordĂłw z paginacjÄ…. "
        "Pole `record_id` z odpowiedzi jest pĂłĹşniej uĹĽywane jako `person_id` albo `party_id` "
        "w endpointach szczegĂłĹ‚Ăłw, lineage i historii."
    ),
)
def golden_records(
    entity_type: str | None = Query(default=None, description="Opcjonalnie: PERSON albo PARTY."),
    limit: int = Query(default=50, ge=1, le=200, description="Rozmiar strony wynikĂłw."),
    offset: int = Query(default=0, ge=0, description="PrzesuniÄ™cie paginacji."),
    db: Session = Depends(get_db),
) -> GoldenRecordListResponse:
    try:
        return list_golden_records(db, entity_type=entity_type, limit=limit, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/persons/{person_id}",
    response_model=PersonDetailResponse,
    summary="Person Detail",
    description=(
        "Zwraca szczegĂłĹ‚y golden rekordu osoby. "
        "Tutaj podajesz `Person_ID`, czyli `record_id` z listy `/golden-records` dla `entity_type=PERSON`."
    ),
)
def person_detail(person_id: int, db: Session = Depends(get_db)) -> PersonDetailResponse:
    try:
        return get_person_detail(db, person_id=person_id)
    except GoldenRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/persons/search/by-pesel",
    response_model=PersonDetailResponse,
    summary="Search Person by PESEL",
    description="Wyszukuje golden rekord osoby po numerze PESEL i zwraca jego szczegĂłĹ‚y.",
)
def person_search_by_pesel(
    pesel: str = Query(..., min_length=1, description="PESEL osoby."),
    db: Session = Depends(get_db),
) -> PersonDetailResponse:
    try:
        return search_person_by_pesel(db, pesel=pesel)
    except GoldenRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/parties/search",
    response_model=GoldenRecordListResponse,
    summary="Search Party",
    description=(
        "Wyszukuje golden rekordy podmiotĂłw po NIP, REGON, KRS, LEI albo nazwie. "
        "Pole `record_id` z odpowiedzi jest pĂłĹşniej uĹĽywane jako `party_id`."
    ),
)
def party_search(
    nip: str | None = Query(default=None, description="NIP podmiotu."),
    regon: str | None = Query(default=None, description="REGON podmiotu."),
    krs: str | None = Query(default=None, description="KRS podmiotu."),
    lei: str | None = Query(default=None, description="LEI podmiotu."),
    name: str | None = Query(default=None, description="Nazwa podmiotu."),
    limit: int = Query(default=50, ge=1, le=200, description="Rozmiar strony wynikĂłw."),
    offset: int = Query(default=0, ge=0, description="PrzesuniÄ™cie paginacji."),
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


@router.get(
    "/parties/{party_id}",
    response_model=PartyDetailResponse,
    summary="Party Detail",
    description=(
        "Zwraca szczegĂłĹ‚y golden rekordu podmiotu. "
        "Tutaj podajesz `Party_ID`, czyli `record_id` z listy `/golden-records` dla `entity_type=PARTY`."
    ),
)
def party_detail(party_id: int, db: Session = Depends(get_db)) -> PartyDetailResponse:
    try:
        return get_party_detail(db, party_id=party_id)
    except GoldenRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/lineage/{entity_type}/{record_id}",
    response_model=LineageResponse,
    summary="Record Lineage",
    description=(
        "Zwraca lineage golden rekordu. "
        "Parametr `record_id` to golden `Person_ID` albo `Party_ID`, nie `preprocessed_id`."
    ),
)
def lineage(
    entity_type: str,
    record_id: int,
    db: Session = Depends(get_db),
) -> LineageResponse:
    try:
        return get_lineage(db, entity_type=entity_type, record_id=record_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/history/{entity_type}/{record_id}",
    response_model=ChangeHistoryResponse,
    summary="Change History",
    description=(
        "Zwraca historiÄ™ zmian atrybutĂłw golden rekordu. "
        "Parametr `record_id` to golden `Person_ID` albo `Party_ID`, nie `preprocessed_id`."
    ),
)
def history(
    entity_type: str,
    record_id: int,
    db: Session = Depends(get_db),
) -> ChangeHistoryResponse:
    try:
        return get_change_history(db, entity_type=entity_type, record_id=record_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/validation-results",
    response_model=ValidationResultListResponse,
    summary="Validation Results",
    description="Zwraca listÄ™ wynikĂłw walidacji z opcjonalnym filtrowaniem i paginacjÄ….",
)
def validation_results(
    entity_type: str | None = Query(default=None, description="Opcjonalnie: PERSON albo PARTY."),
    source_system_code: str | None = Query(default=None, description="Kod systemu ĹşrĂłdĹ‚owego, np. KRS."),
    rule_code: str | None = Query(default=None, description="Kod reguĹ‚y walidacyjnej."),
    status: str | None = Query(default=None, description="Opcjonalny status walidacji, np. PASS albo ERROR."),
    severity: str | None = Query(default=None, description="Opcjonalna severity reguĹ‚y, np. INFO albo ERROR."),
    limit: int = Query(default=50, ge=1, le=200, description="Rozmiar strony wynikĂłw."),
    offset: int = Query(default=0, ge=0, description="PrzesuniÄ™cie paginacji."),
    db: Session = Depends(get_db),
) -> ValidationResultListResponse:
    try:
        return list_validation_results(
            db,
            entity_type=entity_type,
            source_system_code=source_system_code,
            rule_code=rule_code,
            status=status,
            severity=severity,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/match-results/levenshtein",
    response_model=MatchCandidateListResponse,
    summary="Levenshtein Matches",
    description=(
        "Zwraca listÄ™ kandydatĂłw dopasowania Levenshteina. "
        "Z odpowiedzi bierzesz `left_preprocessed_id` i `right_preprocessed_id` do endpointu comparison."
    ),
)
def levenshtein_results(
    entity_type: str | None = Query(default=None, description="Opcjonalnie: PERSON albo PARTY."),
    decision: str | None = Query(default=None, description="Opcjonalny status decyzji matchingu."),
    limit: int = Query(default=50, ge=1, le=200, description="Rozmiar strony wynikĂłw."),
    offset: int = Query(default=0, ge=0, description="PrzesuniÄ™cie paginacji."),
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


@router.get(
    "/match-results/jaro-winkler",
    response_model=MatchCandidateListResponse,
    summary="Jaro-Winkler Matches",
    description=(
        "Zwraca listÄ™ kandydatĂłw dopasowania Jaro-Winklera. "
        "Z odpowiedzi bierzesz `left_preprocessed_id` i `right_preprocessed_id` do endpointu comparison."
    ),
)
def jaro_winkler_results(
    entity_type: str | None = Query(default=None, description="Opcjonalnie: PERSON albo PARTY."),
    decision: str | None = Query(default=None, description="Opcjonalny status decyzji matchingu."),
    limit: int = Query(default=50, ge=1, le=200, description="Rozmiar strony wynikĂłw."),
    offset: int = Query(default=0, ge=0, description="PrzesuniÄ™cie paginacji."),
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


@router.get(
    "/match-results/comparison",
    response_model=MatchComparisonDetailResponse,
    summary="Compare Two Records",
    description=(
        "Zwraca szczegĂłĹ‚y porĂłwnania dwĂłch rekordĂłw z warstwy preprocessed. "
        "Tutaj podajesz `left_preprocessed_id` i `right_preprocessed_id` pobrane z endpointĂłw "
        "`/match-results/levenshtein` albo `/match-results/jaro-winkler`."
    ),
)
def match_comparison(
    entity_type: str = Query(..., description="PERSON albo PARTY."),
    left_preprocessed_id: int = Query(..., description="ID lewego rekordu z warstwy preprocessed."),
    right_preprocessed_id: int = Query(..., description="ID prawego rekordu z warstwy preprocessed."),
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


@router.get(
    "/counts",
    response_model=StageCountResponse,
    summary="Stage Counts",
    description="Zwraca podstawowe liczniki rekordĂłw dla kolejnych etapĂłw przetwarzania.",
)
def counts(db: Session = Depends(get_db)) -> StageCountResponse:
    return get_stage_counts(db)
