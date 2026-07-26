from pydantic import BaseModel


class ServiceHealth(BaseModel):
    service: str
    status: str
    detail: str | None = None


class GatewayHealthResponse(BaseModel):
    gateway: str = "ok"
    services: list[ServiceHealth]
