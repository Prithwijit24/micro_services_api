from typing import Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


class BrowseRequest(BaseModel):
    url: HttpUrl
    action: Literal["screenshot", "content", "click", "fill_form"] = "content"
    selector: Optional[str] = Field(default=None, description="CSS selector for click/fill actions")
    text: Optional[str] = Field(default=None, description="Text to fill for fill_form action")
    full_page: bool = Field(default=True, description="Full page screenshot")
    wait_ms: int = Field(default=1000, ge=0, le=30000)


class BrowseResponse(BaseModel):
    url: str
    action: str
    content: Optional[str] = None
    screenshot_base64: Optional[str] = None
    success: bool = True
    message: Optional[str] = None
