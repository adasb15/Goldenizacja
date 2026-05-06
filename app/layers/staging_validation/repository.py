from sqlalchemy import select
from sqlalchemy.orm import Session

from app.layers.staging_validation.models import ColumnMapping


SUPPORTED_ENTITY_TYPES = {"PERSON", "PARTY"}


class UnsupportedEntityTypeError(ValueError):
    pass


def normalize_entity_type(entity_type: str) -> str:
    normalized = entity_type.strip().upper()
    if normalized not in SUPPORTED_ENTITY_TYPES:
        raise UnsupportedEntityTypeError(
            f"Unsupported entity type '{entity_type}'. Supported types: PERSON, PARTY."
        )
    return normalized


class StagingValidationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_column_mappings(
        self,
        source_system_id: int,
        entity_type: str,
    ) -> list[ColumnMapping]:
        entity_type = normalize_entity_type(entity_type)
        return list(
            self.db.scalars(
                select(ColumnMapping)
                .where(ColumnMapping.SourceSystem_ID == source_system_id)
                .where(ColumnMapping.Entity_Type == entity_type)
                .order_by(ColumnMapping.ColumnMapping_ID)
            )
        )

    def get_column_mapping(
        self,
        source_system_id: int,
        entity_type: str,
    ) -> dict[str, str]:
        mappings = self.get_column_mappings(source_system_id, entity_type)
        return {
            row.Source_Column_Name: row.Canonical_Column_Name
            for row in mappings
        }
