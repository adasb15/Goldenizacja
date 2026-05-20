try:
    from pydantic import BaseModel
except ImportError:
    class BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)


class LayerStatus(BaseModel):
    # Ujednolicamy status warstwy, żeby healthchecki wszystkich etapów wyglądały tak samo
    layer: str
    status: str


class RawLoadResponse(BaseModel):
    # Zwracamy batch i raw_file_id, żeby użytkownik mógł od razu uruchomić następny krok w Postmanie
    import_batch_id: int
    raw_file_id: int
    file_name: str
    file_type: str
    file_size: int
    file_hash: str
    records_in: int | None
    import_status: str


class RelationalQueryInfo(BaseModel):
    query_name: str
    source_system_code: str
    entity_type: str
    description: str
