from pydantic import BaseModel


class LayerStatus(BaseModel):
    layer: str
    status: str


class RawLoadResponse(BaseModel):
    import_batch_id: int
    raw_file_id: int
    file_name: str
    file_type: str
    file_size: int
    file_hash: str
    records_in: int | None
    import_status: str
