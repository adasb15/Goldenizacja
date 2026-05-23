"""Dostep do danych dla warstwy integration_golden."""

import json
from typing import Any

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.layers.integration_golden.models import MatchCandidateRecord
from app.layers.preprocessing.models import PartyPreprocessed, PersonPreprocessed
from app.layers.staging_validation.mapper import normalize_entity_type


class IntegrationGoldenRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_preprocessed_records(
        self,
        entity_type: str,
        raw_file_id: int | None = None,
    ) -> list[Any]:
        entity_type = normalize_entity_type(entity_type)
        model = PersonPreprocessed if entity_type == "PERSON" else PartyPreprocessed
        query = select(model).order_by(model.Preprocessed_ID)
        if raw_file_id is not None:
            query = query.where(model.RawFile_ID == raw_file_id)
        return list(self.db.scalars(query))

    def count_preprocessed_records(self, entity_type: str) -> int:
        entity_type = normalize_entity_type(entity_type)
        model = PersonPreprocessed if entity_type == "PERSON" else PartyPreprocessed
        return int(self.db.scalar(select(func.count()).select_from(model)) or 0)

    def get_candidate_records_for_match(self, entity_type: str, record: Any) -> list[Any]:
        entity_type = normalize_entity_type(entity_type)
        if entity_type == "PERSON":
            return self._get_person_candidate_records(record)
        return self._get_party_candidate_records(record)

    def replace_match_candidates(
        self,
        entity_type: str,
        raw_file_id: int | None,
        candidates: list[Any],
    ) -> int:
        entity_type = normalize_entity_type(entity_type)
        self.db.execute(
            delete(MatchCandidateRecord)
            .where(MatchCandidateRecord.Entity_Type == entity_type)
            .where(MatchCandidateRecord.RawFile_ID == raw_file_id)
        )

        entities = [
            MatchCandidateRecord(
                Entity_Type=entity_type,
                RawFile_ID=raw_file_id,
                Left_Preprocessed_ID=candidate.left_preprocessed_id,
                Right_Preprocessed_ID=candidate.right_preprocessed_id,
                Left_Staging_ID=candidate.left_staging_id,
                Right_Staging_ID=candidate.right_staging_id,
                Left_RawFile_ID=candidate.left_raw_file_id,
                Right_RawFile_ID=candidate.right_raw_file_id,
                Left_Source_Record_ID=candidate.left_source_record_id,
                Right_Source_Record_ID=candidate.right_source_record_id,
                Score=candidate.score,
                Decision=str(candidate.decision.value),
                Strong_Match_Fields_JSON=json.dumps(list(candidate.strong_match_fields), ensure_ascii=False),
                Conflict_Fields_JSON=json.dumps(list(candidate.conflict_fields), ensure_ascii=False),
            )
            for candidate in candidates
        ]
        self.db.add_all(entities)
        self.db.commit()
        return len(entities)

    def _get_person_candidate_records(self, record: Any) -> list[PersonPreprocessed]:
        conditions = []
        conditions.extend(
            self._exact_conditions(
                PersonPreprocessed,
                record,
                (
                    "PESEL_Normalized",
                    "Serial_Number_ID_Card_Normalized",
                    "Serial_Number_Passport_Normalized",
                    "Email_Normalized",
                    "Phone_Normalized",
                ),
            )
        )

        birth_date = self._record_value(record, "Birth_Date")
        last_name_prefix = self._prefix(self._record_value(record, "Last_Name_Normalized"))
        first_name_prefix = self._prefix(self._record_value(record, "First_Name_Normalized"))
        place_of_birth = self._record_value(record, "Place_Of_Birth_Normalized")
        postal_code = self._record_value(record, "Postal_Code_Normalized")

        if birth_date and last_name_prefix:
            conditions.append(
                and_(
                    PersonPreprocessed.Birth_Date == birth_date,
                    PersonPreprocessed.Last_Name_Normalized.like(f"{last_name_prefix}%"),
                )
            )
        if birth_date and first_name_prefix and last_name_prefix:
            conditions.append(
                and_(
                    PersonPreprocessed.Birth_Date == birth_date,
                    PersonPreprocessed.First_Name_Normalized.like(f"{first_name_prefix}%"),
                    PersonPreprocessed.Last_Name_Normalized.like(f"{last_name_prefix}%"),
                )
            )
        if birth_date and place_of_birth:
            conditions.append(
                and_(
                    PersonPreprocessed.Birth_Date == birth_date,
                    PersonPreprocessed.Place_Of_Birth_Normalized == place_of_birth,
                )
            )
        if postal_code and last_name_prefix:
            conditions.append(
                and_(
                    PersonPreprocessed.Postal_Code_Normalized == postal_code,
                    PersonPreprocessed.Last_Name_Normalized.like(f"{last_name_prefix}%"),
                )
            )

        return self._records_for_conditions(PersonPreprocessed, conditions)

    def _get_party_candidate_records(self, record: Any) -> list[PartyPreprocessed]:
        conditions = []
        conditions.extend(
            self._exact_conditions(
                PartyPreprocessed,
                record,
                (
                    "NIP_Normalized",
                    "REGON_Normalized",
                    "KRS_Normalized",
                    "LEI_Normalized",
                    "Decision_Number_Normalized",
                    "Register_Number_Normalized",
                    "Validation_Authority_Entity_ID_Normalized",
                    "Website_Normalized",
                    "Email_Normalized",
                    "Phone_Normalized",
                ),
            )
        )

        name_prefix = self._prefix(self._record_value(record, "Name_Normalized"))
        short_name = self._record_value(record, "Short_Name_Normalized")
        legal_entity_type = self._record_value(record, "Legal_Entity_Type_Normalized")
        city = self._record_value(record, "City_Normalized")
        postal_code = self._record_value(record, "Postal_Code_Normalized")
        country = self._record_value(record, "Country_Normalized") or self._record_value(
            record,
            "Registration_Country_Normalized",
        )

        if name_prefix and city:
            conditions.append(
                and_(
                    PartyPreprocessed.Name_Normalized.like(f"{name_prefix}%"),
                    PartyPreprocessed.City_Normalized == city,
                )
            )
        if name_prefix and postal_code:
            conditions.append(
                and_(
                    PartyPreprocessed.Name_Normalized.like(f"{name_prefix}%"),
                    PartyPreprocessed.Postal_Code_Normalized == postal_code,
                )
            )
        if name_prefix and country:
            conditions.append(
                and_(
                    PartyPreprocessed.Name_Normalized.like(f"{name_prefix}%"),
                    or_(
                        PartyPreprocessed.Country_Normalized == country,
                        PartyPreprocessed.Registration_Country_Normalized == country,
                    ),
                )
            )
        if short_name and country:
            conditions.append(
                and_(
                    PartyPreprocessed.Short_Name_Normalized == short_name,
                    or_(
                        PartyPreprocessed.Country_Normalized == country,
                        PartyPreprocessed.Registration_Country_Normalized == country,
                    ),
                )
            )
        if legal_entity_type and name_prefix:
            conditions.append(
                and_(
                    PartyPreprocessed.Legal_Entity_Type_Normalized == legal_entity_type,
                    PartyPreprocessed.Name_Normalized.like(f"{name_prefix}%"),
                )
            )

        return self._records_for_conditions(PartyPreprocessed, conditions)

    def _exact_conditions(
        self,
        model: type[PersonPreprocessed] | type[PartyPreprocessed],
        record: Any,
        field_names: tuple[str, ...],
    ) -> list[Any]:
        conditions = []
        for field_name in field_names:
            value = self._record_value(record, field_name)
            if self._is_present(value):
                conditions.append(getattr(model, field_name) == value)
        return conditions

    def _records_for_conditions(
        self,
        model: type[PersonPreprocessed] | type[PartyPreprocessed],
        conditions: list[Any],
    ) -> list[Any]:
        if not conditions:
            return []
        query = select(model).where(or_(*conditions)).order_by(model.Preprocessed_ID)
        return list(self.db.scalars(query).unique())

    def _record_value(self, record: Any, field_name: str) -> Any:
        if isinstance(record, dict):
            return record.get(field_name)
        return getattr(record, field_name, None)

    def _prefix(self, value: Any, length: int = 4) -> str | None:
        if not self._is_present(value):
            return None
        normalized = str(value).strip()
        if len(normalized) < 3:
            return None
        return normalized[:length]

    def _is_present(self, value: Any) -> bool:
        return value is not None and str(value).strip() != ""
