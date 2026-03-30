from pydantic import BaseModel


class LayerStatus(BaseModel):
    layer: str
    status: str
