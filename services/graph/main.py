from fastapi import FastAPI

from routers.graph import router as graph_router
from service import graph_service

app = FastAPI(title="Graph API", description="Knowledge graph API wrapping Neo4j", version="1.0.0")

app.include_router(graph_router, tags=["graph"])


@app.on_event("shutdown")
async def shutdown():
    await graph_service.close()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "graph"}
