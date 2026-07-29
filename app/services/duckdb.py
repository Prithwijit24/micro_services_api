"""DuckDB OLAP service for analytical queries."""

import os
import logging
from typing import Any, Optional

import duckdb

from app.models import (
    DuckDBQueryRequest,
    DuckDBQueryResponse,
    DuckDBInsertRequest,
    DuckDBInsertResponse,
    DuckDBTableRequest,
    DuckDBTableResponse,
)

logger = logging.getLogger("duckdb")

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/data/duckdb/ai-stack.duckdb")


class DuckDBService:
    def __init__(self):
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            os.makedirs(os.path.dirname(DUCKDB_PATH), exist_ok=True)
            self._conn = duckdb.connect(DUCKDB_PATH)
        return self._conn

    async def query(self, req: DuckDBQueryRequest) -> DuckDBQueryResponse:
        conn = self._get_conn()
        try:
            result = conn.execute(req.sql, req.params or [])
            columns = [desc[0] for desc in result.description] if result.description else []
            rows = [dict(zip(columns, row)) for row in result.fetchall()] if columns else []
            return DuckDBQueryResponse(
                columns=columns,
                rows=rows,
                row_count=len(rows),
            )
        except Exception as e:
            logger.exception("DuckDB query failed")
            return DuckDBQueryResponse(
                columns=[],
                rows=[],
                row_count=0,
                error=str(e),
            )

    async def insert(self, req: DuckDBInsertRequest) -> DuckDBInsertResponse:
        conn = self._get_conn()
        try:
            cols = ", ".join(f'"{c}"' for c in req.columns)
            placeholders = ", ".join(["?"] * len(req.columns))
            sql = f'INSERT INTO "{req.table}" ({cols}) VALUES ({placeholders})'

            inserted = 0
            for row in req.rows:
                values = [row.get(c) for c in req.columns]
                conn.execute(sql, values)
                inserted += 1

            return DuckDBInsertResponse(
                table=req.table,
                inserted=inserted,
            )
        except Exception as e:
            logger.exception("DuckDB insert failed")
            return DuckDBInsertResponse(
                table=req.table,
                inserted=0,
                error=str(e),
            )

    def close(self):
        """Close the DuckDB connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    async def list_tables(self, req: DuckDBTableRequest) -> DuckDBTableResponse:
        conn = self._get_conn()
        try:
            tables_result = conn.execute(
                "SELECT table_name, table_schema FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'pg_catalog') ORDER BY table_schema, table_name"
            ).fetchall()

            tables = []
            for table_name, schema in tables_result:
                try:
                    count_result = conn.execute(f'SELECT COUNT(*) FROM "{schema}"."{table_name}"').fetchone()
                    row_count = count_result[0] if count_result else 0

                    cols_result = conn.execute(
                        f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table_name}' AND table_schema = '{schema}'"
                    ).fetchall()

                    columns = [
                        {"name": c[0], "type": c[1], "nullable": c[2] == "YES"}
                        for c in cols_result
                    ]
                    tables.append({
                        "name": f"{schema}.{table_name}" if schema != "main" else table_name,
                        "columns": columns,
                        "row_count": row_count,
                    })
                except Exception:
                    tables.append({"name": table_name, "columns": [], "row_count": 0})

            return DuckDBTableResponse(tables=tables)
        except Exception as e:
            logger.exception("DuckDB list_tables failed")
            return DuckDBTableResponse(tables=[], error=str(e))


duckdb_service = DuckDBService()
