from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.layers.ingestion.models import ImportBatch, ProcessLog, RawFile, SourceSystem


class IngestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_source_system(self, code: str, name: str | None = None) -> SourceSystem:
        # Pobieramy albo tworzymy źródło, żeby raw-load działał także na świeżej bazie bez seeda
        source = self.db.scalar(
            select(SourceSystem).where(SourceSystem.SourceSystem_Code == code)
        )
        if source is not None:
            return source

        source = SourceSystem(
            SourceSystem_Code=code,
            SourceSystem_Name=name or code,
            Trust_Level=None,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def create_import_batch(self, source_system_id: int, created_by: str | None) -> ImportBatch:
        # Tworzymy batch jako NEW, żeby import miał identyfikator jeszcze przed etapem PROCESSING
        batch = ImportBatch(
            SourceSystem_ID=source_system_id,
            Import_Status="NEW",
            Created_By=created_by,
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def update_import_batch_status(
        self,
        batch: ImportBatch,
        status: str,
        error_message: str | None = None,
        finish: bool = False,
    ) -> ImportBatch:
        # Aktualizujemy status batcha, żeby kolejne warstwy wiedziały czy mogą pracować dalej
        batch.Import_Status = status
        batch.Error_Message = error_message
        if finish:
            batch.Import_End_At = datetime.utcnow()

        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def create_process_log(self, import_batch_id: int) -> ProcessLog:
        # Zakładamy log kroku, żeby było widać gdzie import się zaczął i gdzie ewentualnie stanął
        log = ProcessLog(
            ImportBatch_ID=import_batch_id,
            Step_Name="RAW_LOAD",
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
        raw_file_id: int | None = None,
        records_in: int | None = None,
        records_out: int | None = None,
        error_message: str | None = None,
    ) -> ProcessLog:
        # Domykamy log z licznikami, żeby odpowiedź API i diagnostyka pokazywały ten sam stan
        log.Step_Status = status
        log.RawFile_ID = raw_file_id
        log.Records_In = records_in
        log.Records_Out = records_out
        log.Error_Message = error_message
        log.Ended_At = datetime.utcnow()

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def insert_raw_file(
        self,
        import_batch_id: int,
        file_name: str,
        file_type: str,
        file_size: int,
        file_hash: str,
        file_content: bytes,
    ) -> RawFile:
        # Zapisujemy plik jako bajty, żeby staging czytał dokładnie tę wersję danych co raw-load
        raw_file = RawFile(
            ImportBatch_ID=import_batch_id,
            File_Name=file_name,
            File_Type=file_type,
            File_Size=file_size,
            File_Hash=file_hash,
            File_Content=file_content,
        )
        self.db.add(raw_file)
        self.db.commit()
        self.db.refresh(raw_file)
        return raw_file
