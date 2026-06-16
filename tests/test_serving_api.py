from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.db.sql import get_db
from app.layers.serving.api import router
from app.layers.serving.schemas import (
    ChangeHistoryResponse,
    GoldenRecordListResponse,
    GoldenRecordSummary,
    LineageResponse,
    MatchCandidateListItem,
    MatchCandidateListResponse,
    MatchComparisonDetailResponse,
    PageMeta,
    PartyDetailResponse,
    PersonDetailResponse,
    StageCountResponse,
    ValidationResultListResponse,
)


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()
    return TestClient(app)


def test_get_golden_records_returns_paginated_payload() -> None:
    client = build_client()
    mocked = GoldenRecordListResponse(
        items=[
            GoldenRecordSummary(
                entity_type="PERSON",
                record_id=1,
                display_name="JAN KOWALSKI",
                primary_identifier="90010112345",
                created_at=datetime(2026, 6, 1, 10, 0, 0),
            )
        ],
        page=PageMeta(limit=10, offset=0, total=1),
    )

    with patch("app.layers.serving.api.list_golden_records", return_value=mocked) as service:
        response = client.get("/serving/golden-records?entity_type=PERSON&search=KOWALSKI&limit=10&offset=0")

    assert response.status_code == 200
    assert response.json()["items"][0]["record_id"] == 1
    assert response.json()["page"]["total"] == 1
    service.assert_called_once()
    assert service.call_args.kwargs["entity_type"] == "PERSON"
    assert service.call_args.kwargs["search"] == "KOWALSKI"


def test_get_person_detail_returns_person_payload() -> None:
    client = build_client()
    mocked = PersonDetailResponse(
        person_id=10,
        pesel="90010112345",
        first_name="JAN",
        last_name="KOWALSKI",
    )

    with patch("app.layers.serving.api.get_person_detail", return_value=mocked):
        response = client.get("/serving/persons/10")

    assert response.status_code == 200
    assert response.json()["person_id"] == 10
    assert response.json()["pesel"] == "90010112345"


def test_get_party_detail_returns_party_payload() -> None:
    client = build_client()
    mocked = PartyDetailResponse(
        party_id=20,
        name="ALFA SA",
    )

    with patch("app.layers.serving.api.get_party_detail", return_value=mocked):
        response = client.get("/serving/parties/20")

    assert response.status_code == 200
    assert response.json()["party_id"] == 20
    assert response.json()["name"] == "ALFA SA"


def test_search_person_by_pesel_uses_query_parameter() -> None:
    client = build_client()
    mocked = PersonDetailResponse(person_id=11, pesel="74042826025")

    with patch("app.layers.serving.api.search_person_by_pesel", return_value=mocked) as service:
        response = client.get("/serving/persons/search/by-pesel?pesel=74042826025")

    assert response.status_code == 200
    assert response.json()["person_id"] == 11
    assert service.call_args.kwargs["pesel"] == "74042826025"


def test_search_parties_supports_identity_and_name_filters() -> None:
    client = build_client()
    mocked = GoldenRecordListResponse(
        items=[GoldenRecordSummary(entity_type="PARTY", record_id=30, display_name="ALFA SA")],
        page=PageMeta(limit=50, offset=0, total=1),
    )

    with patch("app.layers.serving.api.search_parties", return_value=mocked) as service:
        response = client.get(
            "/serving/parties/search?nip=1234567890&regon=123456789&krs=0000001234&lei=ABC&name=ALFA"
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["entity_type"] == "PARTY"
    assert service.call_args.kwargs["nip"] == "1234567890"
    assert service.call_args.kwargs["regon"] == "123456789"
    assert service.call_args.kwargs["krs"] == "0000001234"
    assert service.call_args.kwargs["lei"] == "ABC"
    assert service.call_args.kwargs["name"] == "ALFA"


def test_lineage_and_history_endpoints_return_lists() -> None:
    client = build_client()
    lineage = LineageResponse(entity_type="PERSON", record_id=10, items=[])
    history = ChangeHistoryResponse(entity_type="PERSON", record_id=10, items=[])

    with (
        patch("app.layers.serving.api.get_lineage", return_value=lineage),
        patch("app.layers.serving.api.get_change_history", return_value=history),
    ):
        lineage_response = client.get("/serving/lineage/PERSON/10")
        history_response = client.get("/serving/history/PERSON/10")

    assert lineage_response.status_code == 200
    assert lineage_response.json()["items"] == []
    assert history_response.status_code == 200
    assert history_response.json()["entity_type"] == "PERSON"


def test_validation_results_endpoint_accepts_filters() -> None:
    client = build_client()
    mocked = ValidationResultListResponse(items=[], page=PageMeta(limit=25, offset=5, total=0))

    with patch("app.layers.serving.api.list_validation_results", return_value=mocked) as service:
        response = client.get(
            "/serving/validation-results?entity_type=PARTY&source_system_code=KRS&rule_code=NIP_INVALID&status=ERROR&severity=ERROR&limit=25&offset=5"
        )

    assert response.status_code == 200
    assert response.json()["page"]["limit"] == 25
    assert service.call_args.kwargs["entity_type"] == "PARTY"
    assert service.call_args.kwargs["source_system_code"] == "KRS"
    assert service.call_args.kwargs["rule_code"] == "NIP_INVALID"
    assert service.call_args.kwargs["status"] == "ERROR"
    assert service.call_args.kwargs["severity"] == "ERROR"


def test_matching_endpoints_and_comparison_return_payloads() -> None:
    client = build_client()
    candidate = MatchCandidateListItem(
        candidate_id=1,
        entity_type="PARTY",
        left_preprocessed_id=10,
        right_preprocessed_id=20,
        left_staging_id=100,
        right_staging_id=200,
        left_raw_file_id=1000,
        right_raw_file_id=2000,
        levenshtein_score=0.91,
        jaro_winkler_score=0.96,
        decision="AUTO_MERGE",
        strong_match_fields=["NIP"],
        conflict_fields=[],
        passed_to_second_stage=True,
    )
    list_response = MatchCandidateListResponse(
        items=[candidate],
        page=PageMeta(limit=50, offset=0, total=1),
    )
    comparison = MatchComparisonDetailResponse(
        entity_type="PARTY",
        left_preprocessed_id=10,
        right_preprocessed_id=20,
        levenshtein=candidate,
        jaro_winkler=candidate,
    )

    with (
        patch("app.layers.serving.api.list_levenshtein_candidates", return_value=list_response),
        patch("app.layers.serving.api.list_jaro_winkler_candidates", return_value=list_response),
        patch("app.layers.serving.api.get_match_comparison", return_value=comparison),
    ):
        levenshtein_response = client.get("/serving/match-results/levenshtein?entity_type=PARTY")
        jaro_response = client.get("/serving/match-results/jaro-winkler?entity_type=PARTY")
        comparison_response = client.get(
            "/serving/match-results/comparison?entity_type=PARTY&left_preprocessed_id=10&right_preprocessed_id=20"
        )

    assert levenshtein_response.status_code == 200
    assert jaro_response.status_code == 200
    assert comparison_response.status_code == 200
    assert comparison_response.json()["levenshtein"]["strong_match_fields"] == ["NIP"]


def test_counts_endpoint_returns_stage_counters() -> None:
    client = build_client()
    mocked = StageCountResponse(
        raw_files=1,
        person_staging=2,
        party_staging=3,
        person_preprocessed=4,
        party_preprocessed=5,
        validation_results=6,
        levenshtein_candidates=7,
        jaro_winkler_candidates=8,
        entity_groups=9,
        golden_persons=10,
        golden_parties=11,
    )

    with patch("app.layers.serving.api.get_stage_counts", return_value=mocked):
        response = client.get("/serving/counts")

    assert response.status_code == 200
    assert response.json()["golden_parties"] == 11


def test_main_app_has_cors_middleware_for_react() -> None:
    from app.main import app

    middleware_classes = [middleware.cls for middleware in app.user_middleware]

    assert CORSMiddleware in middleware_classes
