"""Logika biznesowa warstwy."""
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.layers.ingestion.repository import IngestionRepository
from app.layers.ingestion.schemas import RawLoadResponse


SUPPORTED_FILE_TYPES = {"csv", "json", "xml", "xlsx"}
SUPPORTED_SOURCE_SYSTEMS = {
    "CEIDG",
    "KRS",
    "REGON",
    "VAT",
    "PESEL",
    "GLEIF_LEVEL1",
    "GLEIF_LEVEL2",
    "KNF_REJESTR_FIRM_INWESTYCYJNYCH",
    "KNF_REJESTR_DOSTAWCOW_I_WYDAWCOW_PIENIADZA_ELEKTRONICZNEGO",
    "KNF_REJESTR_POSREDNIKOW_UBEZPIECZENIOWYCH_AGENT",
    "KNF_REJESTR_POSREDNIKOW_UBEZPIECZENIOWYCH_PRACOWNIK_AGENTA",
}


class UnsupportedFileTypeError(ValueError):
    pass

class UnsupportedSourceSystemError(ValueError):
    pass


class InvalidFileContentError(ValueError):
    pass


def _get_file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_FILE_TYPES:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{suffix}'. Supported types: {', '.join(sorted(SUPPORTED_FILE_TYPES))}."
        )
    return suffix


def _validate_source_system_code(source_system_code: str) -> str:
    normalized = source_system_code.strip().upper()
    if normalized not in SUPPORTED_SOURCE_SYSTEMS:
        raise UnsupportedSourceSystemError(
            f"Unsupported source system '{source_system_code}'."
        )
    return normalized


def _validate_and_count_records(file_type: str, content: bytes) -> int | None:
    if not content:
        raise InvalidFileContentError("Uploaded file is empty.")

    if file_type == "csv":
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            raise InvalidFileContentError("CSV file has no rows.")
        return max(len(rows) - 1, 0)

    if file_type == "json":
        parsed = json.loads(content.decode("utf-8-sig"))
        if isinstance(parsed, list):
            return len(parsed)
        if isinstance(parsed, dict):
            return 1
        raise InvalidFileContentError("JSON root must be an object or an array.")

    if file_type == "xml":
        root = ElementTree.fromstring(content)
        return len(list(root))

    if file_type == "xlsx":
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
                raise InvalidFileContentError("Invalid XLSX file.")
        return None

    return None


def import_raw_file(
    db: Session,
    filename: str,
    content: bytes,
    source_system_code: str,
    created_by: str | None = None,
) -> RawLoadResponse:
    source_system_code = _validate_source_system_code(source_system_code)
    repo = IngestionRepository(db)
    batch = None
    process_log = None

    try:
        file_type = _get_file_type(filename)
        records_in = _validate_and_count_records(file_type, content)

        source = repo.get_or_create_source_system(source_system_code)
        batch = repo.create_import_batch(source.SourceSystem_ID, created_by)
        batch = repo.update_import_batch_status(batch, "PROCESSING")

        process_log = repo.create_process_log(batch.ImportBatch_ID)

        file_hash = hashlib.sha256(content).hexdigest()
        raw_file = repo.insert_raw_file(
            import_batch_id=batch.ImportBatch_ID,
            file_name=filename,
            file_type=file_type.upper(),
            file_size=len(content),
            file_hash=file_hash,
            file_content=content,
        )

        repo.finish_process_log(
            process_log,
            status="SUCCESS",
            raw_file_id=raw_file.RawFile_ID,
            records_in=records_in,
            records_out=records_in,
        )
        batch = repo.update_import_batch_status(batch, "RAW_LOADED", finish=True)

        return RawLoadResponse(
            import_batch_id=batch.ImportBatch_ID,
            raw_file_id=raw_file.RawFile_ID,
            file_name=raw_file.File_Name,
            file_type=raw_file.File_Type,
            file_size=raw_file.File_Size,
            file_hash=raw_file.File_Hash,
            records_in=records_in,
            import_status=batch.Import_Status,
        )

    except IntegrityError as exc:
        db.rollback()
        error_message = "File with this hash already exists."

        if process_log is not None:
            repo.finish_process_log(process_log, status="FAILED", error_message=error_message)
        if batch is not None:
            repo.update_import_batch_status(batch, "FAILED", error_message=error_message, finish=True)

        raise InvalidFileContentError(error_message) from exc

    except Exception as exc:
        db.rollback()
        error_message = str(exc)

        if process_log is not None:
            repo.finish_process_log(process_log, status="FAILED", error_message=error_message)
        if batch is not None:
            repo.update_import_batch_status(batch, "FAILED", error_message=error_message, finish=True)

        raise
