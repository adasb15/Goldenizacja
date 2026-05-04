import csv
import io
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from xml.etree import ElementTree

from app.layers.staging_validation.mapper import (
    MISSING_COLUMNS_KEY,
    PARTY_CANONICAL_COLUMNS,
    PERSON_CANONICAL_COLUMNS,
    UNRECOGNIZED_COLUMNS_KEY,
    map_records_to_canonical,
    normalize_entity_type,
)


SOURCE_RECORD_ID_CANDIDATES = (
    "Source_Record_ID",
    "source_record_id",
    "id",
    "ID",
    "firma.id",
    "numerKRS",
    "PESEL",
    "LEI",
)
SOURCE_RECORD_ID_CANDIDATE_KEYS = {
    candidate.strip().casefold()
    for candidate in SOURCE_RECORD_ID_CANDIDATES
}


class RawFileNotFoundError(ValueError):
    pass


class ImportBatchNotFoundError(ValueError):
    pass


class UnsupportedStagingFileTypeError(ValueError):
    pass


class InvalidRawFileContentError(ValueError):
    pass


class MissingColumnMappingError(ValueError):
    pass


@dataclass
class StagingLoadResult:
    import_batch_id: int
    raw_file_id: int
    entity_type: str
    records_in: int
    records_out: int
    import_status: str
    process_status: str
    missing_columns: dict[str, int]
    unrecognized_columns: dict[str, int]


def get_column_mapping(
    db: Any,
    source_system_id: int,
    entity_type: str,
    repo: Any | None = None,
) -> dict[str, str]:
    repo = repo or create_repository(db)
    return repo.get_column_mapping(source_system_id, entity_type)


def map_source_records_to_canonical(
    db: Any,
    source_system_id: int,
    entity_type: str,
    source_records: list[Mapping[str, Any]],
    repo: Any | None = None,
) -> list[dict[str, Any]]:
    mapping = get_column_mapping(db, source_system_id, entity_type, repo=repo)
    return map_records_to_canonical(source_records, mapping, entity_type)


def create_repository(db: Any) -> Any:
    from app.layers.staging_validation.repository import StagingValidationRepository

    return StagingValidationRepository(db)


def parse_raw_file_records(file_type: str, file_content: bytes | None) -> list[dict[str, Any]]:
    if not file_content:
        raise InvalidRawFileContentError("Raw file content is empty.")

    normalized_file_type = file_type.strip().upper()

    if normalized_file_type == "CSV":
        text = file_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise InvalidRawFileContentError("CSV file has no header row.")
        return [dict(row) for row in reader]

    if normalized_file_type == "JSON":
        parsed = json.loads(file_content.decode("utf-8-sig"))
        if isinstance(parsed, list):
            if not all(isinstance(record, Mapping) for record in parsed):
                raise InvalidRawFileContentError("JSON array must contain objects.")
            return [dict(record) for record in parsed]
        if isinstance(parsed, Mapping):
            return [dict(parsed)]
        raise InvalidRawFileContentError("JSON root must be an object or an array.")

    if normalized_file_type == "XLSX":
        return parse_xlsx_records(file_content)

    if normalized_file_type == "XML":
        return parse_xml_records(file_content)

    raise UnsupportedStagingFileTypeError(
        f"Unsupported staging file type '{file_type}'. Supported types: CSV, JSON, XLSX, XML."
    )


def parse_xlsx_records(file_content: bytes) -> list[dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise UnsupportedStagingFileTypeError(
            "XLSX staging load requires openpyxl to be installed."
        ) from exc

    try:
        workbook = load_workbook(
            filename=io.BytesIO(file_content),
            read_only=True,
            data_only=True,
        )
    except Exception as exc:
        raise InvalidRawFileContentError("Invalid XLSX file.") from exc

    try:
        sheet = workbook.active
        rows = [
            list(row)
            for row in sheet.iter_rows(values_only=True)
            if any(cell is not None and cell != "" for cell in row)
        ]
    finally:
        workbook.close()

    if not rows:
        raise InvalidRawFileContentError("XLSX file has no rows.")

    headers = [str(header).strip() if header is not None else "" for header in rows[0]]
    if not any(headers):
        raise InvalidRawFileContentError("XLSX header row is empty.")

    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            record[header] = row[index] if index < len(row) else None
        records.append(record)

    return records


def parse_xml_records(file_content: bytes) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(file_content)
    except ElementTree.ParseError as exc:
        raise InvalidRawFileContentError("Invalid XML file.") from exc

    records: list[dict[str, Any]] = []
    for record_element in root.findall(".//record"):
        record: dict[str, Any] = {}
        fields = list(record_element.findall("field"))

        if fields:
            for field in fields:
                field_name = field.attrib.get("name")
                if field_name:
                    record[field_name] = field.text or ""
        else:
            for child in list(record_element):
                record[child.tag] = child.text or ""

        if record:
            records.append(record)

    if not records:
        raise InvalidRawFileContentError("XML file has no record elements.")

    return records


def load_raw_file_to_staging(
    db: Any,
    raw_file_id: int,
    entity_type: str,
    repo: Any | None = None,
) -> StagingLoadResult:
    entity_type = normalize_entity_type(entity_type)
    repo = repo or create_repository(db)
    process_log = None
    batch = None

    try:
        raw_file = repo.get_raw_file(raw_file_id)
        if raw_file is None:
            raise RawFileNotFoundError(f"RawFile_ID={raw_file_id} does not exist.")

        batch = repo.get_import_batch(raw_file.ImportBatch_ID)
        if batch is None:
            raise ImportBatchNotFoundError(
                f"ImportBatch_ID={raw_file.ImportBatch_ID} does not exist."
            )

        batch = repo.update_import_batch_status(batch, "PROCESSING")
        process_log = repo.create_staging_process_log(
            import_batch_id=batch.ImportBatch_ID,
            raw_file_id=raw_file.RawFile_ID,
        )

        source_records = parse_raw_file_records(raw_file.File_Type, raw_file.File_Content)
        mapping = repo.get_column_mapping(batch.SourceSystem_ID, entity_type)
        if not mapping:
            raise MissingColumnMappingError(
                f"No ColumnMapping rows for SourceSystem_ID={batch.SourceSystem_ID} and Entity_Type={entity_type}."
            )

        canonical_records = map_records_to_canonical(source_records, mapping, entity_type)
        staging_records = [
            build_staging_record(
                canonical_record=canonical_record,
                source_record=source_record,
                import_batch_id=batch.ImportBatch_ID,
                raw_file_id=raw_file.RawFile_ID,
                entity_type=entity_type,
                row_number=row_number,
            )
            for row_number, (canonical_record, source_record) in enumerate(
                zip(canonical_records, source_records),
                start=1,
            )
        ]

        if entity_type == "PERSON":
            records_out = repo.insert_person_staging_records(staging_records)
        else:
            records_out = repo.insert_party_staging_records(staging_records)

        repo.finish_process_log(
            process_log,
            status="SUCCESS",
            records_in=len(source_records),
            records_out=records_out,
        )
        batch = repo.update_import_batch_status(batch, "STAGING_LOADED", finish=True)

        return StagingLoadResult(
            import_batch_id=batch.ImportBatch_ID,
            raw_file_id=raw_file.RawFile_ID,
            entity_type=entity_type,
            records_in=len(source_records),
            records_out=records_out,
            import_status=batch.Import_Status,
            process_status="SUCCESS",
            missing_columns=count_report_columns(canonical_records, MISSING_COLUMNS_KEY),
            unrecognized_columns=count_report_columns(canonical_records, UNRECOGNIZED_COLUMNS_KEY),
        )

    except Exception as exc:
        error_message = str(exc)
        if hasattr(repo, "rollback"):
            repo.rollback()
        if process_log is not None:
            repo.finish_process_log(process_log, status="FAILED", error_message=error_message)
        if batch is not None:
            repo.update_import_batch_status(
                batch,
                "FAILED",
                error_message=error_message,
                finish=True,
            )
        raise


def build_staging_record(
    canonical_record: Mapping[str, Any],
    source_record: Mapping[str, Any],
    import_batch_id: int,
    raw_file_id: int,
    entity_type: str,
    row_number: int,
) -> dict[str, Any]:
    canonical_columns = (
        PERSON_CANONICAL_COLUMNS
        if entity_type == "PERSON"
        else PARTY_CANONICAL_COLUMNS
    )
    staging_record = {
        column: canonical_record.get(column)
        for column in canonical_columns
        if column not in {MISSING_COLUMNS_KEY, UNRECOGNIZED_COLUMNS_KEY}
    }
    staging_record["ImportBatch_ID"] = import_batch_id
    staging_record["RawFile_ID"] = raw_file_id
    staging_record["Source_Record_ID"] = detect_source_record_id(
        canonical_record,
        source_record,
        row_number,
    )

    if entity_type == "PERSON":
        staging_record["Birth_Date"] = parse_date_value(staging_record.get("Birth_Date"))
    else:
        staging_record["Establishment_Date"] = parse_date_value(
            staging_record.get("Establishment_Date")
        )

    return staging_record


def detect_source_record_id(
    canonical_record: Mapping[str, Any],
    source_record: Mapping[str, Any],
    row_number: int,
) -> str:
    canonical_source_record_id = canonical_record.get("Source_Record_ID")
    if canonical_source_record_id not in (None, ""):
        return str(canonical_source_record_id)

    lookup = {
        str(column_name).strip().casefold(): value
        for column_name, value in source_record.items()
    }
    for candidate in SOURCE_RECORD_ID_CANDIDATES:
        value = lookup.get(candidate.strip().casefold())
        if value not in (None, ""):
            return str(value)

    return str(row_number)


def parse_date_value(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def count_report_columns(
    canonical_records: list[Mapping[str, Any]],
    report_key: str,
) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in canonical_records:
        for column in record.get(report_key, []):
            column_name = str(column)
            if (
                report_key == UNRECOGNIZED_COLUMNS_KEY
                and column_name.strip().casefold() in SOURCE_RECORD_ID_CANDIDATE_KEYS
            ):
                continue
            counter.update([column_name])
    return dict(counter)
