from typing import Optional
from pydantic import BaseModel, Field


class TextEmbeddingRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1)


class ImageEmbeddingRequest(BaseModel):
    image_urls: Optional[list[str]] = None
    images_base64: Optional[list[str]] = None


class EmbeddingResponse(BaseModel):
    model: str
    dimensions: int
    embeddings: list[list[float]]


class SimilarityRequest(BaseModel):
    text: str
    image_urls: Optional[list[str]] = None
    images_base64: Optional[list[str]] = None


class SimilarityResponse(BaseModel):
    text: str
    scores: list[float]
