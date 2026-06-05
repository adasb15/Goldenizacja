from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.layers.ingestion.models import ProcessLog
from app.layers.preprocessing.models import PartyPreprocessed, PersonPreprocessed
from app.layers.staging_validation.mapper import normalize_entity_type
from app.layers.staging_validation.models import PartyStaging, PersonStaging
from app.layers.validation.models import ValidationResult


class ValidationRepository:
    def __init__(self, db: Session):
        self.db = db

    def rollback(self) -> None:
        self.db.rollback()

    def get_records_for_validation(self, raw_file_id: int, entity_type: str) -> list[tuple[Any, Any]]:
        entity_type = normalize_entity_type(entity_type)
        if entity_type == "PERSON":
            statement = (
                select(PersonStaging, PersonPreprocessed)
                .join(PersonPreprocessed, PersonPreprocessed.Staging_ID == PersonStaging.Staging_ID)
                .where(PersonStaging.RawFile_ID == raw_file_id)
                .order_by(PersonStaging.Staging_ID)
            )
        else:
            statement = (
                select(PartyStaging, PartyPreprocessed)
                .join(PartyPreprocessed, PartyPreprocessed.Staging_ID == PartyStaging.Staging_ID)
                .where(PartyStaging.RawFile_ID == raw_file_id)
                .order_by(PartyStaging.Staging_ID)
            )

        return list(self.db.execute(statement).all())

    def delete_validation_results_for_raw_file(self, raw_file_id: int, entity_type: str) -> None:
        entity_type = normalize_entity_type(entity_type)
        self.db.execute(
            delete(ValidationResult)
            .where(ValidationResult.RawFile_ID == raw_file_id)
            .where(ValidationResult.Entity_Type == entity_type)
        )
        self.db.commit()

    def create_validation_process_log(
        self,
        import_batch_id: int,
        raw_file_id: int,
    ) -> ProcessLog:
        log = ProcessLog(
            ImportBatch_ID=import_batch_id,
            RawFile_ID=raw_file_id,
            Step_Name="VALIDATION",
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

    def insert_validation_results(self, records: list[dict[str, Any]]) -> int:
        entities = [ValidationResult(**record) for record in records]
        self.db.add_all(entities)
        self.db.commit()
        return len(entities)
