from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.layers.staging_validation.mapper import map_records_to_canonical
from app.layers.staging_validation.repository import StagingValidationRepository


def get_column_mapping(
    db: Session,
    source_system_id: int,
    entity_type: str,
) -> dict[str, str]:
    repo = StagingValidationRepository(db)
    return repo.get_column_mapping(source_system_id, entity_type)


def map_source_records_to_canonical(
    db: Session,
    source_system_id: int,
    entity_type: str,
    source_records: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    mapping = get_column_mapping(db, source_system_id, entity_type)
    return map_records_to_canonical(source_records, mapping, entity_type)
