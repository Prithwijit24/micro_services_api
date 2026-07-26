from pydantic import BaseModel, Field


class RerankRequest(BaseModel):
    query: str
    documents: list[str] = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1)


class RerankedDocument(BaseModel):
    index: int
    document: str
    score: float


class RerankResponse(BaseModel):
    model: str
    query: str
    results: list[RerankedDocument]
