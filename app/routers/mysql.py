from fastapi import APIRouter, HTTPException

from app.models import (
    MySqlQueryRequest,
    MySqlQueryResponse,
    MySqlInsertRequest,
    MySqlInsertResponse,
    MySqlTableRequest,
    MySqlTableResponse,
)
from app.services.mysql import MySqlService

router = APIRouter(prefix="/mysql")
svc = MySqlService()


@router.post("/query", response_model=MySqlQueryResponse)
async def query(req: MySqlQueryRequest):
    try:
        return await svc.query(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insert", response_model=MySqlInsertResponse)
async def insert(req: MySqlInsertRequest):
    try:
        return await svc.insert(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tables", response_model=MySqlTableResponse)
async def list_tables(req: MySqlTableRequest):
    try:
        return await svc.list_tables(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
