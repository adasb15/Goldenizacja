from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=1)


class DocumentRead(BaseModel):
    id: int
    title: str
    content: str
    file_path: str

    model_config = {"from_attributes": True}


class MatchResult(BaseModel):
    id: int
    title: str
    score: float


class FileLineCountResponse(BaseModel):
    filename: str
    line_count: int
