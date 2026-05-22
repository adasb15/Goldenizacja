from dataclasses import asdict

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.sql import get_db
from app.layers.integration_golden.schemas import LayerStatus, MatchingRunResponse
from app.layers.integration_golden.service import (
    DEFAULT_MATCHING_MAX_PAIRS,
    MatchingPairLimitExceededError,
    PreprocessedRecordsNotFoundError,
    find_match_candidates,
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
    min_score: float = Form(0.70),
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
