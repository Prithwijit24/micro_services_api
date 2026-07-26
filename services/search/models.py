from typing import Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    categories: Optional[str] = Field(default="general", description="SearXNG category filter")
    language: Optional[str] = Field(default="en")
    max_results: int = Field(default=10, ge=1, le=50)
    safesearch: int = Field(default=1, ge=0, le=2)


class SearchResultItem(BaseModel):
    title: str
    url: str
    content: Optional[str] = None
    engine: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    number_of_results: int
    results: list[SearchResultItem]
