from typing import Any

from sqlalchemy.orm import Session

from app.layers.integration_golden.models import (
    DimAddress,
    DimAddressType,
    DimParty,
    DimPerson,
    EntityChangeLog,
    FactlessPartyAddress,
    FactlessPartyIdentities,
    FactlessPersonAddress,
    GoldenPartyLineage,
    GoldenPersonLineage,
    JaroWinklerCandidateRecord,
    MatchCandidateRecord,
)
from app.layers.serving.repository import ServingRepository
from app.layers.serving.schemas import (
    AddressResponse,
    ChangeHistoryEntry,
    ChangeHistoryResponse,
    GoldenRecordListResponse,
    GoldenRecordSummary,
    LineageEntry,
    LineageResponse,
    MatchCandidateListItem,
    MatchCandidateListResponse,
    MatchComparisonDetailResponse,
    PageMeta,
    PartyDetailResponse,
    PartyIdentityResponse,
    PersonDetailResponse,
    StageCountResponse,
    ValidationResultListResponse,
    ValidationResultResponse,
)
from app.layers.staging_validation.mapper import normalize_entity_type


class GoldenRecordNotFoundError(Exception):
    pass


def list_golden_records(
    db: Session,
    *,
    entity_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    repo: ServingRepository | None = None,
) -> GoldenRecordListResponse:
    repo = repo or ServingRepository(db)
    records, total = repo.list_golden_records(entity_type=entity_type, limit=limit, offset=offset)
    return GoldenRecordListResponse(
        items=[_golden_summary(record) for record in records],
        page=PageMeta(limit=limit, offset=offset, total=total),
    )


def get_person_detail(
    db: Session,
    *,
    person_id: int,
    repo: ServingRepository | None = None,
) -> PersonDetailResponse:
    repo = repo or ServingRepository(db)
    person = repo.get_person(person_id)
    if person is None:
        raise GoldenRecordNotFoundError(f"Person_ID={person_id} not found.")
    return _person_detail(person, repo.get_person_addresses(person_id))


def get_party_detail(
    db: Session,
    *,
    party_id: int,
    repo: ServingRepository | None = None,
) -> PartyDetailResponse:
    repo = repo or ServingRepository(db)
    party = repo.get_party(party_id)
    if party is None:
        raise GoldenRecordNotFoundError(f"Party_ID={party_id} not found.")
    return _party_detail(
        party,
        identities=repo.get_party_identities(party_id),
        addresses=repo.get_party_addresses(party_id),
    )


def search_person_by_pesel(
    db: Session,
    *,
    pesel: str,
    repo: ServingRepository | None = None,
) -> PersonDetailResponse:
    repo = repo or ServingRepository(db)
    person = repo.search_person_by_pesel(pesel=pesel)
    if person is None:
        raise GoldenRecordNotFoundError(f"Person with PESEL={pesel} not found.")
    return _person_detail(person, repo.get_person_addresses(person.Person_ID))


def search_parties(
    db: Session,
    *,
    nip: str | None = None,
    regon: str | None = None,
    krs: str | None = None,
    lei: str | None = None,
    name: str | None = None,
    limit: int = 50,
    offset: int = 0,
    repo: ServingRepository | None = None,
) -> GoldenRecordListResponse:
    repo = repo or ServingRepository(db)
    records, total = repo.search_parties(
        nip=nip,
        regon=regon,
        krs=krs,
        lei=lei,
        name=name,
        limit=limit,
        offset=offset,
    )
    return GoldenRecordListResponse(
        items=[_golden_summary(record) for record in records],
        page=PageMeta(limit=limit, offset=offset, total=total),
    )


def get_lineage(
    db: Session,
    *,
    entity_type: str,
    record_id: int,
    repo: ServingRepository | None = None,
) -> LineageResponse:
    repo = repo or ServingRepository(db)
    normalized = normalize_entity_type(entity_type)
    rows = repo.get_lineage(normalized, record_id)
    return LineageResponse(
        entity_type=normalized,
        record_id=record_id,
        items=[_lineage_entry(lineage, source_system) for lineage, source_system in rows],
    )


def get_change_history(
    db: Session,
    *,
    entity_type: str,
    record_id: int,
    repo: ServingRepository | None = None,
) -> ChangeHistoryResponse:
    repo = repo or ServingRepository(db)
    normalized = normalize_entity_type(entity_type)
    changes = repo.get_change_history(normalized, record_id)
    return ChangeHistoryResponse(
        entity_type=normalized,
        record_id=record_id,
        items=[_change_history_entry(change) for change in changes],
    )


def list_validation_results(
    db: Session,
    *,
    entity_type: str | None = None,
    source_system_code: str | None = None,
    rule_code: str | None = None,
    limit: int = 50,
    offset: int = 0,
    repo: ServingRepository | None = None,
) -> ValidationResultListResponse:
    repo = repo or ServingRepository(db)
    rows, total = repo.list_validation_results(
        entity_type=entity_type,
        source_system_code=source_system_code,
        rule_code=rule_code,
        limit=limit,
        offset=offset,
    )
    return ValidationResultListResponse(
        items=[_validation_result(result, source_system) for result, source_system in rows],
        page=PageMeta(limit=limit, offset=offset, total=total),
    )


def list_levenshtein_candidates(
    db: Session,
    *,
    entity_type: str | None = None,
    decision: str | None = None,
    limit: int = 50,
    offset: int = 0,
    repo: ServingRepository | None = None,
) -> MatchCandidateListResponse:
    repo = repo or ServingRepository(db)
    rows, total = repo.list_levenshtein_candidates(
        entity_type=entity_type,
        decision=decision,
        limit=limit,
        offset=offset,
    )
    return MatchCandidateListResponse(
        items=[_levenshtein_candidate(row, repo) for row in rows],
        page=PageMeta(limit=limit, offset=offset, total=total),
    )


def list_jaro_winkler_candidates(
    db: Session,
    *,
    entity_type: str | None = None,
    decision: str | None = None,
    limit: int = 50,
    offset: int = 0,
    repo: ServingRepository | None = None,
) -> MatchCandidateListResponse:
    repo = repo or ServingRepository(db)
    rows, total = repo.list_jaro_winkler_candidates(
        entity_type=entity_type,
        decision=decision,
        limit=limit,
        offset=offset,
    )
    return MatchCandidateListResponse(
        items=[_jaro_winkler_candidate(row, repo) for row in rows],
        page=PageMeta(limit=limit, offset=offset, total=total),
    )


def get_match_comparison(
    db: Session,
    *,
    entity_type: str,
    left_preprocessed_id: int,
    right_preprocessed_id: int,
    repo: ServingRepository | None = None,
) -> MatchComparisonDetailResponse:
    repo = repo or ServingRepository(db)
    normalized = normalize_entity_type(entity_type)
    levenshtein, jaro_winkler, left_record, right_record = repo.get_match_comparison(
        entity_type=normalized,
        left_preprocessed_id=left_preprocessed_id,
        right_preprocessed_id=right_preprocessed_id,
    )
    return MatchComparisonDetailResponse(
        entity_type=normalized,
        left_preprocessed_id=min(left_preprocessed_id, right_preprocessed_id),
        right_preprocessed_id=max(left_preprocessed_id, right_preprocessed_id),
        levenshtein=_levenshtein_candidate(levenshtein, repo) if levenshtein else None,
        jaro_winkler=_jaro_winkler_candidate(jaro_winkler, repo) if jaro_winkler else None,
        left_record=repo.record_to_dict(left_record),
        right_record=repo.record_to_dict(right_record),
    )


def get_stage_counts(
    db: Session,
    *,
    repo: ServingRepository | None = None,
) -> StageCountResponse:
    repo = repo or ServingRepository(db)
    return StageCountResponse(**repo.get_stage_counts())


def _golden_summary(record: Any) -> GoldenRecordSummary:
    if isinstance(record, DimPerson) or hasattr(record, "Person_ID"):
        display_name = " ".join(
            value
            for value in (record.First_Name, record.Second_Name, record.Last_Name)
            if value
        ) or None
        return GoldenRecordSummary(
            entity_type="PERSON",
            record_id=record.Person_ID,
            display_name=display_name,
            primary_identifier=record.PESEL,
            created_at=record.Created_At,
            updated_at=record.Updated_At,
        )
    return GoldenRecordSummary(
        entity_type="PARTY",
        record_id=record.Party_ID,
        display_name=record.Name,
        primary_identifier=None,
        created_at=record.Created_At,
        updated_at=record.Updated_At,
    )


def _person_detail(person: DimPerson, address_rows: list[Any]) -> PersonDetailResponse:
    return PersonDetailResponse(
        person_id=person.Person_ID,
        pesel=person.PESEL,
        serial_number_id_card=person.Serial_Number_ID_Card,
        serial_number_passport=person.Serial_Number_Passport,
        first_name=person.First_Name,
        second_name=person.Second_Name,
        last_name=person.Last_Name,
        family_name=person.Family_Name,
        birth_date=person.Birth_Date,
        place_of_birth=person.Place_Of_Birth,
        sex=person.Sex,
        citizenship=person.Citizenship,
        phone_number=person.Phone_Number,
        email_address=person.Email_Address,
        created_at=person.Created_At,
        updated_at=person.Updated_At,
        addresses=[_address_response(link, address, address_type) for link, address, address_type in address_rows],
    )


def _party_detail(
    party: DimParty,
    *,
    identities: list[Any],
    addresses: list[Any],
) -> PartyDetailResponse:
    return PartyDetailResponse(
        party_id=party.Party_ID,
        name=party.Name,
        short_name=party.Short_Name,
        legal_entity_type=party.Legal_Entity_Type,
        registration_country=party.Registration_Country,
        establishment_date=party.Establishment_Date,
        created_at=party.Created_At,
        updated_at=party.Updated_At,
        identities=[_party_identity_response(identity, identity_type) for identity, identity_type in identities],
        addresses=[_address_response(link, address, address_type) for link, address, address_type in addresses],
    )


def _address_response(
    link: FactlessPersonAddress | FactlessPartyAddress,
    address: DimAddress,
    address_type: DimAddressType,
) -> AddressResponse:
    return AddressResponse(
        address_id=address.Address_ID,
        address_type=address_type.AddressType_Name,
        street=address.Street,
        building_number=address.Building_Number,
        apartment_number=address.Apartment_Number,
        city=address.City,
        postal_city=address.Postal_City,
        postal_code=address.Postal_Code,
        district=address.District,
        province=address.Province,
        country=address.Country,
        valid_from=link.Valid_From,
        valid_to=link.Valid_To,
    )


def _party_identity_response(
    identity: FactlessPartyIdentities,
    identity_type: Any,
) -> PartyIdentityResponse:
    return PartyIdentityResponse(
        party_identity_id=identity.PartyIdentity_ID,
        identity_type=identity_type.IdentityType_Name,
        identity_value=identity.Identity_Value,
        is_valid=identity.Is_Valid,
        match_confidence=float(identity.Match_Confidence) if identity.Match_Confidence is not None else None,
        valid_from=identity.Valid_From,
        valid_to=identity.Valid_To,
    )


def _lineage_entry(
    lineage: GoldenPersonLineage | GoldenPartyLineage,
    source_system: Any,
) -> LineageEntry:
    return LineageEntry(
        lineage_type="PERSON" if hasattr(lineage, "DimPerson_ID") else "PARTY",
        lineage_id=lineage.Lineage_ID,
        attribute_name=lineage.Attribute_Name,
        source_system_id=lineage.SourceSystem_ID,
        source_system_code=source_system.SourceSystem_Code,
        source_record_id=lineage.Source_Record_ID,
        import_batch_id=lineage.ImportBatch_ID,
        selection_rule=lineage.Selection_Rule,
        trust_score=float(lineage.Trust_Score) if lineage.Trust_Score is not None else None,
        quality_score=float(lineage.Quality_Score) if lineage.Quality_Score is not None else None,
        validation_status=lineage.Validation_Status,
        recorded_at=lineage.Recorded_At,
    )


def _change_history_entry(change: EntityChangeLog) -> ChangeHistoryEntry:
    return ChangeHistoryEntry(
        change_id=change.Change_ID,
        entity_type=change.Entity_Type,
        attribute_name=change.Attribute_Name,
        old_value=change.Old_Value,
        new_value=change.New_Value,
        import_batch_id=change.ImportBatch_ID,
        change_date=change.Change_Date,
    )


def _validation_result(result: Any, source_system: Any) -> ValidationResultResponse:
    return ValidationResultResponse(
        validation_id=result.Validation_ID,
        import_batch_id=result.ImportBatch_ID,
        raw_file_id=result.RawFile_ID,
        source_system_code=source_system.SourceSystem_Code,
        entity_type=result.Entity_Type,
        staging_id=result.Staging_ID,
        preprocessed_id=result.Preprocessed_ID,
        validation_level=result.Validation_Level,
        rule_code=result.Rule_Code,
        field_name=result.Field_Name,
        severity=result.Severity,
        status=result.Status,
        message=result.Message,
        checked_value=result.Checked_Value,
        created_at=result.Created_At,
    )


def _levenshtein_candidate(
    candidate: MatchCandidateRecord,
    repo: ServingRepository,
) -> MatchCandidateListItem:
    return MatchCandidateListItem(
        candidate_id=candidate.Match_Candidate_Levenshtein_ID,
        entity_type=candidate.Entity_Type,
        raw_file_id=candidate.RawFile_ID,
        left_preprocessed_id=candidate.Left_Preprocessed_ID,
        right_preprocessed_id=candidate.Right_Preprocessed_ID,
        left_staging_id=candidate.Left_Staging_ID,
        right_staging_id=candidate.Right_Staging_ID,
        left_raw_file_id=candidate.Left_RawFile_ID,
        right_raw_file_id=candidate.Right_RawFile_ID,
        left_source_record_id=candidate.Left_Source_Record_ID,
        right_source_record_id=candidate.Right_Source_Record_ID,
        levenshtein_score=candidate.Score,
        decision=candidate.Decision,
        strong_match_fields=repo.parse_json_list(candidate.Strong_Match_Fields_JSON),
        conflict_fields=repo.parse_json_list(candidate.Conflict_Fields_JSON),
        created_at=candidate.Created_At,
    )


def _jaro_winkler_candidate(
    candidate: JaroWinklerCandidateRecord,
    repo: ServingRepository,
) -> MatchCandidateListItem:
    return MatchCandidateListItem(
        candidate_id=candidate.Match_Candidate_JaroWinkler_ID,
        entity_type=candidate.Entity_Type,
        raw_file_id=candidate.RawFile_ID,
        left_preprocessed_id=candidate.Left_Preprocessed_ID,
        right_preprocessed_id=candidate.Right_Preprocessed_ID,
        left_staging_id=candidate.Left_Staging_ID,
        right_staging_id=candidate.Right_Staging_ID,
        left_raw_file_id=candidate.Left_RawFile_ID,
        right_raw_file_id=candidate.Right_RawFile_ID,
        left_source_record_id=candidate.Left_Source_Record_ID,
        right_source_record_id=candidate.Right_Source_Record_ID,
        levenshtein_score=candidate.Levenshtein_Score,
        jaro_winkler_score=candidate.JaroWinkler_Score,
        decision=candidate.Decision,
        strong_match_fields=repo.parse_json_list(candidate.Strong_Match_Fields_JSON),
        conflict_fields=repo.parse_json_list(candidate.Conflict_Fields_JSON),
        text_match_fields=repo.parse_json_list(candidate.Text_Match_Fields_JSON),
        created_at=candidate.Created_At,
    )
