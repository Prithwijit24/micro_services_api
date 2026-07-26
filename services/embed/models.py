from pydantic import BaseModel, Field


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="List of texts to embed")
    normalize: bool = Field(default=True)


class EmbedResponse(BaseModel):
    model: str
    dimensions: int
    embeddings: list[list[float]]
