import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.sql import get_db
from app.layers.integration_golden.api import router
from app.layers.integration_golden.service import (
    GoldenDimensionLoadResult,
    GoldenLoadRunResult,
    GoldenRecordRejectResult,
    golden_load_dimensions,
)


class GoldenLoadRepo:
    def __init__(self, entity_type: str, records: list[SimpleNamespace]) -> None:
        self.entity_type = entity_type
        self.records = records
        self.existing_person = None
        self.existing_party = None
        self.existing_address = None
        self.created_person = None
        self.updated_person = None
        self.created_party = None
        self.updated_party = None
        self.address_types = {
            "RESIDENCE": SimpleNamespace(AddressType_ID=1, AddressType_Name="RESIDENCE"),
            "REGISTERED": SimpleNamespace(AddressType_ID=2, AddressType_Name="REGISTERED"),
        }
        self.identity_types = {
            "NIP": SimpleNamespace(IdentityType_ID=11),
            "REGON": SimpleNamespace(IdentityType_ID=12),
            "KRS": SimpleNamespace(IdentityType_ID=13),
            "LEI": SimpleNamespace(IdentityType_ID=14),
            "KNF_REGISTER_NUMBER": SimpleNamespace(IdentityType_ID=15),
            "DECISION_NUMBER": SimpleNamespace(IdentityType_ID=16),
        }
        self.person_address_links = {}
        self.party_address_links = {}
        self.party_identities = {}
        self.golden_record_rejects = []
        self.groups = [SimpleNamespace(Entity_Group_ID=1, Entity_Type=entity_type)]
        self.scoped_raw_file_ids = []
        self.process_logs = []
        self.commits = 0

    def get_entity_groups(self, entity_type: str):
        assert entity_type == self.entity_type
        return self.groups

    def get_entity_groups_for_raw_file(self, entity_type: str, raw_file_id: int):
        assert entity_type == self.entity_type
        self.scoped_raw_file_ids.append(raw_file_id)
        return self.groups

    def get_entity_group_members(self, entity_type: str, entity_group_id: int):
        assert entity_type == self.entity_type
        assert entity_group_id == 1
        return [SimpleNamespace(Preprocessed_ID=record.Preprocessed_ID) for record in self.records]

    def get_preprocessed_records_by_ids(self, entity_type: str, preprocessed_ids: list[int]):
        assert entity_type == self.entity_type
        assert sorted(preprocessed_ids) == sorted(record.Preprocessed_ID for record in self.records)
        return self.records

    def get_source_metadata_for_import_batch(self, import_batch_id: int):
        for record in self.records:
            if record.ImportBatch_ID == import_batch_id:
                return (
                    getattr(record, "source_system_code", None),
                    getattr(record, "trust_level", None),
                    getattr(record, "import_started_at", None),
                )
        return None, None, None

    def get_import_batch_id_for_raw_file(self, raw_file_id: int):
        return raw_file_id + 1000

    def create_golden_load_process_log(self, import_batch_id: int, raw_file_id: int | None):
        log = SimpleNamespace(
            ImportBatch_ID=import_batch_id,
            RawFile_ID=raw_file_id,
            Step_Name="GOLDEN_LOAD",
            Step_Status="STARTED",
            Records_In=None,
            Records_Out=None,
            Error_Message=None,
        )
        self.process_logs.append(log)
        return log

    def finish_process_log(
        self,
        log,
        status: str,
        records_in: int | None = None,
        records_out: int | None = None,
        error_message: str | None = None,
    ):
        log.Step_Status = status
        log.Records_In = records_in
        log.Records_Out = records_out
        log.Error_Message = error_message
        return log

    def find_person_by_identity(self, **_kwargs):
        return self.existing_person

    def create_person(self, **kwargs):
        self.created_person = SimpleNamespace(Person_ID=101, **kwargs)
        return self.created_person

    def update_person(self, person, **kwargs):
        for key, value in kwargs.items():
            setattr(person, key, value)
        self.updated_person = person
        return person

    def find_party_by_identity(self, **_kwargs):
        return self.existing_party

    def create_party(self, **kwargs):
        self.created_party = SimpleNamespace(Party_ID=201, **kwargs)
        return self.created_party

    def update_party(self, party, **kwargs):
        for key, value in kwargs.items():
            setattr(party, key, value)
        self.updated_party = party
        return party

    def find_address(self, **_kwargs):
        return self.existing_address

    def get_or_create_address(self, **kwargs):
        if self.existing_address is not None:
            return self.existing_address
        self.existing_address = SimpleNamespace(Address_ID=301, **kwargs)
        return self.existing_address

    def get_address_type_by_name(self, address_type_name: str):
        return self.address_types.get(address_type_name)

    def get_identity_type_by_name(self, identity_type_name: str):
        return self.identity_types.get(identity_type_name)

    def ensure_person_address_link(self, *, person_id: int, address_id: int, address_type_id: int, valid_from=None, valid_to=None):
        key = (person_id, address_id, address_type_id, valid_from, valid_to)
        if key not in self.person_address_links:
            self.person_address_links[key] = SimpleNamespace(PersonAddress_ID=len(self.person_address_links) + 1)
        return self.person_address_links[key]

    def ensure_party_address_link(self, *, party_id: int, address_id: int, address_type_id: int, valid_from=None, valid_to=None):
        key = (party_id, address_id, address_type_id, valid_from, valid_to)
        if key not in self.party_address_links:
            self.party_address_links[key] = SimpleNamespace(PartyAddress_ID=len(self.party_address_links) + 1)
        return self.party_address_links[key]

    def ensure_party_identity(self, *, party_id: int, identity_type_id: int, identity_value: str, **kwargs):
        key = (identity_type_id, identity_value)
        if key not in self.party_identities:
            self.party_identities[key] = SimpleNamespace(PartyIdentity_ID=len(self.party_identities) + 1)
        return self.party_identities[key]

    def record_golden_record_reject(self, **kwargs):
        reject = SimpleNamespace(Reject_ID=len(self.golden_record_rejects) + 1, **kwargs)
        self.golden_record_rejects.append(reject)
        return reject

    def commit(self):
        self.commits += 1


class GoldenLoadServiceTests(unittest.TestCase):
    def test_golden_load_dimensions_person_processes_group(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_code="PESEL",
                trust_level=90,
                PESEL_Normalized="90010112345",
                First_Name_Normalized="JAN",
                Last_Name_Normalized="KOWALSKI",
                Street_Normalized="KWIATOWA",
                Building_Number_Normalized="10",
                City_Normalized="WARSZAWA",
                Postal_Code_Normalized="00-001",
                Country_Normalized="PL",
            )
        ]
        repo = GoldenLoadRepo("PERSON", records)

        result = golden_load_dimensions(db=None, entity_type="PERSON", repo=repo)

        self.assertEqual(result.entity_type, "PERSON")
        self.assertEqual(result.groups_in_scope, 1)
        self.assertEqual(result.groups_processed, 1)
        self.assertEqual(result.groups_rejected, 0)
        self.assertEqual(result.results[0].dimension_action, "CREATED")
        self.assertEqual(result.results[0].address_link_action, "CREATED")
        self.assertEqual(len(repo.person_address_links), 1)

    def test_golden_load_dimensions_party_processes_group(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_code="REGON",
                trust_level=85,
                REGON_Normalized="123456789",
                NIP_Normalized="1234567890",
                KRS_Normalized="0000001234",
                LEI_Normalized="5493001KJTIIGC8Y1R12",
                Name_Normalized="ALFA SA",
                Legal_Entity_Type_Normalized="SA",
                Registration_Country_Normalized="PL",
                Street_Normalized="KWIATOWA",
                Building_Number_Normalized="10",
                City_Normalized="WARSZAWA",
                Postal_Code_Normalized="00-001",
                Country_Normalized="PL",
            )
        ]
        repo = GoldenLoadRepo("PARTY", records)

        result = golden_load_dimensions(db=None, entity_type="PARTY", repo=repo)

        self.assertEqual(result.entity_type, "PARTY")
        self.assertEqual(result.groups_processed, 1)
        self.assertEqual(result.groups_rejected, 0)
        self.assertEqual(result.results[0].dimension_action, "CREATED")
        self.assertEqual(result.results[0].address_link_action, "CREATED")
        self.assertEqual(result.results[0].party_identities_saved, 4)
        self.assertEqual(len(repo.party_address_links), 1)
        self.assertEqual(len(repo.party_identities), 4)

    def test_golden_load_dimensions_rejects_party_without_required_name(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_code="REGON",
                trust_level=85,
                REGON_Normalized="123456789",
                NIP_Normalized="1234567890",
            )
        ]
        repo = GoldenLoadRepo("PARTY", records)

        result = golden_load_dimensions(
            db=None,
            entity_type="PARTY",
            raw_file_id=55,
            repo=repo,
        )

        self.assertEqual(result.groups_in_scope, 1)
        self.assertEqual(result.groups_processed, 0)
        self.assertEqual(result.groups_rejected, 1)
        self.assertEqual(result.results, ())
        self.assertEqual(result.rejects[0].missing_fields, ("Name",))
        self.assertEqual(result.rejects[0].reason_code, "MISSING_REQUIRED_GOLDEN_FIELD")
        self.assertIsNone(repo.created_party)
        self.assertEqual(len(repo.golden_record_rejects), 1)
        self.assertEqual(repo.golden_record_rejects[0].entity_group_id, 1)

    def test_golden_load_dimensions_logs_process_when_raw_file_id_is_passed(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_code="PESEL",
                trust_level=90,
                PESEL_Normalized="90010112345",
                First_Name_Normalized="JAN",
                Last_Name_Normalized="KOWALSKI",
            )
        ]
        repo = GoldenLoadRepo("PERSON", records)

        result = golden_load_dimensions(
            db=None,
            entity_type="PERSON",
            raw_file_id=55,
            repo=repo,
        )

        self.assertEqual(result.raw_file_id, 55)
        self.assertEqual(len(repo.process_logs), 1)
        self.assertEqual(repo.process_logs[0].Step_Name, "GOLDEN_LOAD")
        self.assertEqual(repo.process_logs[0].Step_Status, "SUCCESS")
        self.assertEqual(repo.process_logs[0].Records_In, 1)
        self.assertEqual(repo.process_logs[0].Records_Out, 1)

    def test_golden_load_dimensions_scopes_groups_by_raw_file_id(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_code="PESEL",
                trust_level=90,
                PESEL_Normalized="90010112345",
                First_Name_Normalized="JAN",
                Last_Name_Normalized="KOWALSKI",
            )
        ]
        repo = GoldenLoadRepo("PERSON", records)

        golden_load_dimensions(
            db=None,
            entity_type="PERSON",
            raw_file_id=55,
            repo=repo,
        )

        self.assertEqual(repo.scoped_raw_file_ids, [55])


class GoldenLoadApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_db] = lambda: SimpleNamespace()
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_post_golden_load_returns_person_payload(self) -> None:
        mocked_result = GoldenLoadRunResult(
            entity_type="PERSON",
            raw_file_id=100,
            entity_group_id=1,
            groups_in_scope=1,
            groups_processed=1,
            groups_rejected=0,
            results=(
                GoldenDimensionLoadResult(
                    entity_type="PERSON",
                    entity_group_id=1,
                    member_preprocessed_ids=(1,),
                    dimension_id=101,
                    dimension_action="CREATED",
                    address_id=301,
                    address_action="CREATED",
                    address_link_action="CREATED",
                ),
            ),
            rejects=(),
        )
        with patch("app.layers.integration_golden.api.golden_load_dimensions", return_value=mocked_result):
            response = self.client.post(
                "/integration_golden/golden-load",
                data={"entity_type": "PERSON", "raw_file_id": 100, "entity_group_id": 1},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entity_type"], "PERSON")
        self.assertEqual(response.json()["raw_file_id"], 100)
        self.assertEqual(response.json()["results"][0]["dimension_id"], 101)

    def test_post_golden_load_returns_party_payload(self) -> None:
        mocked_result = GoldenLoadRunResult(
            entity_type="PARTY",
            raw_file_id=200,
            entity_group_id=1,
            groups_in_scope=1,
            groups_processed=1,
            groups_rejected=1,
            results=(
                GoldenDimensionLoadResult(
                    entity_type="PARTY",
                    entity_group_id=1,
                    member_preprocessed_ids=(1,),
                    dimension_id=201,
                    dimension_action="UPDATED",
                    address_id=301,
                    address_action="REUSED",
                    address_link_action="REUSED",
                    party_identities_saved=3,
                ),
            ),
            rejects=(
                GoldenRecordRejectResult(
                    entity_type="PARTY",
                    entity_group_id=2,
                    raw_file_id=200,
                    missing_fields=("Name",),
                    reason_code="MISSING_REQUIRED_GOLDEN_FIELD",
                    reason_message="Missing required fields for golden PARTY: Name",
                    member_preprocessed_ids=(10,),
                ),
            ),
        )
        with patch("app.layers.integration_golden.api.golden_load_dimensions", return_value=mocked_result):
            response = self.client.post(
                "/integration_golden/golden-load",
                data={"entity_type": "PARTY", "raw_file_id": 200, "entity_group_id": 1},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entity_type"], "PARTY")
        self.assertEqual(response.json()["raw_file_id"], 200)
        self.assertEqual(response.json()["results"][0]["party_identities_saved"], 3)
        self.assertEqual(response.json()["groups_rejected"], 1)
        self.assertEqual(response.json()["rejects"][0]["missing_fields"], ["Name"])


if __name__ == "__main__":
    unittest.main()
