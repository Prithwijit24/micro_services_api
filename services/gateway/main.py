from fastapi import FastAPI

from routers.proxy import router as proxy_router
from service import gateway_service, SERVICE_URLS
from models import GatewayHealthResponse, ServiceHealth

app = FastAPI(
    title="API Gateway",
    description="Single entry point that routes requests to internal AI infrastructure microservices",
    version="1.0.0",
)


@app.get("/health", response_model=GatewayHealthResponse)
async def health():
    results = []
    for name in SERVICE_URLS:
        status, detail = await gateway_service.check_health(name)
        results.append(ServiceHealth(service=name, status=status, detail=detail))
    return GatewayHealthResponse(services=results)


@app.get("/")
async def root():
    return {
        "message": "AI Infrastructure API Gateway",
        "routes": list(SERVICE_URLS.keys()),
        "health_check": "/health",
    }


# Catch-all proxy must be included last so /health and / take precedence
app.include_router(proxy_router)
