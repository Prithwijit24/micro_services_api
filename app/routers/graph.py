from fastapi import APIRouter, HTTPException

from app.models import (
    GraphQueryRequest,
    GraphQueryResponse,
    AddNodeRequest,
    AddNodeResponse,
    AddEdgeRequest,
    AddEdgeResponse,
)
from app.services.graph import GraphService

router = APIRouter(prefix="/graph")
svc = GraphService()


@router.post("/query", response_model=GraphQueryResponse)
async def query(req: GraphQueryRequest):
    try:
        return await svc.query(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_node", response_model=AddNodeResponse)
async def add_node(req: AddNodeRequest):
    try:
        return await svc.add_node(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_edge", response_model=AddEdgeResponse)
async def add_edge(req: AddEdgeRequest):
    try:
        return await svc.add_edge(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
