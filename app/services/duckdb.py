"""DuckDB OLAP service for analytical queries."""

from __future__ import annotations

import asyncio
import os
import re
from concurrent.futures import ThreadPoolExecutor

from app.services.executors import ManagedExecutor
from typing import Any, Optional

import duckdb

from app.models import (
    DuckDBInsertRequest,
    DuckDBInsertResponse,
    DuckDBQueryRequest,
    DuckDBQueryResponse,
    DuckDBTableResponse,
)

logger = __import__("logging").getLogger("duckdb")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/data/duckdb/ai-stack.duckdb")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


def _quote(value: str) -> str:
    return f'"{_identifier(value)}"'


class DuckDBService:
    def __init__(self):
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._executor = ManagedExecutor(1, "duckdb")

    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            directory = os.path.dirname(DUCKDB_PATH)
            if directory:
                os.makedirs(directory, exist_ok=True)
            self._conn = duckdb.connect(DUCKDB_PATH)
        return self._conn

    def _query_sync(self, req: DuckDBQueryRequest) -> DuckDBQueryResponse:
        conn = self._get_conn()
        try:
            result = conn.execute(req.sql, req.params or [])
            columns = [description[0] for description in result.description] if result.description else []
            rows = [dict(zip(columns, row)) for row in result.fetchall()] if columns else []
            return DuckDBQueryResponse(columns=columns, rows=rows, row_count=len(rows))
        except Exception as exc:
            logger.exception("DuckDB query failed")
            return DuckDBQueryResponse(columns=[], rows=[], row_count=0, error=str(exc))

    async def query(self, req: DuckDBQueryRequest) -> DuckDBQueryResponse:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor.get(), self._query_sync, req)

    def _insert_sync(self, req: DuckDBInsertRequest) -> DuckDBInsertResponse:
        conn = self._get_conn()
        try:
            table = _quote(req.table)
            columns = ", ".join(_quote(column) for column in req.columns)
            placeholders = ", ".join("?" for _ in req.columns)
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            for row in req.rows:
                conn.execute(sql, [row.get(column) for column in req.columns])
            return DuckDBInsertResponse(table=req.table, inserted=len(req.rows))
        except Exception as exc:
            logger.exception("DuckDB insert failed")
            return DuckDBInsertResponse(table=req.table, inserted=0, error=str(exc))

    async def insert(self, req: DuckDBInsertRequest) -> DuckDBInsertResponse:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor.get(), self._insert_sync, req)

    def _list_tables_sync(self) -> DuckDBTableResponse:
        conn = self._get_conn()
        try:
            table_rows = conn.execute(
                "SELECT table_name, table_schema FROM information_schema.tables "
                "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') "
                "ORDER BY table_schema, table_name"
            ).fetchall()
            tables: list[dict[str, Any]] = []
            for table_name, schema in table_rows:
                try:
                    count = conn.execute(
                        f"SELECT COUNT(*) FROM {_quote(schema)}.{_quote(table_name)}"
                    ).fetchone()
                    columns = conn.execute(
                        "SELECT column_name, data_type, is_nullable "
                        "FROM information_schema.columns "
                        "WHERE table_name = ? AND table_schema = ?",
                        [table_name, schema],
                    ).fetchall()
                    tables.append({
                        "name": f"{schema}.{table_name}" if schema != "main" else table_name,
                        "columns": [
                            {"name": name, "type": data_type, "nullable": nullable == "YES"}
                            for name, data_type, nullable in columns
                        ],
                        "row_count": count[0] if count else 0,
                    })
                except Exception:
                    logger.exception("DuckDB table inspection failed for %s.%s", schema, table_name)
                    tables.append({"name": table_name, "columns": [], "row_count": 0})
            return DuckDBTableResponse(tables=tables)
        except Exception as exc:
            logger.exception("DuckDB list_tables failed")
            return DuckDBTableResponse(tables=[], error=str(exc))

    async def list_tables(self) -> DuckDBTableResponse:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor.get(), self._list_tables_sync)

    def close(self) -> None:
        # Drain the serialized worker before closing the connection it owns.
        self._executor.close()
        if self._conn is not None:
            self._conn.close()
            self._conn = None


duckdb_service = DuckDBService()
