from fastapi import APIRouter, HTTPException

from models import (
    GraphQueryRequest, GraphQueryResponse,
    AddNodeRequest, AddNodeResponse,
    AddEdgeRequest, AddEdgeResponse,
)
from service import graph_service

router = APIRouter(prefix="/graph")


@router.post("/query", response_model=GraphQueryResponse)
async def query(req: GraphQueryRequest):
    try:
        return await graph_service.query(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph query error: {e}")


@router.post("/add_node", response_model=AddNodeResponse)
async def add_node(req: AddNodeRequest):
    try:
        return await graph_service.add_node(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph add_node error: {e}")


@router.post("/add_edge", response_model=AddEdgeResponse)
async def add_edge(req: AddEdgeRequest):
    try:
        return await graph_service.add_edge(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph add_edge error: {e}")
