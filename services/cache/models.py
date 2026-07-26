from typing import Optional, Any
from pydantic import BaseModel, Field


class SetRequest(BaseModel):
    key: str
    value: Any
    ttl_seconds: Optional[int] = Field(default=None, ge=1)


class SetResponse(BaseModel):
    key: str
    success: bool


class GetResponse(BaseModel):
    key: str
    value: Optional[Any] = None
    found: bool


class DeleteResponse(BaseModel):
    key: str
    deleted: bool
