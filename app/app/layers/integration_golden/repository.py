"""Dostep do danych dla warstwy integration_golden."""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.layers.integration_golden.models import (
    DimAddress,
    DimAddressType,
    DimIdentityType,
    DimParty,
    DimPerson,
    EntityGroupMemberRecord,
    EntityGroupRecord,
    FactlessPartyAddress,
    FactlessPartyIdentities,
    FactlessPersonAddress,
    JaroWinklerCandidateRecord,
    MatchCandidateRecord,
)
from app.layers.ingestion.models import ImportBatch, ProcessLog, RawFile, SourceSystem
from app.layers.preprocessing.models import PartyPreprocessed, PersonPreprocessed
from app.layers.staging_validation.mapper import normalize_entity_type


class IntegrationGoldenRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_entity_groups(self, entity_type: str) -> list[EntityGroupRecord]:
        entity_type = normalize_entity_type(entity_type)
        query = (
            select(EntityGroupRecord)
            .where(EntityGroupRecord.Entity_Type == entity_type)
            .order_by(EntityGroupRecord.Entity_Group_ID)
        )
        return list(self.db.scalars(query))

    def get_entity_groups_for_raw_file(
        self,
        entity_type: str,
        raw_file_id: int,
    ) -> list[EntityGroupRecord]:
        entity_type = normalize_entity_type(entity_type)
        model = PersonPreprocessed if entity_type == "PERSON" else PartyPreprocessed
        member_preprocessed_id = (
            EntityGroupMemberRecord.Person_Preprocessed_ID
            if entity_type == "PERSON"
            else EntityGroupMemberRecord.Party_Preprocessed_ID
        )
        query = (
            select(EntityGroupRecord)
            .join(
                EntityGroupMemberRecord,
                and_(
                    EntityGroupMemberRecord.Entity_Group_ID == EntityGroupRecord.Entity_Group_ID,
                    EntityGroupMemberRecord.Entity_Type == EntityGroupRecord.Entity_Type,
                ),
            )
            .join(model, model.Preprocessed_ID == member_preprocessed_id)
            .where(EntityGroupRecord.Entity_Type == entity_type)
            .where(EntityGroupMemberRecord.Entity_Type == entity_type)
            .where(model.RawFile_ID == raw_file_id)
            .distinct()
            .order_by(EntityGroupRecord.Entity_Group_ID)
        )
        return list(self.db.scalars(query))

    def get_import_batch_id_for_raw_file(self, raw_file_id: int) -> int:
        import_batch_id = self.db.scalar(
            select(RawFile.ImportBatch_ID).where(RawFile.RawFile_ID == raw_file_id)
        )
        if import_batch_id is None:
            raise ValueError(f"RawFile_ID={raw_file_id} not found.")
        return int(import_batch_id)

    def create_golden_load_process_log(
        self,
        import_batch_id: int,
        raw_file_id: int | None,
    ) -> ProcessLog:
        log = ProcessLog(
            ImportBatch_ID=import_batch_id,
            RawFile_ID=raw_file_id,
            Step_Name="GOLDEN_LOAD",
            Step_Status="STARTED",
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def finish_process_log(
        self,
        log: ProcessLog,
        status: str,
        records_in: int | None = None,
        records_out: int | None = None,
        error_message: str | None = None,
    ) -> ProcessLog:
        log.Step_Status = status
        log.Records_In = records_in
        log.Records_Out = records_out
        log.Error_Message = error_message
        log.Ended_At = datetime.utcnow()
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_entity_group_members(
        self,
        entity_type: str,
        entity_group_id: int,
    ) -> list[EntityGroupMemberRecord]:
        entity_type = normalize_entity_type(entity_type)
        query = (
            select(EntityGroupMemberRecord)
            .where(EntityGroupMemberRecord.Entity_Type == entity_type)
            .where(EntityGroupMemberRecord.Entity_Group_ID == entity_group_id)
            .order_by(EntityGroupMemberRecord.Preprocessed_ID)
        )
        return list(self.db.scalars(query))

    def get_preprocessed_records_by_ids(
        self,
        entity_type: str,
        preprocessed_ids: list[int],
    ) -> list[Any]:
        entity_type = normalize_entity_type(entity_type)
        if not preprocessed_ids:
            return []
        model = PersonPreprocessed if entity_type == "PERSON" else PartyPreprocessed
        query = (
            select(model)
            .where(model.Preprocessed_ID.in_(preprocessed_ids))
            .order_by(model.Preprocessed_ID)
        )
        return list(self.db.scalars(query))

    def get_source_metadata_for_import_batch(
        self,
        import_batch_id: int,
    ) -> tuple[str | None, int | float | None, Any]:
        row = self.db.execute(
            select(
                SourceSystem.SourceSystem_Code,
                SourceSystem.Trust_Level,
                ImportBatch.Import_Start_At,
            )
            .join(SourceSystem, SourceSystem.SourceSystem_ID == ImportBatch.SourceSystem_ID)
            .where(ImportBatch.ImportBatch_ID == import_batch_id)
        ).first()
        if row is None:
            return None, None, None
        return row[0], row[1], row[2]

    def get_identity_type_by_name(self, identity_type_name: str) -> DimIdentityType | None:
        return self.db.scalar(
            select(DimIdentityType).where(
                DimIdentityType.IdentityType_Name == identity_type_name
            )
        )

    def get_address_type_by_name(self, address_type_name: str) -> DimAddressType | None:
        return self.db.scalar(
            select(DimAddressType).where(
                DimAddressType.AddressType_Name == address_type_name
            )
        )

    def find_address(
        self,
        *,
        street: str | None = None,
        building_number: str | None = None,
        apartment_number: str | None = None,
        city: str | None = None,
        postal_city: str | None = None,
        postal_code: str | None = None,
        district: str | None = None,
        province: str | None = None,
        country: str | None = None,
    ) -> DimAddress | None:
        if not any(
            self._is_present(value)
            for value in (
                street,
                building_number,
                apartment_number,
                city,
                postal_city,
                postal_code,
                district,
                province,
                country,
            )
        ):
            return None

        query = select(DimAddress).where(
            DimAddress.Street == street,
            DimAddress.Building_Number == building_number,
            DimAddress.Apartment_Number == apartment_number,
            DimAddress.City == city,
            DimAddress.Postal_City == postal_city,
            DimAddress.Postal_Code == postal_code,
            DimAddress.District == district,
            DimAddress.Province == province,
            DimAddress.Country == country,
        )
        return self.db.scalar(query)

    def get_or_create_address(self, **address_fields: Any) -> DimAddress | None:
        existing = self.find_address(**address_fields)
        if existing is not None:
            return existing
        if not any(self._is_present(value) for value in address_fields.values()):
            return None
        address = DimAddress(
            Street=address_fields.get("street"),
            Building_Number=address_fields.get("building_number"),
            Apartment_Number=address_fields.get("apartment_number"),
            City=address_fields.get("city"),
            Postal_City=address_fields.get("postal_city"),
            Postal_Code=address_fields.get("postal_code"),
            District=address_fields.get("district"),
            Province=address_fields.get("province"),
            Country=address_fields.get("country"),
        )
        self.db.add(address)
        self.db.flush()
        return address

    def find_person_by_identity(
        self,
        *,
        pesel: str | None = None,
        serial_number_id_card: str | None = None,
        serial_number_passport: str | None = None,
    ) -> DimPerson | None:
        conditions = []
        if self._is_present(pesel):
            conditions.append(DimPerson.PESEL == pesel)
        if self._is_present(serial_number_id_card):
            conditions.append(DimPerson.Serial_Number_ID_Card == serial_number_id_card)
        if self._is_present(serial_number_passport):
            conditions.append(DimPerson.Serial_Number_Passport == serial_number_passport)
        if not conditions:
            return None
        query = select(DimPerson).where(or_(*conditions)).order_by(DimPerson.Person_ID)
        return self.db.scalar(query)

    def create_person(self, **person_fields: Any) -> DimPerson:
        person = DimPerson(**self._filter_allowed_fields(DimPerson, person_fields))
        self.db.add(person)
        self.db.flush()
        return person

    def update_person(self, person: DimPerson, **person_fields: Any) -> DimPerson:
        for field_name, value in self._filter_allowed_fields(DimPerson, person_fields).items():
            setattr(person, field_name, value)
        self.db.flush()
        return person

    def find_party_by_identity(self, **identity_values: Any) -> DimParty | None:
        conditions = []
        for identity_type_name, identity_value in identity_values.items():
            if not self._is_present(identity_value):
                continue
            conditions.append(
                and_(
                    DimIdentityType.IdentityType_Name == identity_type_name,
                    FactlessPartyIdentities.Identity_Value == identity_value,
                )
            )
        if not conditions:
            return None

        query = (
            select(DimParty)
            .join(
                FactlessPartyIdentities,
                FactlessPartyIdentities.Party_ID == DimParty.Party_ID,
            )
            .join(
                DimIdentityType,
                DimIdentityType.IdentityType_ID == FactlessPartyIdentities.IdentityType_ID,
            )
            .where(or_(*conditions))
            .order_by(DimParty.Party_ID)
        )
        return self.db.scalars(query).first()

    def create_party(self, **party_fields: Any) -> DimParty:
        party = DimParty(**self._filter_allowed_fields(DimParty, party_fields))
        self.db.add(party)
        self.db.flush()
        return party

    def update_party(self, party: DimParty, **party_fields: Any) -> DimParty:
        for field_name, value in self._filter_allowed_fields(DimParty, party_fields).items():
            setattr(party, field_name, value)
        self.db.flush()
        return party

    def ensure_party_identity(
        self,
        *,
        party_id: int,
        identity_type_id: int,
        identity_value: str,
        is_valid: bool | None = None,
        match_confidence: float | None = None,
        valid_from: Any = None,
        valid_to: Any = None,
    ) -> FactlessPartyIdentities:
        existing = self.db.scalar(
            select(FactlessPartyIdentities).where(
                FactlessPartyIdentities.IdentityType_ID == identity_type_id,
                FactlessPartyIdentities.Identity_Value == identity_value,
            )
        )
        if existing is not None:
            existing.Party_ID = party_id
            existing.Is_Valid = is_valid
            existing.Match_Confidence = match_confidence
            existing.Valid_From = valid_from
            existing.Valid_To = valid_to
            self.db.flush()
            return existing

        identity = FactlessPartyIdentities(
            Party_ID=party_id,
            IdentityType_ID=identity_type_id,
            Identity_Value=identity_value,
            Is_Valid=is_valid,
            Match_Confidence=match_confidence,
            Valid_From=valid_from,
            Valid_To=valid_to,
        )
        self.db.add(identity)
        self.db.flush()
        return identity

    def ensure_person_address_link(
        self,
        *,
        person_id: int,
        address_id: int,
        address_type_id: int,
        valid_from: Any = None,
        valid_to: Any = None,
    ) -> FactlessPersonAddress:
        existing = self.db.scalar(
            select(FactlessPersonAddress).where(
                FactlessPersonAddress.Person_ID == person_id,
                FactlessPersonAddress.Address_ID == address_id,
                FactlessPersonAddress.AddressType_ID == address_type_id,
                FactlessPersonAddress.Valid_From == valid_from,
                FactlessPersonAddress.Valid_To == valid_to,
            )
        )
        if existing is not None:
            return existing
        link = FactlessPersonAddress(
            Person_ID=person_id,
            Address_ID=address_id,
            AddressType_ID=address_type_id,
            Valid_From=valid_from,
            Valid_To=valid_to,
        )
        self.db.add(link)
        self.db.flush()
        return link

    def ensure_party_address_link(
        self,
        *,
        party_id: int,
        address_id: int,
        address_type_id: int,
        valid_from: Any = None,
        valid_to: Any = None,
    ) -> FactlessPartyAddress:
        existing = self.db.scalar(
            select(FactlessPartyAddress).where(
                FactlessPartyAddress.Party_ID == party_id,
                FactlessPartyAddress.Address_ID == address_id,
                FactlessPartyAddress.AddressType_ID == address_type_id,
                FactlessPartyAddress.Valid_From == valid_from,
                FactlessPartyAddress.Valid_To == valid_to,
            )
        )
        if existing is not None:
            return existing
        link = FactlessPartyAddress(
            Party_ID=party_id,
            Address_ID=address_id,
            AddressType_ID=address_type_id,
            Valid_From=valid_from,
            Valid_To=valid_to,
        )
        self.db.add(link)
        self.db.flush()
        return link

    def commit(self) -> None:
        self.db.commit()

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
            delete(JaroWinklerCandidateRecord)
            .where(JaroWinklerCandidateRecord.Entity_Type == entity_type)
            .where(JaroWinklerCandidateRecord.RawFile_ID == raw_file_id)
        )
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

    def get_levenshtein_candidates(
        self,
        entity_type: str,
        raw_file_id: int | None = None,
    ) -> list[MatchCandidateRecord]:
        entity_type = normalize_entity_type(entity_type)
        query = (
            select(MatchCandidateRecord)
            .where(MatchCandidateRecord.Entity_Type == entity_type)
            .order_by(MatchCandidateRecord.Score.desc())
        )
        if raw_file_id is not None:
            query = query.where(MatchCandidateRecord.RawFile_ID == raw_file_id)
        return list(self.db.scalars(query))

    def get_preprocessed_record_by_id(self, entity_type: str, preprocessed_id: int) -> Any | None:
        entity_type = normalize_entity_type(entity_type)
        model = PersonPreprocessed if entity_type == "PERSON" else PartyPreprocessed
        return self.db.get(model, preprocessed_id)

    def replace_jaro_winkler_candidates(
        self,
        entity_type: str,
        raw_file_id: int | None,
        candidates: list[Any],
    ) -> int:
        entity_type = normalize_entity_type(entity_type)
        self.db.execute(
            delete(JaroWinklerCandidateRecord)
            .where(JaroWinklerCandidateRecord.Entity_Type == entity_type)
            .where(JaroWinklerCandidateRecord.RawFile_ID == raw_file_id)
        )

        entities = [
            JaroWinklerCandidateRecord(
                Levenshtein_Candidate_ID=candidate.levenshtein_candidate_id,
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
                Levenshtein_Score=candidate.levenshtein_score,
                JaroWinkler_Score=candidate.jaro_winkler_score,
                Decision=str(candidate.decision.value),
                Strong_Match_Fields_JSON=json.dumps(list(candidate.strong_match_fields), ensure_ascii=False),
                Conflict_Fields_JSON=json.dumps(list(candidate.conflict_fields), ensure_ascii=False),
                Text_Match_Fields_JSON=json.dumps(list(candidate.text_match_fields), ensure_ascii=False),
            )
            for candidate in candidates
        ]
        self.db.add_all(entities)
        self.db.commit()
        return len(entities)

    def get_jaro_winkler_candidates(self, entity_type: str) -> list[JaroWinklerCandidateRecord]:
        entity_type = normalize_entity_type(entity_type)
        query = (
            select(JaroWinklerCandidateRecord)
            .where(JaroWinklerCandidateRecord.Entity_Type == entity_type)
            .where(JaroWinklerCandidateRecord.Decision == "AUTO_MERGE")
            .order_by(JaroWinklerCandidateRecord.Match_Candidate_JaroWinkler_ID)
        )
        return list(self.db.scalars(query))

    def replace_entity_groups(self, entity_type: str, groups: list[Any]) -> tuple[int, int]:
        entity_type = normalize_entity_type(entity_type)
        group_keys = {group.group_key for group in groups}
        existing_groups = list(
            self.db.scalars(
                select(EntityGroupRecord).where(EntityGroupRecord.Entity_Type == entity_type)
            )
        )
        groups_by_key = {group.Group_Key: group for group in existing_groups}

        self.db.execute(
            delete(EntityGroupMemberRecord).where(EntityGroupMemberRecord.Entity_Type == entity_type)
        )
        for stale_group in existing_groups:
            if stale_group.Group_Key not in group_keys:
                self.db.delete(stale_group)

        for group in groups:
            group_record = groups_by_key.get(group.group_key)
            if group_record is None:
                group_record = EntityGroupRecord(
                    Entity_Type=entity_type,
                    Group_Key=group.group_key,
                )
                self.db.add(group_record)
                self.db.flush()
            else:
                group_record.Updated_At = func.now()
            for preprocessed_id in group.member_preprocessed_ids:
                self.db.add(
                    EntityGroupMemberRecord(
                        Entity_Group_ID=group_record.Entity_Group_ID,
                        Entity_Type=entity_type,
                        Preprocessed_ID=preprocessed_id,
                        Person_Preprocessed_ID=preprocessed_id if entity_type == "PERSON" else None,
                        Party_Preprocessed_ID=preprocessed_id if entity_type == "PARTY" else None,
                    )
                )

        self.db.commit()
        return len(groups), sum(len(group.member_preprocessed_ids) for group in groups)

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

    def _filter_allowed_fields(self, model: Any, values: dict[str, Any]) -> dict[str, Any]:
        allowed_fields = set(model.__table__.columns.keys())
        return {field_name: value for field_name, value in values.items() if field_name in allowed_fields}
