"""Logika biznesowa warstwy."""
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

try:
    from sqlalchemy.exc import IntegrityError
except ImportError:
    class IntegrityError(Exception):
        pass

from app.layers.ingestion.schemas import RawLoadResponse, RelationalQueryInfo


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
    "GLEIF": "GLEIF",
    "INSURANCE_CORE": "Oracle Insurance Core - relacyjne zrodlo przez ODBC",
}

INSURANCE_CORE_PARTY_MAIN_SQL = """
SELECT
    c.CLIENT_ID,
    c.CLIENT_NUMBER,
    c.CLIENT_TYPE,
    c.DISPLAY_NAME,
    c.SHORT_NAME,
    c.LEGAL_FORM,
    c.STATUS_CODE,
    c.OPENED_AT,
    c.CLOSED_AT,
    c.RISK_CLASS,
    c.INTERNAL_SEGMENT,
    b.CITY AS BRANCH_CITY,
    b.REGION_CODE AS BRANCH_REGION,
    nip.IDENTIFIER_VALUE AS TAX_NUMBER,
    regon.IDENTIFIER_VALUE AS NATIONAL_REGISTRY_NO,
    krs.IDENTIFIER_VALUE AS LEGAL_REGISTER_NO,
    addr.ADDRESS_LINE AS MAIN_ADDRESS_LINE,
    addr.CITY AS MAIN_CITY,
    addr.POSTAL_CODE AS MAIN_POSTAL_CODE,
    addr.COUNTRY AS MAIN_COUNTRY,
    email.CONTACT_VALUE AS MAIN_EMAIL,
    phone.CONTACT_VALUE AS MAIN_PHONE,
    iban.IBAN AS PRIMARY_IBAN,
    contracts.ACTIVE_CONTRACTS_COUNT,
    contracts.LATEST_CONTRACT_STATUS
FROM CLIENT_ACCOUNT c
LEFT JOIN BRANCH b
    ON b.BRANCH_ID = c.BRANCH_ID
LEFT JOIN CUSTOMER_IDENTIFIER nip
    ON nip.CLIENT_ID = c.CLIENT_ID
   AND nip.IDENTIFIER_TYPE = 'NIP'
LEFT JOIN CUSTOMER_IDENTIFIER regon
    ON regon.CLIENT_ID = c.CLIENT_ID
   AND regon.IDENTIFIER_TYPE = 'REGON'
LEFT JOIN CUSTOMER_IDENTIFIER krs
    ON krs.CLIENT_ID = c.CLIENT_ID
   AND krs.IDENTIFIER_TYPE = 'KRS'
LEFT JOIN CUSTOMER_ADDRESS addr
    ON addr.CLIENT_ID = c.CLIENT_ID
   AND addr.ADDRESS_TYPE = 'REGISTERED'
LEFT JOIN CLIENT_CONTACT_LOG email
    ON email.CLIENT_ID = c.CLIENT_ID
   AND email.CONTACT_KIND = 'EMAIL'
   AND email.IS_CONFIRMED = 1
LEFT JOIN CLIENT_CONTACT_LOG phone
    ON phone.CLIENT_ID = c.CLIENT_ID
   AND phone.CONTACT_KIND = 'PHONE'
   AND phone.IS_CONFIRMED = 1
LEFT JOIN PAYMENT_ACCOUNT iban
    ON iban.CLIENT_ID = c.CLIENT_ID
   AND iban.IS_ACTIVE = 1
LEFT JOIN (
    SELECT
        cp.CLIENT_ID,
        COUNT(*) AS ACTIVE_CONTRACTS_COUNT,
        MAX(co.CONTRACT_STATUS) AS LATEST_CONTRACT_STATUS
    FROM CONTRACT_PARTY cp
    JOIN CONTRACT co
        ON co.CONTRACT_ID = cp.CONTRACT_ID
    WHERE co.CONTRACT_STATUS = 'ACTIVE'
    GROUP BY cp.CLIENT_ID
) contracts
    ON contracts.CLIENT_ID = c.CLIENT_ID
WHERE c.CLIENT_TYPE = 'ORG'
"""

INSURANCE_CORE_PERSON_ROLES_SQL = """
SELECT
    ar.CLIENT_ID,
    ar.AGENT_FIRST_NAME,
    ar.AGENT_LAST_NAME,
    ar.AGENT_PESEL,
    ar.AGENT_LICENSE_NO,
    ar.ROLE_NAME,
    ar.VALID_FROM,
    ar.VALID_TO
FROM AGENT_ASSIGNMENT ar
"""

INSURANCE_CORE_RELATED_PARTIES_SQL = """
SELECT
    rc.PARENT_CLIENT_ID AS CLIENT_ID,
    child.CLIENT_NUMBER AS RELATED_CLIENT_NUMBER,
    child.DISPLAY_NAME AS RELATED_DISPLAY_NAME,
    rc.RELATIONSHIP_TYPE,
    rc.VALID_FROM,
    rc.VALID_TO
FROM RELATED_CLIENT rc
JOIN CLIENT_ACCOUNT child
    ON child.CLIENT_ID = rc.CHILD_CLIENT_ID
"""

RELATIONAL_QUERY_DEFINITIONS = {
    "insurance_core_party_export": {
        "source_system_code": "INSURANCE_CORE",
        "description": "Eksport podmiotow z relacyjnego systemu Oracle Insurance Core",
        "file_name": "insurance_core_party_export.json",
        "main_sql": INSURANCE_CORE_PARTY_MAIN_SQL,
        "person_roles_sql": INSURANCE_CORE_PERSON_ROLES_SQL,
        "related_parties_sql": INSURANCE_CORE_RELATED_PARTIES_SQL,
    }
}



class UnsupportedFileTypeError(ValueError):
    pass

class UnsupportedSourceSystemError(ValueError):
    pass


class InvalidFileContentError(ValueError):
    pass


class UnsupportedRelationalQueryError(ValueError):
    pass


class RelationalConnectionConfigurationError(ValueError):
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
            from openpyxl import load_workbook

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


def list_relational_queries() -> list[RelationalQueryInfo]:
    return [
        RelationalQueryInfo(
            query_name=query_name,
            source_system_code=str(definition["source_system_code"]),
            description=str(definition["description"]),
        )
        for query_name, definition in sorted(RELATIONAL_QUERY_DEFINITIONS.items())
    ]


def import_raw_file(
    db: Any,
    filename: str,
    content: bytes,
    source_system_code: str,
    created_by: str | None = None,
) -> RawLoadResponse:
    # Importujemy plik do RAW bez czyszczenia, żeby zachować oryginalne dane dla kolejnych warstw
    source_system_code = _validate_source_system_code(source_system_code)
    file_type = _get_file_type(filename)
    records_in = _validate_and_count_records(file_type, content)

    return persist_raw_content(
        db=db,
        filename=filename,
        file_type=file_type.upper(),
        content=content,
        source_system_code=source_system_code,
        created_by=created_by,
        records_in=records_in,
    )


def import_relational_source(
    db: Any,
    source_system_code: str,
    query_name: str,
    created_by: str | None = None,
    connector: Any | None = None,
    repo: Any | None = None,
) -> RawLoadResponse:
    source_system_code = _validate_source_system_code(source_system_code)
    normalized_query_name = query_name.strip().casefold()
    definition = RELATIONAL_QUERY_DEFINITIONS.get(normalized_query_name)
    if definition is None:
        raise UnsupportedRelationalQueryError(
            f"Unsupported relational query '{query_name}'."
        )
    if definition["source_system_code"] != source_system_code:
        raise UnsupportedRelationalQueryError(
            f"Query '{query_name}' is configured for source system "
            f"'{definition['source_system_code']}', not '{source_system_code}'."
        )

    records = extract_relational_records(definition, connector=connector)
    content = json.dumps(records, ensure_ascii=False, default=str).encode("utf-8")
    return persist_raw_content(
        db=db,
        filename=str(definition["file_name"]),
        file_type="JSON",
        content=content,
        source_system_code=source_system_code,
        created_by=created_by,
        records_in=len(records),
        repo=repo,
    )


def extract_relational_records(
    definition: dict[str, Any],
    connector: Any | None = None,
) -> list[dict[str, Any]]:
    connection_config = None
    if connector is None:
        from app.core.config import settings

        connection_config = settings
    if connector is None and connection_config is None:
        raise RelationalConnectionConfigurationError("Oracle connection is not configured.")

    connection = (
        connector(connection_config)
        if connector is not None
        else connect_relational_source(connection_config)
    )
    try:
        main_records = fetch_relational_rows(connection, str(definition["main_sql"]))
        person_roles = fetch_relational_rows(connection, str(definition["person_roles_sql"]))
        related_parties = fetch_relational_rows(connection, str(definition["related_parties_sql"]))
    finally:
        close = getattr(connection, "close", None)
        if callable(close):
            close()

    records_by_client_id = {
        str(record["CLIENT_ID"]): record
        for record in main_records
    }

    roles_by_client_id: dict[str, list[dict[str, Any]]] = {}
    for role in person_roles:
        client_id = str(role.get("CLIENT_ID"))
        if client_id not in records_by_client_id:
            continue
        roles_by_client_id.setdefault(client_id, []).append(
            {
                "role_group": role.get("ROLE_NAME"),
                "first_name": role.get("AGENT_FIRST_NAME"),
                "last_name": role.get("AGENT_LAST_NAME"),
                "pesel": role.get("AGENT_PESEL"),
                "license_no": role.get("AGENT_LICENSE_NO"),
                "valid_from": role.get("VALID_FROM"),
                "valid_to": role.get("VALID_TO"),
            }
        )

    parties_by_client_id: dict[str, list[dict[str, Any]]] = {}
    for relation in related_parties:
        client_id = str(relation.get("CLIENT_ID"))
        if client_id not in records_by_client_id:
            continue
        parties_by_client_id.setdefault(client_id, []).append(
            {
                "relationship_group": relation.get("RELATIONSHIP_TYPE"),
                "related_source_record_id": relation.get("RELATED_CLIENT_NUMBER"),
                "name": relation.get("RELATED_DISPLAY_NAME"),
                "valid_from": relation.get("VALID_FROM"),
                "valid_to": relation.get("VALID_TO"),
            }
        )

    for client_id, record in records_by_client_id.items():
        if client_id in roles_by_client_id:
            record["RELATED_PERSONS_JSON"] = json.dumps(
                roles_by_client_id[client_id],
                ensure_ascii=False,
                default=str,
            )
        if client_id in parties_by_client_id:
            record["RELATED_PARTIES_JSON"] = json.dumps(
                parties_by_client_id[client_id],
                ensure_ascii=False,
                default=str,
            )

    return list(records_by_client_id.values())


def connect_relational_source(settings: Any) -> Any:
    if settings.oracle_odbc_connection_string:
        return connect_odbc(settings.oracle_odbc_connection_string)

    return connect_oracle_thin(
        user=settings.oracle_app_user,
        password=settings.oracle_app_password,
        host=settings.oracle_host,
        port=settings.oracle_port,
        service_name=settings.oracle_service_name,
    )


def connect_odbc(connection_string: str | None) -> Any:
    if not connection_string:
        raise RelationalConnectionConfigurationError(
            "ORACLE_ODBC_CONNECTION_STRING is not configured."
        )

    import pyodbc

    return pyodbc.connect(connection_string)


def connect_oracle_thin(
    user: str,
    password: str,
    host: str,
    port: int,
    service_name: str,
) -> Any:
    import oracledb

    dsn = f"{host}:{port}/{service_name}"
    return oracledb.connect(user=user, password=password, dsn=dsn)


def fetch_relational_rows(connection: Any, sql: str) -> list[dict[str, Any]]:
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        columns = [str(column[0]) for column in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
    finally:
        close = getattr(cursor, "close", None)
        if callable(close):
            close()


def persist_raw_content(
    db: Any,
    filename: str,
    file_type: str,
    content: bytes,
    source_system_code: str,
    created_by: str | None,
    records_in: int | None,
    repo: Any | None = None,
) -> RawLoadResponse:
    if repo is None:
        from app.layers.ingestion.repository import IngestionRepository

    repo = repo or IngestionRepository(db)
    batch = None
    process_log = None

    try:
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
        if hasattr(db, "rollback"):
            db.rollback()
        # Zamieniamy konflikt hasha na błąd walidacji, żeby użytkownik wiedział że plik już istnieje
        error_message = "File with this hash already exists."

        if process_log is not None:
            repo.finish_process_log(process_log, status="FAILED", error_message=error_message)
        if batch is not None:
            repo.update_import_batch_status(batch, "FAILED", error_message=error_message, finish=True)

        raise InvalidFileContentError(error_message) from exc

    except Exception as exc:
        if hasattr(db, "rollback"):
            db.rollback()
        # Domykamy logi przy błędzie technicznym, żeby baza nie zostawiała importu w PROCESSING
        error_message = str(exc)

        if process_log is not None:
            repo.finish_process_log(process_log, status="FAILED", error_message=error_message)
        if batch is not None:
            repo.update_import_batch_status(batch, "FAILED", error_message=error_message, finish=True)

        raise
