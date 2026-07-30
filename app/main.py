from fastapi import FastAPI

from app.routers import register_all_routers
from app.middleware import setup_security
from app.auth import router as auth_router

app = FastAPI(
    title="AI Infra Stack",
    description="Unified API for search, browse, embed, and more",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Security middleware (CORS, rate limiting, auth, headers)
setup_security(app)

# Auth routes (token generation, API key management)
app.include_router(auth_router)

# All service routers
register_all_routers(app)


@app.get("/health")
async def health():
    return {"status": "ok"}
