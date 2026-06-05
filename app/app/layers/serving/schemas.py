from pydantic import BaseModel


class LayerStatus(BaseModel):
    # Ujednolicamy odpowiedź statusu, żeby testy wszystkich warstw wyglądały tak samo
    layer: str
    status: str
