"""MySQL database service via aiomysql."""

import os
import logging
from typing import Any, Optional

import aiomysql

from app.models import (
    MySqlQueryRequest,
    MySqlQueryResponse,
    MySqlInsertRequest,
    MySqlInsertResponse,
    MySqlTableRequest,
    MySqlTableResponse,
)

logger = logging.getLogger("mysql")

MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "aistack")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "changeme")
MYSQL_DB = os.getenv("MYSQL_DB", "aistack")


class MySqlService:
    def __init__(self):
        self._pool: Optional[aiomysql.Pool] = None

    async def _get_pool(self) -> aiomysql.Pool:
        if self._pool is None or self._pool.closed:
            self._pool = await aiomysql.create_pool(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DB,
                autocommit=True,
                minsize=1,
                maxsize=5,
            )
        return self._pool

    async def query(self, req: MySqlQueryRequest) -> MySqlQueryResponse:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(req.sql, req.params)
                if cur.description:
                    rows = await cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    return MySqlQueryResponse(
                        columns=columns,
                        rows=[dict(row) for row in rows],
                        row_count=len(rows),
                    )
                else:
                    return MySqlQueryResponse(
                        columns=[], rows=[], row_count=cur.rowcount
                    )

    async def insert(self, req: MySqlInsertRequest) -> MySqlInsertResponse:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                cols = ", ".join(f"`{c}`" for c in req.columns)
                placeholders = ", ".join(["%s"] * len(req.columns))
                sql = f"INSERT INTO `{req.table}` ({cols}) VALUES ({placeholders})"
                inserted = 0
                for row in req.rows:
                    await cur.execute(sql, list(row.values()))
                    inserted += cur.rowcount
                await conn.commit()
        return MySqlInsertResponse(table=req.table, inserted=inserted)

    async def list_tables(self, req: MySqlTableRequest) -> MySqlTableResponse:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SHOW TABLES")
                tables = [row[0] for row in await cur.fetchall()]

                table_info = []
                for table in tables:
                    await cur.execute(f"DESCRIBE `{table}`")
                    columns = [
                        {"name": col[0], "type": col[1], "nullable": col[2] == "YES"}
                        for col in await cur.fetchall()
                    ]
                    await cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                    count = (await cur.fetchone())[0]
                    table_info.append(
                        {"name": table, "columns": columns, "row_count": count}
                    )

        return MySqlQueryResponse(
            columns=["tables"],
            rows=table_info,
            row_count=len(table_info),
        ) if False else MySqlTableResponse(tables=table_info)
