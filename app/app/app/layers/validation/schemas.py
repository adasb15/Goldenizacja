from pydantic import BaseModel


class LayerStatus(BaseModel):
    # Status pozwala sprawdzić, czy etap walidacji jest podpięty pod API
    layer: str
    status: str


class ValidationLoadResponse(BaseModel):
    # Raport pokazuje, ile reguł przeszło i ile oznaczyło dane jako błędne
    import_batch_id: int
    raw_file_id: int
    entity_type: str
    records_in: int
    validation_results: int
    passed: int
    failed: int
    process_status: str
