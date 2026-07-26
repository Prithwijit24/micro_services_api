from typing import Optional, Any
from pydantic import BaseModel, Field


class VectorRecord(BaseModel):
    id: str
    embedding: list[float]
    document: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpsertRequest(BaseModel):
    collection: str
    records: list[VectorRecord] = Field(..., min_length=1)


class UpsertResponse(BaseModel):
    collection: str
    upserted: int


class SearchRequest(BaseModel):
    collection: str
    query_embedding: list[float]
    top_k: int = Field(default=5, ge=1, le=100)
    where: Optional[dict[str, Any]] = None


class SearchMatch(BaseModel):
    id: str
    score: float
    document: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    collection: str
    matches: list[SearchMatch]


class DeleteRequest(BaseModel):
    collection: str
    ids: list[str] = Field(..., min_length=1)


class DeleteResponse(BaseModel):
    collection: str
    deleted: int
