from pydantic import BaseModel


class LayerStatus(BaseModel):
    # Zwracamy status warstwy, żeby szybko sprawdzić czy router stagingu odpowiada
    layer: str
    status: str


class StagingLoadResponse(BaseModel):
    # Zwracamy raport staging-load, żeby użytkownik widział wynik i braki mapowania
    import_batch_id: int
    raw_file_id: int
    entity_type: str
    records_in: int
    records_out: int
    import_status: str
    process_status: str
    missing_columns: dict[str, int]
    unrecognized_columns: dict[str, int]
