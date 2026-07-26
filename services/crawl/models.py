from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class CrawlRequest(BaseModel):
    url: HttpUrl
    only_main_content: bool = Field(default=True)
    include_html: bool = Field(default=False)
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)


class CrawlResponse(BaseModel):
    url: str
    markdown: str
    html: Optional[str] = None
    title: Optional[str] = None
    status_code: Optional[int] = None
