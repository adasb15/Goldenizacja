from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.layers.ingestion.models import ImportBatch, ProcessLog, RawFile
from app.layers.staging_validation.models import ColumnMapping, PartyStaging, PersonStaging


SUPPORTED_ENTITY_TYPES = {"PERSON", "PARTY"}


class UnsupportedEntityTypeError(ValueError):
    pass


def normalize_entity_type(entity_type: str) -> str:
    normalized = entity_type.strip().upper()
    if normalized not in SUPPORTED_ENTITY_TYPES:
        raise UnsupportedEntityTypeError(
            f"Unsupported entity type '{entity_type}'. Supported types: PERSON, PARTY."
        )
    return normalized


class StagingValidationRepository:
    def __init__(self, db: Session):
        self.db = db

    def rollback(self) -> None:
        self.db.rollback()

    def get_column_mappings(
        self,
        source_system_id: int,
        entity_type: str,
    ) -> list[ColumnMapping]:
        entity_type = normalize_entity_type(entity_type)
        return list(
            self.db.scalars(
                select(ColumnMapping)
                .where(ColumnMapping.SourceSystem_ID == source_system_id)
                .where(ColumnMapping.Entity_Type == entity_type)
                .order_by(ColumnMapping.ColumnMapping_ID)
            )
        )

    def get_column_mapping(
        self,
        source_system_id: int,
        entity_type: str,
    ) -> dict[str, str]:
        mappings = self.get_column_mappings(source_system_id, entity_type)
        return {
            row.Source_Column_Name: row.Canonical_Column_Name
            for row in mappings
        }

    def get_raw_file(self, raw_file_id: int) -> RawFile | None:
        return self.db.get(RawFile, raw_file_id)

    def get_import_batch(self, import_batch_id: int) -> ImportBatch | None:
        return self.db.get(ImportBatch, import_batch_id)

    def count_staging_records_for_raw_file(self, raw_file_id: int, entity_type: str) -> int:
        entity_type = normalize_entity_type(entity_type)
        model = PersonStaging if entity_type == "PERSON" else PartyStaging
        # Liczymy rekordy staging po raw_file_id, żeby zablokować duplikat tego samego ładowania
        return self.db.scalar(
            select(func.count()).select_from(model).where(model.RawFile_ID == raw_file_id)
        ) or 0

    def update_import_batch_status(
        self,
        batch: ImportBatch,
        status: str,
        error_message: str | None = None,
        finish: bool = False,
    ) -> ImportBatch:
        batch.Import_Status = status
        batch.Error_Message = error_message
        if finish:
            batch.Import_End_At = datetime.utcnow()

        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def create_staging_process_log(
        self,
        import_batch_id: int,
        raw_file_id: int,
    ) -> ProcessLog:
        log = ProcessLog(
            ImportBatch_ID=import_batch_id,
            RawFile_ID=raw_file_id,
            Step_Name="STAGING_LOAD",
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

    def insert_person_staging_records(self, records: list[dict[str, Any]]) -> int:
        entities = [PersonStaging(**record) for record in records]
        self.db.add_all(entities)
        self.db.commit()
        return len(entities)

    def insert_party_staging_records(self, records: list[dict[str, Any]]) -> int:
        entities = [PartyStaging(**record) for record in records]
        self.db.add_all(entities)
        self.db.commit()
        return len(entities)
