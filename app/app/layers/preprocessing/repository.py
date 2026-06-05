from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.layers.ingestion.models import ProcessLog
from app.layers.preprocessing.models import PartyPreprocessed, PersonPreprocessed
from app.layers.staging_validation.mapper import normalize_entity_type
from app.layers.staging_validation.models import PartyStaging, PersonStaging


class PreprocessingRepository:
    def __init__(self, db: Session):
        self.db = db

    def rollback(self) -> None:
        self.db.rollback()

    def get_staging_records(self, raw_file_id: int, entity_type: str) -> list[Any]:
        entity_type = normalize_entity_type(entity_type)
        model = PersonStaging if entity_type == "PERSON" else PartyStaging
        return list(
            self.db.scalars(
                select(model)
                .where(model.RawFile_ID == raw_file_id)
                .order_by(model.Staging_ID)
            )
        )

    def count_preprocessed_records_for_raw_file(self, raw_file_id: int, entity_type: str) -> int:
        entity_type = normalize_entity_type(entity_type)
        model = PersonPreprocessed if entity_type == "PERSON" else PartyPreprocessed
        return self.db.scalar(
            select(func.count()).select_from(model).where(model.RawFile_ID == raw_file_id)
        ) or 0

    def create_preprocessing_process_log(
        self,
        import_batch_id: int,
        raw_file_id: int,
    ) -> ProcessLog:
        log = ProcessLog(
            ImportBatch_ID=import_batch_id,
            RawFile_ID=raw_file_id,
            Step_Name="STANDARDIZATION",
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

    def insert_person_preprocessed_records(self, records: list[dict[str, Any]]) -> int:
        entities = [PersonPreprocessed(**record) for record in records]
        self.db.add_all(entities)
        self.db.commit()
        return len(entities)

    def insert_party_preprocessed_records(self, records: list[dict[str, Any]]) -> int:
        entities = [PartyPreprocessed(**record) for record in records]
        self.db.add_all(entities)
        self.db.commit()
        return len(entities)
