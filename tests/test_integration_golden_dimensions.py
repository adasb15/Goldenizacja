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
        self.address_types = {
            "RESIDENCE": SimpleNamespace(AddressType_ID=1, AddressType_Name="RESIDENCE"),
            "REGISTERED": SimpleNamespace(AddressType_ID=2, AddressType_Name="REGISTERED"),
        }
        self.identity_types = {
            "NIP": SimpleNamespace(IdentityType_ID=11, IdentityType_Name="NIP"),
            "REGON": SimpleNamespace(IdentityType_ID=12, IdentityType_Name="REGON"),
            "KRS": SimpleNamespace(IdentityType_ID=13, IdentityType_Name="KRS"),
            "LEI": SimpleNamespace(IdentityType_ID=14, IdentityType_Name="LEI"),
            "KNF_REGISTER_NUMBER": SimpleNamespace(
                IdentityType_ID=15,
                IdentityType_Name="KNF_REGISTER_NUMBER",
            ),
            "DECISION_NUMBER": SimpleNamespace(
                IdentityType_ID=16,
                IdentityType_Name="DECISION_NUMBER",
            ),
        }
        self.person_address_links = {}
        self.party_address_links = {}
        self.party_identities = {}
        self.dimension_lineage = {}
        self.entity_changes = []

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
                getattr(record, "source_system_id", None),
                getattr(record, "source_system_code", None),
                getattr(record, "trust_level", None),
                getattr(record, "import_started_at", None),
            )
            for record in self.records
        }
        return lookup.get(import_batch_id, (None, None, None, None))

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

    def get_address_type_by_name(self, address_type_name: str):
        return self.address_types.get(address_type_name)

    def get_identity_type_by_name(self, identity_type_name: str):
        return self.identity_types.get(identity_type_name)

    def ensure_person_address_link(self, *, person_id: int, address_id: int, address_type_id: int, valid_from=None, valid_to=None):
        key = (person_id, address_id, address_type_id, valid_from, valid_to)
        if key in self.person_address_links:
            return self.person_address_links[key]
        link = SimpleNamespace(
            PersonAddress_ID=len(self.person_address_links) + 1,
            Person_ID=person_id,
            Address_ID=address_id,
            AddressType_ID=address_type_id,
            Valid_From=valid_from,
            Valid_To=valid_to,
        )
        self.person_address_links[key] = link
        return link

    def ensure_party_address_link(self, *, party_id: int, address_id: int, address_type_id: int, valid_from=None, valid_to=None):
        key = (party_id, address_id, address_type_id, valid_from, valid_to)
        if key in self.party_address_links:
            return self.party_address_links[key]
        link = SimpleNamespace(
            PartyAddress_ID=len(self.party_address_links) + 1,
            Party_ID=party_id,
            Address_ID=address_id,
            AddressType_ID=address_type_id,
            Valid_From=valid_from,
            Valid_To=valid_to,
        )
        self.party_address_links[key] = link
        return link

    def ensure_party_identity(
        self,
        *,
        party_id: int,
        identity_type_id: int,
        identity_value: str,
        is_valid=None,
        match_confidence=None,
        valid_from=None,
        valid_to=None,
    ):
        key = (identity_type_id, identity_value)
        if key in self.party_identities:
            identity = self.party_identities[key]
            identity.Party_ID = party_id
            identity.Is_Valid = is_valid
            identity.Match_Confidence = match_confidence
            identity.Valid_From = valid_from
            identity.Valid_To = valid_to
            return identity
        identity = SimpleNamespace(
            PartyIdentity_ID=len(self.party_identities) + 1,
            Party_ID=party_id,
            IdentityType_ID=identity_type_id,
            Identity_Value=identity_value,
            Is_Valid=is_valid,
            Match_Confidence=match_confidence,
            Valid_From=valid_from,
            Valid_To=valid_to,
        )
        self.party_identities[key] = identity
        return identity

    def upsert_dimension_lineage(self, **kwargs):
        key = (
            kwargs["lineage_type"],
            kwargs["dimension_id"],
            kwargs["attribute_name"],
        )
        self.dimension_lineage[key] = SimpleNamespace(**kwargs)
        return self.dimension_lineage[key]

    def record_entity_change(self, **kwargs):
        change = SimpleNamespace(Change_ID=len(self.entity_changes) + 1, **kwargs)
        self.entity_changes.append(change)
        return change

    def commit(self):
        self.committed = True


class GoldenDimensionServiceTests(unittest.TestCase):
    def test_creates_dim_person_and_address_from_group(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_id=1,
                source_system_code="PESEL",
                trust_level=90,
                Source_Record_ID="SRC-1",
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
                source_system_id=2,
                source_system_code="CEIDG",
                trust_level=80,
                Source_Record_ID="SRC-2",
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
        self.assertEqual(repo.created_address.street, "DLUGA")
        self.assertEqual(result.address_link_action, "CREATED")
        self.assertEqual(len(repo.person_address_links), 1)
        person_lineage = repo.dimension_lineage[("PERSON", 101, "First_Name")]
        self.assertEqual(person_lineage.source_system_id, 1)
        self.assertEqual(person_lineage.source_record_id, "SRC-1")
        self.assertEqual(person_lineage.import_batch_id, 10)
        self.assertEqual(person_lineage.selection_rule, "SOURCE_PRIORITY")
        address_lineage = repo.dimension_lineage[("ADDRESS", 301, "Street")]
        self.assertEqual(address_lineage.attribute_name, "Street")
        self.assertTrue(repo.committed)

    def test_updates_dim_party_when_identity_already_exists(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_id=3,
                source_system_code="REGON",
                trust_level=85,
                Source_Record_ID="REGON-1",
                REGON_Normalized="123456789",
                Name_Normalized="ALFA SA",
                Short_Name_Normalized="ALFA",
                Legal_Entity_Type_Normalized="SA",
                Registration_Country_Normalized="PL",
                Establishment_Date="2020-01-01",
                NIP_Normalized="1234567890",
                Street_Normalized="KWIATOWA",
                Building_Number_Normalized="10",
                City_Normalized="WARSZAWA",
                Postal_Code_Normalized="00-001",
                Country_Normalized="PL",
            ),
            SimpleNamespace(
                Preprocessed_ID=2,
                ImportBatch_ID=20,
                source_system_id=4,
                source_system_code="KRS",
                trust_level=90,
                Source_Record_ID="KRS-1",
                REGON_Normalized="123456789",
                KRS_Normalized="0000001234",
                Name_Normalized="ALFA SPOLKA AKCYJNA",
                Short_Name_Normalized="ALFA SA",
                Legal_Entity_Type_Normalized="SPOLKA AKCYJNA",
                Registration_Country_Normalized="PL",
                Establishment_Date="2019-12-31",
                Decision_Number_Normalized="DEC-1",
            ),
        ]
        repo = GoldenRepo("PARTY", records)
        repo.existing_party = SimpleNamespace(
            Party_ID=201,
            Name="OLD NAME",
            Registration_Country="PL",
        )

        result = create_or_update_golden_party(db=None, entity_group_id=1, repo=repo)

        self.assertEqual(result.dimension_action, "UPDATED")
        self.assertEqual(result.dimension_id, 201)
        self.assertEqual(repo.updated_party.Name, "ALFA SPOLKA AKCYJNA")
        self.assertEqual(repo.updated_party.Legal_Entity_Type, "SPOLKA AKCYJNA")
        self.assertEqual(result.address_action, "CREATED")
        self.assertEqual(result.address_link_action, "CREATED")
        self.assertEqual(result.party_identities_saved, 4)
        self.assertEqual(len(repo.party_address_links), 1)
        self.assertEqual(len(repo.party_identities), 4)
        party_lineage = repo.dimension_lineage[("PARTY", 201, "Name")]
        self.assertEqual(party_lineage.source_system_id, 4)
        self.assertEqual(party_lineage.source_record_id, "KRS-1")
        self.assertEqual(party_lineage.import_batch_id, 20)
        self.assertEqual(party_lineage.selection_rule, "SOURCE_PRIORITY")
        identity = next(
            identity
            for identity in repo.party_identities.values()
            if identity.Identity_Value == "1234567890"
        )
        identity_lineage = repo.dimension_lineage[
            ("PARTY_IDENTITY", identity.PartyIdentity_ID, "Identity_Value")
        ]
        self.assertEqual(identity_lineage.source_record_id, "REGON-1")
        changed_fields = {change.attribute_name for change in repo.entity_changes}
        self.assertIn("Name", changed_fields)
        self.assertNotIn("Registration_Country", changed_fields)
        self.assertTrue(repo.committed)

    def test_does_not_log_change_when_existing_value_is_unchanged(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_id=3,
                source_system_code="REGON",
                trust_level=85,
                Source_Record_ID="REGON-1",
                REGON_Normalized="123456789",
                Name_Normalized="ALFA SA",
                Registration_Country_Normalized="PL",
            )
        ]
        repo = GoldenRepo("PARTY", records)
        repo.existing_party = SimpleNamespace(
            Party_ID=201,
            Name="ALFA SA",
            Registration_Country="PL",
        )

        create_or_update_golden_party(db=None, entity_group_id=1, repo=repo)

        self.assertEqual(repo.entity_changes, [])

    def test_lineage_write_is_idempotent_for_same_dimension_attribute(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_id=3,
                source_system_code="REGON",
                trust_level=85,
                Source_Record_ID="REGON-1",
                REGON_Normalized="123456789",
                NIP_Normalized="1234567890",
                Name_Normalized="ALFA SA",
                Registration_Country_Normalized="PL",
            )
        ]
        repo = GoldenRepo("PARTY", records)
        repo.existing_party = SimpleNamespace(Party_ID=201, Name="ALFA SA")

        create_or_update_golden_party(db=None, entity_group_id=1, repo=repo)
        create_or_update_golden_party(db=None, entity_group_id=1, repo=repo)

        self.assertEqual(
            sum(
                1
                for key in repo.dimension_lineage
                if key == ("PARTY", 201, "Name")
            ),
            1,
        )

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

    def test_party_identity_and_address_writes_are_idempotent(self) -> None:
        records = [
            SimpleNamespace(
                Preprocessed_ID=1,
                ImportBatch_ID=10,
                source_system_code="REGON",
                trust_level=85,
                REGON_Normalized="123456789",
                NIP_Normalized="1234567890",
                KRS_Normalized="0000001234",
                Name_Normalized="ALFA SA",
                Registration_Country_Normalized="PL",
                Street_Normalized="KWIATOWA",
                Building_Number_Normalized="10",
                City_Normalized="WARSZAWA",
                Postal_Code_Normalized="00-001",
                Country_Normalized="PL",
            )
        ]
        repo = GoldenRepo("PARTY", records)
        repo.existing_party = SimpleNamespace(Party_ID=201, Name="ALFA SA")
        repo.existing_address = SimpleNamespace(Address_ID=301)

        first = create_or_update_golden_party(db=None, entity_group_id=1, repo=repo)
        second = create_or_update_golden_party(db=None, entity_group_id=1, repo=repo)

        self.assertEqual(first.party_identities_saved, 3)
        self.assertEqual(second.party_identities_saved, 3)
        self.assertEqual(len(repo.party_identities), 3)
        self.assertEqual(len(repo.party_address_links), 1)


if __name__ == "__main__":
    unittest.main()
