from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    # Walidujemy dokument wejściowy, żeby nie zapisywać pustej treści do pliku i SQL
    title: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=1)


class DocumentRead(BaseModel):
    # Włączamy from_attributes, żeby endpoint mógł zwrócić model SQLAlchemy jako odpowiedź Pydantic
    id: int
    title: str
    content: str
    file_path: str

    model_config = {"from_attributes": True}


class MatchResult(BaseModel):
    # Zwracamy score dopasowania, żeby klient widział jak mocny jest wynik wyszukiwania
    id: int
    title: str
    score: float


class FileLineCountResponse(BaseModel):
    # Zwracamy nazwę i liczbę wierszy, żeby test uploadu CSV nie musiał zapisywać pliku w bazie
    filename: str
    line_count: int
