from pydantic import BaseModel


class LayerStatus(BaseModel):
    layer: str
    status: str


class StagingLoadResponse(BaseModel):
    import_batch_id: int
    raw_file_id: int
    entity_type: str
    records_in: int
    records_out: int
    import_status: str
    process_status: str
    missing_columns: dict[str, int]
    unrecognized_columns: dict[str, int]
