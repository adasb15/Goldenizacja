"""Logika biznesowa warstwy."""
import csv
import hashlib
import io
import json
from pathlib import Path
from xml.etree import ElementTree
from openpyxl import load_workbook

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.layers.ingestion.repository import IngestionRepository
from app.layers.ingestion.schemas import RawLoadResponse


SUPPORTED_FILE_TYPES = {"csv", "json", "xml", "xlsx"}
SUPPORTED_SOURCE_SYSTEMS = {
    "CEIDG": "Centralna Ewidencja i Informacja o Dzialalnosci Gospodarczej",
    "KRS": "Krajowy Rejestr Sadowy",
    "REGON": "Rejestr REGON",
    "VAT": "Wykaz podatnikow VAT",
    "PESEL": "Rejestr PESEL",
    "KNF_AGENT": "KNF Rejestr posrednikow ubezpieczeniowych - agent",
    "KNF_PRACOWNIK_AGENTA": "KNF Rejestr posrednikow ubezpieczeniowych - pracownik agenta",
    "KNF_FIRMY_INWESTYCYJNE": "KNF Rejestr firm inwestycyjnych",
    "KNF_PIENIADZ_ELEKTRONICZNY": "KNF Rejestr dostawcow i wydawcow pieniadza elektronicznego",
    "GLEIF": "GLEIF"
}



class UnsupportedFileTypeError(ValueError):
    pass

class UnsupportedSourceSystemError(ValueError):
    pass


class InvalidFileContentError(ValueError):
    pass


def _get_file_type(filename: str) -> str:
    # Wyciągamy typ z rozszerzenia, żeby zapisać go w RAW i dobrać późniejszy parser stagingu
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_FILE_TYPES:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{suffix}'. Supported types: {', '.join(sorted(SUPPORTED_FILE_TYPES))}."
        )
    return suffix


def _validate_source_system_code(source_system_code: str) -> str:
    # Normalizujemy kod źródła, żeby użytkownik w Postmanie nie musiał pilnować wielkości liter
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
        # Liczymy rekordy CSV bez nagłówka, żeby raw-load raportował rozmiar paczki przed mapowaniem
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            raise InvalidFileContentError("CSV file has no rows.")
        return max(len(rows) - 1, 0)

    if file_type == "json":
        # Obsługujemy obiekt i listę JSON, żeby raw-load przyjął pojedynczy rekord albo paczkę
        parsed = json.loads(content.decode("utf-8-sig"))
        if isinstance(parsed, list):
            return len(parsed)
        if isinstance(parsed, dict):
            return 1
        raise InvalidFileContentError("JSON root must be an object or an array.")

    if file_type == "xml":
        # Liczymy elementy XML pierwszego poziomu, żeby RAW miał szybki licznik przed dokładnym stagingiem
        root = ElementTree.fromstring(content)
        return len(list(root))

    if file_type == "xlsx":
        try:
            # Liczymy niepuste wiersze XLSX, żeby formatowanie arkusza nie zawyżało liczby rekordów
            workbook = load_workbook(
                filename=io.BytesIO(content),
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            raise InvalidFileContentError("Invalid XLSX file.") from exc

        sheet = workbook.active
        row_count = 0

        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                row_count += 1

        workbook.close()

        if row_count == 0:
            raise InvalidFileContentError("XLSX file has no rows.")

        return max(row_count - 1, 0)

    return None


def import_raw_file(
    db: Session,
    filename: str,
    content: bytes,
    source_system_code: str,
    created_by: str | None = None,
) -> RawLoadResponse:
    # Importujemy plik do RAW bez czyszczenia, żeby zachować oryginalne dane dla kolejnych warstw
    source_system_code = _validate_source_system_code(source_system_code)
    repo = IngestionRepository(db)
    batch = None
    process_log = None

    try:
        file_type = _get_file_type(filename)
        records_in = _validate_and_count_records(file_type, content)

        source = repo.get_or_create_source_system(
            source_system_code,
            SUPPORTED_SOURCE_SYSTEMS[source_system_code],
        )
        # Tworzymy batch przed zapisem pliku, żeby każdy błąd miał wspólny kontekst importu
        batch = repo.create_import_batch(source.SourceSystem_ID, created_by)
        batch = repo.update_import_batch_status(batch, "PROCESSING")

        process_log = repo.create_process_log(batch.ImportBatch_ID)

        # Liczymy hash pliku, żeby zablokować przypadkowy duplikat identycznego RAW
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
        # Zamieniamy konflikt hasha na błąd walidacji, żeby użytkownik wiedział że plik już istnieje
        error_message = "File with this hash already exists."

        if process_log is not None:
            repo.finish_process_log(process_log, status="FAILED", error_message=error_message)
        if batch is not None:
            repo.update_import_batch_status(batch, "FAILED", error_message=error_message, finish=True)

        raise InvalidFileContentError(error_message) from exc

    except Exception as exc:
        db.rollback()
        # Domykamy logi przy błędzie technicznym, żeby baza nie zostawiała importu w PROCESSING
        error_message = str(exc)

        if process_log is not None:
            repo.finish_process_log(process_log, status="FAILED", error_message=error_message)
        if batch is not None:
            repo.update_import_batch_status(batch, "FAILED", error_message=error_message, finish=True)

        raise
