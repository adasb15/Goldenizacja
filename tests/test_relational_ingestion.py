import json
import unittest
from types import SimpleNamespace

from app.layers.ingestion.service import (
    GENERIC_INSURANCE_CORE_QUERY_NAME,
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
        if "PERSON_REF" in sql:
            self.description = [
                ("PERSON_REF",),
                ("NATIONAL_REF",),
                ("GIVEN_TXT",),
                ("FAMILY_TXT",),
                ("LICENSE_TOKEN",),
                ("ROLE_BUCKET",),
                ("MAILBOX",),
                ("TEL_NOTE",),
            ]
            self.rows = [
                ("AGENT-1", "60021406849", "Magdalena", "Pawlak-Sikora", "AG-100", "BOARD_MEMBER", None, None),
                ("IC-90001", None, "Jan", "Nowak", None, "AGENT", "jan.nowak@example.test", "+48 500 100 200"),
            ]
        elif "FROM CLIENT_ACCOUNT" in sql:
            self.description = [
                ("CUST_UID",),
                ("EXT_REF_NO",),
                ("PARTY_LABEL",),
                ("TAX_REF",),
                ("STAT_REG_REF",),
                ("COURT_REF",),
                ("SOURCE_REVISION",),
            ]
            self.rows = [
                (1, "IC-10001", "Facebook Meta Sp. z o.o.", "1234805466", "234963846", "0000000008", "R2026-05-A"),
            ]
        elif "FROM AGENT_ASSIGNMENT" in sql:
            self.description = [
                ("CUST_UID",),
                ("GIVEN_TXT",),
                ("FAMILY_TXT",),
                ("NATIONAL_REF",),
                ("LICENSE_TOKEN",),
                ("ROLE_BUCKET",),
                ("VALID_SINCE",),
                ("VALID_UNTIL",),
                ("HR_SOURCE",),
                ("QUALITY_NOTE",),
            ]
            self.rows = [
                (1, "Magdalena", "Pawlak-Sikora", "60021406849", "AG-100", "BOARD_MEMBER", "2024-01-07", None, "KRS_SYNC", None),
            ]
        else:
            self.description = [
                ("CUST_UID",),
                ("RELATED_EXT_REF_NO",),
                ("RELATED_PARTY_LABEL",),
                ("LINK_BUCKET",),
                ("VALID_SINCE",),
                ("VALID_UNTIL",),
                ("ORIGIN_HINT",),
                ("COMMENT_TXT",),
            ]
            self.rows = [
                (1, "IC-10002", "Baltic Med Supply spolka z ograniczona odpowiedzialnoscia", "SHAREHOLDER", "2021-01-01", None, "KRS", None),
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
        self.assertEqual(records[0]["EXT_REF_NO"], "IC-10001")
        self.assertEqual(json.loads(records[0]["RELATED_PERSONS_JSON"])[0]["pesel"], "60021406849")
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
        self.assertEqual(snapshot[0]["PARTY_LABEL"], "Facebook Meta Sp. z o.o.")

    def test_generic_relational_query_uses_requested_party_entity_type(self) -> None:
        repo = FakeRepo()

        result = import_relational_source(
            db=SimpleNamespace(),
            source_system_code="INSURANCE_CORE",
            query_name=GENERIC_INSURANCE_CORE_QUERY_NAME,
            entity_type="PARTY",
            created_by="test",
            connector=lambda _: FakeConnection(),
            repo=repo,
        )

        self.assertEqual(result.file_name, "insurance_core_party_export.json")
        snapshot = json.loads(repo.file_content.decode("utf-8"))
        self.assertEqual(snapshot[0]["PARTY_LABEL"], "Facebook Meta Sp. z o.o.")

    def test_import_relational_person_source_persists_person_snapshot(self) -> None:
        repo = FakeRepo()

        result = import_relational_source(
            db=SimpleNamespace(),
            source_system_code="INSURANCE_CORE",
            query_name="insurance_core_person_export",
            created_by="test",
            connector=lambda _: FakeConnection(),
            repo=repo,
        )

        self.assertEqual(result.raw_file_id, 40)
        snapshot = json.loads(repo.file_content.decode("utf-8"))
        self.assertEqual(len(snapshot), 2)
        self.assertEqual(snapshot[0]["PERSON_REF"], "AGENT-1")
        self.assertEqual(snapshot[0]["NATIONAL_REF"], "60021406849")

    def test_generic_relational_query_uses_requested_person_entity_type(self) -> None:
        repo = FakeRepo()

        result = import_relational_source(
            db=SimpleNamespace(),
            source_system_code="INSURANCE_CORE",
            query_name=GENERIC_INSURANCE_CORE_QUERY_NAME,
            entity_type="PERSON",
            created_by="test",
            connector=lambda _: FakeConnection(),
            repo=repo,
        )

        self.assertEqual(result.file_name, "insurance_core_person_export.json")
        snapshot = json.loads(repo.file_content.decode("utf-8"))
        self.assertEqual(snapshot[0]["PERSON_REF"], "AGENT-1")

    def test_generic_relational_query_requires_entity_type(self) -> None:
        with self.assertRaises(UnsupportedRelationalQueryError):
            import_relational_source(
                db=SimpleNamespace(),
                source_system_code="INSURANCE_CORE",
                query_name=GENERIC_INSURANCE_CORE_QUERY_NAME,
                connector=lambda _: FakeConnection(),
                repo=FakeRepo(),
            )

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
