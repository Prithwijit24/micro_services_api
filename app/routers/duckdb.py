from fastapi import APIRouter, HTTPException

from app.models import DuckDBQueryRequest, DuckDBQueryResponse
from app.models import DuckDBInsertRequest, DuckDBInsertResponse
from app.models import DuckDBTableRequest, DuckDBTableResponse
from app.services.duckdb import duckdb_service

router = APIRouter(prefix="/duckdb", tags=["duckdb"])


@router.post("/query", response_model=DuckDBQueryResponse)
async def query(req: DuckDBQueryRequest):
    try:
        return await duckdb_service.query(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insert", response_model=DuckDBInsertResponse)
async def insert(req: DuckDBInsertRequest):
    try:
        return await duckdb_service.insert(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables", response_model=DuckDBTableResponse)
async def list_tables():
    try:
        return await duckdb_service.list_tables(DuckDBTableRequest())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
