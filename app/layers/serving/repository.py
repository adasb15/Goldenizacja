import json
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.layers.ingestion.models import ImportBatch, RawFile, SourceSystem
from app.layers.integration_golden.models import (
    DimAddress,
    DimAddressType,
    DimIdentityType,
    DimParty,
    DimPerson,
    EntityChangeLog,
    EntityGroupRecord,
    FactlessPartyAddress,
    FactlessPartyIdentities,
    FactlessPersonAddress,
    GoldenPartyLineage,
    GoldenPersonLineage,
    JaroWinklerCandidateRecord,
    MatchCandidateRecord,
)
from app.layers.preprocessing.models import PartyPreprocessed, PersonPreprocessed
from app.layers.staging_validation.mapper import normalize_entity_type
from app.layers.staging_validation.models import PartyStaging, PersonStaging
from app.layers.validation.models import ValidationResult


class ServingRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_golden_records(
        self,
        *,
        entity_type: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]:
        normalized_entity_type = normalize_entity_type(entity_type) if entity_type else None

        if normalized_entity_type == "PERSON":
            query = select(DimPerson).order_by(DimPerson.Person_ID)
            return list(self.db.scalars(query.offset(offset).limit(limit))), self._count(query)
        if normalized_entity_type == "PARTY":
            query = select(DimParty).order_by(DimParty.Party_ID)
            return list(self.db.scalars(query.offset(offset).limit(limit))), self._count(query)

        person_total = self._count_table(DimPerson)
        party_total = self._count_table(DimParty)
        total = person_total + party_total
        items: list[Any] = []
        remaining = limit

        if offset < person_total:
            person_query = select(DimPerson).order_by(DimPerson.Person_ID)
            people = list(self.db.scalars(person_query.offset(offset).limit(remaining)))
            items.extend(people)
            remaining -= len(people)
            party_offset = 0
        else:
            party_offset = offset - person_total

        if remaining > 0:
            party_query = select(DimParty).order_by(DimParty.Party_ID)
            items.extend(self.db.scalars(party_query.offset(party_offset).limit(remaining)))

        return items, total

    def get_person(self, person_id: int) -> DimPerson | None:
        return self.db.get(DimPerson, person_id)

    def get_party(self, party_id: int) -> DimParty | None:
        return self.db.get(DimParty, party_id)

    def search_person_by_pesel(self, pesel: str) -> DimPerson | None:
        return self.db.scalar(select(DimPerson).where(DimPerson.PESEL == pesel))

    def search_parties(
        self,
        *,
        nip: str | None,
        regon: str | None,
        krs: str | None,
        lei: str | None,
        name: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[DimParty], int]:
        identity_conditions = []
        for identity_type, value in {
            "NIP": nip,
            "REGON": regon,
            "KRS": krs,
            "LEI": lei,
        }.items():
            if self._is_present(value):
                identity_conditions.append(
                    (DimIdentityType.IdentityType_Name == identity_type)
                    & (FactlessPartyIdentities.Identity_Value == value)
                )

        query = select(DimParty)
        if identity_conditions:
            query = query.join(
                FactlessPartyIdentities,
                FactlessPartyIdentities.Party_ID == DimParty.Party_ID,
            ).join(
                DimIdentityType,
                DimIdentityType.IdentityType_ID == FactlessPartyIdentities.IdentityType_ID,
            )
        conditions = []
        if identity_conditions:
            conditions.append(or_(*identity_conditions))
        if self._is_present(name):
            conditions.append(DimParty.Name.ilike(f"%{name.strip()}%"))
        if conditions:
            query = query.where(or_(*conditions))
        query = query.distinct().order_by(DimParty.Party_ID)
        total = self._count(query)
        return list(self.db.scalars(query.offset(offset).limit(limit))), total

    def get_person_addresses(self, person_id: int) -> list[Any]:
        query = (
            select(FactlessPersonAddress, DimAddress, DimAddressType)
            .join(DimAddress, DimAddress.Address_ID == FactlessPersonAddress.Address_ID)
            .join(DimAddressType, DimAddressType.AddressType_ID == FactlessPersonAddress.AddressType_ID)
            .where(FactlessPersonAddress.Person_ID == person_id)
            .order_by(FactlessPersonAddress.PersonAddress_ID)
        )
        return list(self.db.execute(query))

    def get_party_addresses(self, party_id: int) -> list[Any]:
        query = (
            select(FactlessPartyAddress, DimAddress, DimAddressType)
            .join(DimAddress, DimAddress.Address_ID == FactlessPartyAddress.Address_ID)
            .join(DimAddressType, DimAddressType.AddressType_ID == FactlessPartyAddress.AddressType_ID)
            .where(FactlessPartyAddress.Party_ID == party_id)
            .order_by(FactlessPartyAddress.PartyAddress_ID)
        )
        return list(self.db.execute(query))

    def get_party_identities(self, party_id: int) -> list[Any]:
        query = (
            select(FactlessPartyIdentities, DimIdentityType)
            .join(
                DimIdentityType,
                DimIdentityType.IdentityType_ID == FactlessPartyIdentities.IdentityType_ID,
            )
            .where(FactlessPartyIdentities.Party_ID == party_id)
            .order_by(FactlessPartyIdentities.PartyIdentity_ID)
        )
        return list(self.db.execute(query))

    def get_lineage(self, entity_type: str, record_id: int) -> list[Any]:
        entity_type = normalize_entity_type(entity_type)
        if entity_type == "PERSON":
            query = (
                select(GoldenPersonLineage, SourceSystem)
                .join(SourceSystem, SourceSystem.SourceSystem_ID == GoldenPersonLineage.SourceSystem_ID)
                .where(GoldenPersonLineage.DimPerson_ID == record_id)
                .order_by(GoldenPersonLineage.Lineage_ID)
            )
        else:
            query = (
                select(GoldenPartyLineage, SourceSystem)
                .join(SourceSystem, SourceSystem.SourceSystem_ID == GoldenPartyLineage.SourceSystem_ID)
                .where(GoldenPartyLineage.DimParty_ID == record_id)
                .order_by(GoldenPartyLineage.Lineage_ID)
            )
        return list(self.db.execute(query))

    def get_change_history(self, entity_type: str, record_id: int) -> list[EntityChangeLog]:
        entity_type = normalize_entity_type(entity_type)
        id_column = EntityChangeLog.DimPerson_ID if entity_type == "PERSON" else EntityChangeLog.DimParty_ID
        query = (
            select(EntityChangeLog)
            .where(EntityChangeLog.Entity_Type == entity_type)
            .where(id_column == record_id)
            .order_by(EntityChangeLog.Change_Date.desc(), EntityChangeLog.Change_ID.desc())
        )
        return list(self.db.scalars(query))

    def list_validation_results(
        self,
        *,
        entity_type: str | None,
        source_system_code: str | None,
        rule_code: str | None,
        status: str | None,
        severity: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]:
        query = (
            select(ValidationResult, SourceSystem)
            .join(RawFile, RawFile.RawFile_ID == ValidationResult.RawFile_ID)
            .join(ImportBatch, ImportBatch.ImportBatch_ID == RawFile.ImportBatch_ID)
            .join(SourceSystem, SourceSystem.SourceSystem_ID == ImportBatch.SourceSystem_ID)
            .order_by(ValidationResult.Validation_ID.desc())
        )
        if entity_type:
            query = query.where(ValidationResult.Entity_Type == normalize_entity_type(entity_type))
        if self._is_present(source_system_code):
            query = query.where(SourceSystem.SourceSystem_Code == source_system_code.strip().upper())
        if self._is_present(rule_code):
            query = query.where(ValidationResult.Rule_Code == rule_code.strip())
        if self._is_present(status):
            query = query.where(ValidationResult.Status == status.strip().upper())
        if self._is_present(severity):
            query = query.where(ValidationResult.Severity == severity.strip().upper())
        total = self._count(query)
        return list(self.db.execute(query.offset(offset).limit(limit))), total

    def list_levenshtein_candidates(
        self,
        *,
        entity_type: str | None,
        decision: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[MatchCandidateRecord], int]:
        query = select(MatchCandidateRecord).order_by(MatchCandidateRecord.Score.desc())
        if entity_type:
            query = query.where(MatchCandidateRecord.Entity_Type == normalize_entity_type(entity_type))
        if self._is_present(decision):
            query = query.where(MatchCandidateRecord.Decision == decision.strip().upper())
        total = self._count(query)
        return list(self.db.scalars(query.offset(offset).limit(limit))), total

    def list_jaro_winkler_candidates(
        self,
        *,
        entity_type: str | None,
        decision: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[JaroWinklerCandidateRecord], int]:
        query = select(JaroWinklerCandidateRecord).order_by(
            JaroWinklerCandidateRecord.JaroWinkler_Score.desc()
        )
        if entity_type:
            query = query.where(JaroWinklerCandidateRecord.Entity_Type == normalize_entity_type(entity_type))
        if self._is_present(decision):
            query = query.where(JaroWinklerCandidateRecord.Decision == decision.strip().upper())
        total = self._count(query)
        return list(self.db.scalars(query.offset(offset).limit(limit))), total

    def get_jaro_winkler_pair_keys(
        self,
        candidates: list[MatchCandidateRecord],
    ) -> set[tuple[str, int, int]]:
        if not candidates:
            return set()

        conditions = [
            and_(
                JaroWinklerCandidateRecord.Entity_Type == candidate.Entity_Type,
                JaroWinklerCandidateRecord.Left_Preprocessed_ID == candidate.Left_Preprocessed_ID,
                JaroWinklerCandidateRecord.Right_Preprocessed_ID == candidate.Right_Preprocessed_ID,
            )
            for candidate in candidates
        ]
        query = select(
            JaroWinklerCandidateRecord.Entity_Type,
            JaroWinklerCandidateRecord.Left_Preprocessed_ID,
            JaroWinklerCandidateRecord.Right_Preprocessed_ID,
        ).where(or_(*conditions))
        return {
            (row.Entity_Type, int(row.Left_Preprocessed_ID), int(row.Right_Preprocessed_ID))
            for row in self.db.execute(query)
        }

    def get_match_comparison(
        self,
        *,
        entity_type: str,
        left_preprocessed_id: int,
        right_preprocessed_id: int,
    ) -> tuple[MatchCandidateRecord | None, JaroWinklerCandidateRecord | None, Any | None, Any | None]:
        entity_type = normalize_entity_type(entity_type)
        left_id, right_id = sorted((left_preprocessed_id, right_preprocessed_id))
        levenshtein = self.db.scalar(
            select(MatchCandidateRecord)
            .where(MatchCandidateRecord.Entity_Type == entity_type)
            .where(MatchCandidateRecord.Left_Preprocessed_ID == left_id)
            .where(MatchCandidateRecord.Right_Preprocessed_ID == right_id)
        )
        jaro_winkler = self.db.scalar(
            select(JaroWinklerCandidateRecord)
            .where(JaroWinklerCandidateRecord.Entity_Type == entity_type)
            .where(JaroWinklerCandidateRecord.Left_Preprocessed_ID == left_id)
            .where(JaroWinklerCandidateRecord.Right_Preprocessed_ID == right_id)
        )
        model = PersonPreprocessed if entity_type == "PERSON" else PartyPreprocessed
        left_record = self.db.get(model, left_id)
        right_record = self.db.get(model, right_id)
        return levenshtein, jaro_winkler, left_record, right_record

    def get_stage_counts(self) -> dict[str, int]:
        return {
            "raw_files": self._count_table(RawFile),
            "person_staging": self._count_table(PersonStaging),
            "party_staging": self._count_table(PartyStaging),
            "person_preprocessed": self._count_table(PersonPreprocessed),
            "party_preprocessed": self._count_table(PartyPreprocessed),
            "validation_results": self._count_table(ValidationResult),
            "levenshtein_candidates": self._count_table(MatchCandidateRecord),
            "jaro_winkler_candidates": self._count_table(JaroWinklerCandidateRecord),
            "entity_groups": self._count_table(EntityGroupRecord),
            "golden_persons": self._count_table(DimPerson),
            "golden_parties": self._count_table(DimParty),
        }

    def record_to_dict(self, record: Any | None) -> dict[str, Any] | None:
        if record is None:
            return None
        return {column.name: getattr(record, column.name) for column in record.__table__.columns}

    def parse_json_list(self, value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    def _count_table(self, model: Any) -> int:
        return int(self.db.scalar(select(func.count()).select_from(model)) or 0)

    def _count(self, query: Any) -> int:
        return int(self.db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0)

    def _is_present(self, value: str | None) -> bool:
        return value is not None and value.strip() != ""
