from dataclasses import asdict

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.sql import get_db
from app.layers.integration_golden.schemas import (
    EntityGroupingRunResponse,
    GoldenLoadRunResponse,
    JaroWinklerRunResponse,
    LayerStatus,
    MatchingRunResponse,
)
from app.layers.integration_golden.service import (
    DEFAULT_MATCHING_MAX_PAIRS,
    JARO_WINKLER_CANDIDATE_THRESHOLD,
    LEVENSHTEIN_CANDIDATE_THRESHOLD,
    LevenshteinCandidatesNotFoundError,
    MatchingPairLimitExceededError,
    PreprocessedRecordsNotFoundError,
    find_match_candidates,
    golden_load_dimensions,
    group_auto_merge_candidates,
    refine_match_candidates_with_jaro_winkler,
)

# Wystawiamy status integration_golden, żeby warstwa była widoczna zanim powstanie goldenizacja
router = APIRouter(prefix="/integration_golden", tags=["integration_golden"])


@router.get("/status", response_model=LayerStatus)
def status() -> LayerStatus:
    return LayerStatus(layer="integration_golden", status="ready")


@router.post("/match-candidates", response_model=MatchingRunResponse)
def match_candidates(
    entity_type: str = Form(...),
    raw_file_id: int | None = Form(None),
    min_score: float = Form(LEVENSHTEIN_CANDIDATE_THRESHOLD),
    max_pairs: int = Form(DEFAULT_MATCHING_MAX_PAIRS),
    db: Session = Depends(get_db),
) -> MatchingRunResponse:
    try:
        result = find_match_candidates(
            db=db,
            entity_type=entity_type,
            raw_file_id=raw_file_id,
            min_score=min_score,
            max_pairs=max_pairs,
        )
        return MatchingRunResponse(**asdict(result))
    except (
        PreprocessedRecordsNotFoundError,
        MatchingPairLimitExceededError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MATCH_CANDIDATES failed: {exc}") from exc


@router.post("/match-candidates/jaro-winkler", response_model=JaroWinklerRunResponse)
def match_candidates_jaro_winkler(
    entity_type: str = Form(...),
    raw_file_id: int | None = Form(None),
    min_score: float = Form(JARO_WINKLER_CANDIDATE_THRESHOLD),
    db: Session = Depends(get_db),
) -> JaroWinklerRunResponse:
    try:
        result = refine_match_candidates_with_jaro_winkler(
            db=db,
            entity_type=entity_type,
            raw_file_id=raw_file_id,
            min_score=min_score,
        )
        return JaroWinklerRunResponse(**asdict(result))
    except (
        LevenshteinCandidatesNotFoundError,
        PreprocessedRecordsNotFoundError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"JARO_WINKLER_MATCH failed: {exc}") from exc


@router.post("/match-groups", response_model=EntityGroupingRunResponse)
def match_groups(
    entity_type: str = Form(...),
    db: Session = Depends(get_db),
) -> EntityGroupingRunResponse:
    try:
        result = group_auto_merge_candidates(
            db=db,
            entity_type=entity_type,
        )
        return EntityGroupingRunResponse(**asdict(result))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MATCH_GROUPS failed: {exc}") from exc


@router.post("/golden-load", response_model=GoldenLoadRunResponse)
def golden_load(
    entity_type: str = Form(...),
    entity_group_id: int | None = Form(None),
    db: Session = Depends(get_db),
) -> GoldenLoadRunResponse:
    try:
        result = golden_load_dimensions(
            db=db,
            entity_type=entity_type,
            entity_group_id=entity_group_id,
        )
        return GoldenLoadRunResponse(**asdict(result))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"GOLDEN_LOAD failed: {exc}") from exc
