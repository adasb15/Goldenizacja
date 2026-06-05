from pydantic import BaseModel


class LayerStatus(BaseModel):
    # Status mówi, czy endpoint preprocessing jest gotowy do przyjęcia danych ze stagingu
    layer: str
    status: str


class PreprocessingLoadResponse(BaseModel):
    # Raportujemy liczniki, żeby łatwo porównać wejście stagingu z wyjściem preprocessing
    import_batch_id: int
    raw_file_id: int
    entity_type: str
    records_in: int
    records_out: int
    process_status: str
