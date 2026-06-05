import unittest

from app.layers.integration_golden.models import (
    DimAddress,
    DimParty,
    DimPerson,
    FactlessPartyIdentities,
    FactlessPersonAddress,
)
from app.layers.integration_golden.repository import IntegrationGoldenRepository


class FakeDb:
    def __init__(self, scalar_result=None) -> None:
        self.scalar_result = scalar_result
        self.added = []
        self.flush_count = 0
        self.commit_count = 0

    def scalar(self, _query):
        return self.scalar_result

    def add(self, entity) -> None:
        self.added.append(entity)

    def flush(self) -> None:
        self.flush_count += 1

    def commit(self) -> None:
        self.commit_count += 1


class IntegrationGoldenRepositoryTests(unittest.TestCase):
    def test_get_or_create_address_returns_existing_record(self) -> None:
        existing = DimAddress(Address_ID=101, City="WARSZAWA")
        repo = IntegrationGoldenRepository(FakeDb())
        repo.find_address = lambda **_: existing

        result = repo.get_or_create_address(city="WARSZAWA")

        self.assertIs(result, existing)
        self.assertEqual(repo.db.added, [])
        self.assertEqual(repo.db.flush_count, 0)

    def test_get_or_create_address_creates_new_record(self) -> None:
        db = FakeDb()
        repo = IntegrationGoldenRepository(db)
        repo.find_address = lambda **_: None

        result = repo.get_or_create_address(
            street="KWIATOWA",
            building_number="10",
            city="WARSZAWA",
            postal_code="00-001",
            country="PL",
        )

        self.assertIsInstance(result, DimAddress)
        self.assertEqual(result.Street, "KWIATOWA")
        self.assertEqual(result.Building_Number, "10")
        self.assertEqual(result.City, "WARSZAWA")
        self.assertEqual(result.Postal_Code, "00-001")
        self.assertEqual(result.Country, "PL")
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.flush_count, 1)

    def test_create_person_filters_unknown_fields(self) -> None:
        db = FakeDb()
        repo = IntegrationGoldenRepository(db)

        person = repo.create_person(
            PESEL="90010112345",
            First_Name="JAN",
            Last_Name="KOWALSKI",
            Unknown_Field="ignored",
        )

        self.assertIsInstance(person, DimPerson)
        self.assertEqual(person.PESEL, "90010112345")
        self.assertEqual(person.First_Name, "JAN")
        self.assertEqual(person.Last_Name, "KOWALSKI")
        self.assertFalse(hasattr(person, "Unknown_Field"))
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.flush_count, 1)

    def test_update_party_overwrites_known_fields_only(self) -> None:
        db = FakeDb()
        repo = IntegrationGoldenRepository(db)
        party = DimParty(Party_ID=7, Name="OLD NAME", Short_Name="OLD")

        updated = repo.update_party(
            party,
            Name="NEW NAME",
            Short_Name="NEW",
            Not_A_Column="ignored",
        )

        self.assertIs(updated, party)
        self.assertEqual(party.Name, "NEW NAME")
        self.assertEqual(party.Short_Name, "NEW")
        self.assertFalse(hasattr(party, "Not_A_Column"))
        self.assertEqual(db.flush_count, 1)

    def test_ensure_party_identity_updates_existing_record(self) -> None:
        existing = FactlessPartyIdentities(
            PartyIdentity_ID=11,
            Party_ID=1,
            IdentityType_ID=2,
            Identity_Value="1234567890",
            Is_Valid=False,
        )
        db = FakeDb(scalar_result=existing)
        repo = IntegrationGoldenRepository(db)

        result = repo.ensure_party_identity(
            party_id=5,
            identity_type_id=2,
            identity_value="1234567890",
            is_valid=True,
            match_confidence=1.0,
        )

        self.assertIs(result, existing)
        self.assertEqual(existing.Party_ID, 5)
        self.assertEqual(existing.Is_Valid, True)
        self.assertEqual(float(existing.Match_Confidence), 1.0)
        self.assertEqual(len(db.added), 0)
        self.assertEqual(db.flush_count, 1)

    def test_ensure_person_address_link_creates_record_when_missing(self) -> None:
        db = FakeDb(scalar_result=None)
        repo = IntegrationGoldenRepository(db)

        result = repo.ensure_person_address_link(
            person_id=10,
            address_id=20,
            address_type_id=1,
        )

        self.assertIsInstance(result, FactlessPersonAddress)
        self.assertEqual(result.Person_ID, 10)
        self.assertEqual(result.Address_ID, 20)
        self.assertEqual(result.AddressType_ID, 1)
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.flush_count, 1)


if __name__ == "__main__":
    unittest.main()
