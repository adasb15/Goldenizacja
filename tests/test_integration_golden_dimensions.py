import unittest
from types import SimpleNamespace

from app.layers.integration_golden.service import (
    create_or_update_golden_party,
    create_or_update_golden_person,
)


class GoldenRepo:
    def __init__(self, entity_type: str, records: list[SimpleNamespace]) -> None:
        self.entity_type = entity_type
        self.records = records
        self.created_person = None
        self.updated_person = None
        self.created_party = None
        self.updated_party = None
        self.created_address = None
        self.committed = False
        self.existing_person = None
        self.existing_party = None
        self.existing_address = None

    def get_entity_group_members(self, entity_type: str, entity_group_id: int):
        assert entity_type == self.entity_type
        assert entity_group_id == 1
        return [
            SimpleNamespace(Preprocessed_ID=record.Preprocessed_ID)
            for record in self.records
        ]

    def get_preprocessed_records_by_ids(self, entity_type: str, preprocessed_ids: list[int]):
        assert entity_type == self.entity_type
        expected_ids = sorted(record.Preprocessed_ID for record in self.records)
        assert sorted(preprocessed_ids) == expected_ids
        return self.records

    def get_source_metadata_for_import_batch(self, import_batch_id: int):
        lookup = {
            record.ImportBatch_ID: (
                getattr(record, "source_system_code", None),
                getattr(record, "trust_level", None),
                getattr(record, "import_started_at", None),
            )
            for record in self.records
        }
        return lookup.get(import_batch_id, (None, None, None))

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
        self.created_address = SimpleNamespace(Address_ID=301, **kwargs)
        return self.created_address

    def commit(self):
        self.committed = True


class GoldenDimensionServiceTests(unittest.TestCase):
    def test_creates_dim_person_and_address_from_group(self) -> None:
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
            ),
            SimpleNamespace(
                Preprocessed_ID=2,
                ImportBatch_ID=20,
                source_system_code="CEIDG",
                trust_level=80,
                PESEL_Normalized="90010112345",
                First_Name_Normalized="JANUSZ",
                Last_Name_Normalized="KOWALSKI",
                Street_Normalized="DLUGA",
                Building_Number_Normalized="12",
                City_Normalized="POZNAN",
                Postal_Code_Normalized="60-001",
                Country_Normalized="PL",
            ),
        ]
        repo = GoldenRepo("PERSON", records)

        result = create_or_update_golden_person(db=None, entity_group_id=1, repo=repo)

        self.assertEqual(result.dimension_action, "CREATED")
        self.assertEqual(result.dimension_id, 101)
        self.assertEqual(result.address_action, "CREATED")
        self.assertEqual(result.address_id, 301)
        self.assertEqual(repo.created_person.PESEL, "90010112345")
        self.assertEqual(repo.created_person.First_Name, "JAN")
        self.assertEqual(repo.created_address.street, "KWIATOWA")
        self.assertTrue(repo.committed)

    def test_updates_dim_party_when_identity_already_exists(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_code="REGON",
                trust_level=85,
                REGON_Normalized="123456789",
                Name_Normalized="ALFA SA",
                Short_Name_Normalized="ALFA",
                Legal_Entity_Type_Normalized="SA",
                Registration_Country_Normalized="PL",
                Establishment_Date="2020-01-01",
                Street_Normalized="KWIATOWA",
                Building_Number_Normalized="10",
                City_Normalized="WARSZAWA",
                Postal_Code_Normalized="00-001",
                Country_Normalized="PL",
            ),
            SimpleNamespace(
                Preprocessed_ID=2,
                ImportBatch_ID=20,
                source_system_code="KRS",
                trust_level=90,
                REGON_Normalized="123456789",
                Name_Normalized="ALFA SPOLKA AKCYJNA",
                Short_Name_Normalized="ALFA SA",
                Legal_Entity_Type_Normalized="SPOLKA AKCYJNA",
                Registration_Country_Normalized="PL",
                Establishment_Date="2019-12-31",
            ),
        ]
        repo = GoldenRepo("PARTY", records)
        repo.existing_party = SimpleNamespace(Party_ID=201, Name="OLD NAME")

        result = create_or_update_golden_party(db=None, entity_group_id=1, repo=repo)

        self.assertEqual(result.dimension_action, "UPDATED")
        self.assertEqual(result.dimension_id, 201)
        self.assertEqual(repo.updated_party.Name, "ALFA SPOLKA AKCYJNA")
        self.assertEqual(repo.updated_party.Legal_Entity_Type, "SPOLKA AKCYJNA")
        self.assertEqual(result.address_action, "CREATED")
        self.assertTrue(repo.committed)

    def test_reuses_existing_address_when_same_address_already_exists(self) -> None:
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
        repo = GoldenRepo("PERSON", records)
        repo.existing_address = SimpleNamespace(Address_ID=999)

        result = create_or_update_golden_person(db=None, entity_group_id=1, repo=repo)

        self.assertEqual(result.address_action, "REUSED")
        self.assertEqual(result.address_id, 999)


if __name__ == "__main__":
    unittest.main()
