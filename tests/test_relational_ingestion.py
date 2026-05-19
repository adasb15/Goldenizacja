import json
import unittest
from types import SimpleNamespace

from app.layers.ingestion.service import (
    RELATIONAL_QUERY_DEFINITIONS,
    UnsupportedRelationalQueryError,
    extract_relational_records,
    import_relational_source,
)


class FakeCursor:
    def __init__(self) -> None:
        self.description = []
        self.rows = []

    def execute(self, sql: str) -> None:
        if "FROM CLIENT_ACCOUNT" in sql:
            self.description = [
                ("CLIENT_ID",),
                ("CLIENT_NUMBER",),
                ("DISPLAY_NAME",),
                ("TAX_NUMBER",),
                ("NATIONAL_REGISTRY_NO",),
                ("LEGAL_REGISTER_NO",),
            ]
            self.rows = [
                (1, "IC-10001", "Astra Finance sp. z o.o.", "8567346215", "590096454", "0000123456"),
            ]
        elif "FROM AGENT_ASSIGNMENT" in sql:
            self.description = [
                ("CLIENT_ID",),
                ("AGENT_FIRST_NAME",),
                ("AGENT_LAST_NAME",),
                ("AGENT_PESEL",),
                ("AGENT_LICENSE_NO",),
                ("ROLE_NAME",),
                ("VALID_FROM",),
                ("VALID_TO",),
            ]
            self.rows = [
                (1, "Jan", "Nowak", "44051401359", "AG-100", "REPRESENTATIVE", "2022-01-01", None),
            ]
        else:
            self.description = [
                ("CLIENT_ID",),
                ("RELATED_CLIENT_NUMBER",),
                ("RELATED_DISPLAY_NAME",),
                ("RELATIONSHIP_TYPE",),
                ("VALID_FROM",),
                ("VALID_TO",),
            ]
            self.rows = [
                (1, "IC-10002", "Baltic Med Supply S.A.", "SHAREHOLDER", "2021-01-01", None),
            ]

    def fetchall(self) -> list[tuple]:
        return self.rows


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor()

    def close(self) -> None:
        self.closed = True


class FakeRepo:
    def __init__(self) -> None:
        self.file_content = None

    def get_or_create_source_system(self, code: str, name: str | None = None) -> SimpleNamespace:
        return SimpleNamespace(SourceSystem_ID=10)

    def create_import_batch(self, source_system_id: int, created_by: str | None) -> SimpleNamespace:
        return SimpleNamespace(ImportBatch_ID=20, Import_Status="NEW")

    def update_import_batch_status(
        self,
        batch: SimpleNamespace,
        status: str,
        error_message: str | None = None,
        finish: bool = False,
    ) -> SimpleNamespace:
        batch.Import_Status = status
        return batch

    def create_process_log(self, import_batch_id: int) -> SimpleNamespace:
        return SimpleNamespace(ProcessLog_ID=30)

    def finish_process_log(
        self,
        log: SimpleNamespace,
        status: str,
        raw_file_id: int | None = None,
        records_in: int | None = None,
        records_out: int | None = None,
        error_message: str | None = None,
    ) -> SimpleNamespace:
        log.Step_Status = status
        log.Records_In = records_in
        log.Records_Out = records_out
        return log

    def insert_raw_file(
        self,
        import_batch_id: int,
        file_name: str,
        file_type: str,
        file_size: int,
        file_hash: str,
        file_content: bytes,
    ) -> SimpleNamespace:
        self.file_content = file_content
        return SimpleNamespace(
            RawFile_ID=40,
            File_Name=file_name,
            File_Type=file_type,
            File_Size=file_size,
            File_Hash=file_hash,
        )


class RelationalIngestionTests(unittest.TestCase):
    def test_extracts_relational_records_with_related_json(self) -> None:
        definition = RELATIONAL_QUERY_DEFINITIONS["insurance_core_party_export"]

        records = extract_relational_records(definition, connector=lambda _: FakeConnection())

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["CLIENT_NUMBER"], "IC-10001")
        self.assertEqual(json.loads(records[0]["RELATED_PERSONS_JSON"])[0]["pesel"], "44051401359")
        self.assertEqual(json.loads(records[0]["RELATED_PARTIES_JSON"])[0]["relationship_group"], "SHAREHOLDER")

    def test_import_relational_source_persists_json_snapshot(self) -> None:
        repo = FakeRepo()

        result = import_relational_source(
            db=SimpleNamespace(),
            source_system_code="INSURANCE_CORE",
            query_name="insurance_core_party_export",
            created_by="test",
            connector=lambda _: FakeConnection(),
            repo=repo,
        )

        self.assertEqual(result.raw_file_id, 40)
        self.assertEqual(result.file_type, "JSON")
        snapshot = json.loads(repo.file_content.decode("utf-8"))
        self.assertEqual(snapshot[0]["DISPLAY_NAME"], "Astra Finance sp. z o.o.")

    def test_rejects_query_for_different_source_system(self) -> None:
        with self.assertRaises(UnsupportedRelationalQueryError):
            import_relational_source(
                db=SimpleNamespace(),
                source_system_code="PESEL",
                query_name="insurance_core_party_export",
                connector=lambda _: FakeConnection(),
                repo=FakeRepo(),
            )


if __name__ == "__main__":
    unittest.main()
