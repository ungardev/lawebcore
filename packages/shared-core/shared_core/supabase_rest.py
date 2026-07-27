"""Database client using asyncpg — connects directly to Railway Postgres."""

import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any

import asyncpg

from shared_core.config import settings


def _pg_to_json(val: Any) -> Any:
    """Convert asyncpg types to JSON-serializable Python types."""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    if isinstance(val, list):
        return [_pg_to_json(v) for v in val]
    if isinstance(val, dict):
        return {k: _pg_to_json(v) for k, v in val.items()}
    return val


def _row_to_dict(row: asyncpg.Record) -> dict:
    """Convert asyncpg Record to dict with proper type serialization."""
    return {k: _pg_to_json(v) for k, v in row.items()}


class RailwayPg:
    def __init__(self, dsn: str | None = None):
        self._pool: asyncpg.Pool | None = None
        self._dsn = dsn or settings.DATABASE_URL
        if self._dsn and self._dsn.startswith("postgresql+asyncpg://"):
            self._dsn = self._dsn.replace("postgresql+asyncpg://", "postgresql://")

    async def _init_connection(self, conn: asyncpg.Connection) -> None:
        await conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )
        await conn.set_type_codec(
            "json",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )

    async def _ensure_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self._dsn,
                min_size=2,
                max_size=20,
                command_timeout=30,
                init=self._init_connection,
            )
        return self._pool

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def healthcheck(self) -> bool:
        try:
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    def _parse_filters(self, filters: list[str] | None) -> tuple[str, list[Any]]:
        if not filters:
            return "", []
        conds = []
        params: list[Any] = []
        for f in filters:
            if "=" in f:
                col, val = f.split("=", 1)
                conds.append(f"{col} = ${len(params) + 1}")
                params.append(val)
            elif f.startswith("!"):
                continue
            elif f.lower().endswith(".is.null"):
                col = f[:-8]
                conds.append(f"{col} IS NULL")
            elif ".gte." in f:
                col, val = f.split(".gte.", 1)
                conds.append(f"{col} >= ${len(params) + 1}")
                params.append(val)
            elif ".lte." in f:
                col, val = f.split(".lte.", 1)
                conds.append(f"{col} <= ${len(params) + 1}")
                params.append(val)
            elif ".gt." in f:
                col, val = f.split(".gt.", 1)
                conds.append(f"{col} > ${len(params) + 1}")
                params.append(val)
            elif ".lt." in f:
                col, val = f.split(".lt.", 1)
                conds.append(f"{col} < ${len(params) + 1}")
                params.append(val)
            elif ".in." in f:
                col, rest = f.split(".in.", 1)
                vals = rest.strip("()").split(",")
                placeholders = [f"${params.index(v) + 1}" if v in params else f"${len(params) + 1}" for v in vals]
                conds.append(f"{col} IN ({','.join(placeholders)})")
                params.extend(vals)
            elif ".ilike." in f:
                col, val = f.split(".ilike.", 1)
                conds.append(f"{col} ILIKE ${len(params) + 1}")
                params.append(f"%{val}%")
            else:
                conds.append(f"{f} = true")
        where = " WHERE " + " AND ".join(conds) if conds else ""
        return where, params

    async def select(
        self,
        table: str,
        select: str = "*",
        filters: list[str] | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        pool = await self._ensure_pool()
        where, params = self._parse_filters(filters)
        query = f"SELECT {select} FROM {table}{where}"
        if order:
            query += f" ORDER BY {order}"
        if limit is not None:
            query += f" LIMIT {limit}"
        if offset is not None:
            query += f" OFFSET {offset}"
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [_row_to_dict(r) for r in rows]

    async def select_one(
        self,
        table: str,
        select: str = "*",
        filters: list[str] | None = None,
    ) -> dict | None:
        rows = await self.select(table, select, filters, limit=1)
        return rows[0] if rows else None

    def _val_to_pg(self, v: Any) -> Any:
        if isinstance(v, (dict, list)):
            return json.dumps(v)
        elif isinstance(v, bool):
            return v
        elif v is None:
            return None
        elif isinstance(v, uuid.UUID):
            return str(v)
        else:
            return v

    async def insert(
        self,
        table: str,
        values: dict,
        returning: str = "representation",
        on_conflict: list[str] | None = None,
        return_repr: bool | None = None,
    ) -> dict | None:
        pool = await self._ensure_pool()
        cols = list(values.keys())
        placeholders = [f"${i+1}" for i in range(len(cols))]
        vals = [self._val_to_pg(v) for v in values.values()]
        sql = f'INSERT INTO {table} ({",".join(cols)}) VALUES ({",".join(placeholders)})'
        if returning == "minimal" or return_repr is False:
            sql += " RETURNING id"
        else:
            sql += " RETURNING *"
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, *vals)
            return _row_to_dict(row) if row else None

    async def upsert(
        self,
        table: str,
        values: dict,
        on_conflict: list[str],
        returning: str = "representation",
    ) -> dict | None:
        pool = await self._ensure_pool()
        cols = list(values.keys())
        placeholders = [f"${i+1}" for i in range(len(cols))]
        vals = [self._val_to_pg(v) for v in values.values()]
        conflict_cols = ",".join(on_conflict)
        set_parts = [f"{c}=EXCLUDED.{c}" for c in cols if c not in on_conflict]
        sql = f'INSERT INTO {table} ({",".join(cols)}) VALUES ({",".join(placeholders)}) ON CONFLICT ({conflict_cols}) DO UPDATE SET {",".join(set_parts)}'
        if returning != "minimal":
            sql += " RETURNING *"
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *vals)
            return [_row_to_dict(r) for r in rows] if rows else None

    async def update(
        self,
        table: str,
        filters: list[str],
        values: dict,
        returning: str = "representation",
    ) -> dict | None:
        pool = await self._ensure_pool()
        where, wparams = self._parse_filters(filters)
        set_cols = [f"{k}=${i+1}" for i, k in enumerate(values.keys())]
        vals = [self._val_to_pg(v) for v in values.values()]
        sql = f"UPDATE {table} SET {','.join(set_cols)}{where}"
        if returning != "minimal":
            sql += " RETURNING *"
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *vals, *wparams)
            return [_row_to_dict(r) for r in rows] if rows else None

    async def delete(
        self,
        table: str,
        filters: list[str] | None = None,
    ) -> None:
        pool = await self._ensure_pool()
        where, params = self._parse_filters(filters)
        sql = f"DELETE FROM {table}{where}"
        async with pool.acquire() as conn:
            await conn.execute(sql, *params)

    async def rpc(self, function_name: str, params: dict | None = None) -> Any:
        pool = await self._ensure_pool()
        args = params or {}
        if not args:
            sql = f"SELECT * FROM {function_name}()"
            async with pool.acquire() as conn:
                row = await conn.fetchrow(sql)
                return _row_to_dict(row) if row else None
        arg_keys = list(args.keys())
        arg_vals = [args[k] for k in arg_keys]
        placeholders = [f"${i+1}" for i in range(len(arg_keys))]
        sql = f"SELECT * FROM {function_name}({','.join(placeholders)})"
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, *arg_vals)
            return _row_to_dict(row) if row else None

    async def table(
        self,
        name: str,
        select: str = "*",
        eq_filters: dict | None = None,
        is_null_filters: list[str] | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        filters: list[str] = []
        if eq_filters:
            for col, val in eq_filters.items():
                if val is not None and val != "":
                    filters.append(f"{col}={val}")
        if is_null_filters:
            for col in is_null_filters:
                filters.append(f"{col}.is.null")
        return await self.select(name, select, filters, order, limit, offset)


_railway_pg: RailwayPg | None = None


def get_railway_pg() -> RailwayPg:
    global _railway_pg
    if _railway_pg is None:
        _railway_pg = RailwayPg()
    return _railway_pg


class SupabaseRest(RailwayPg):
    pass


def supabase_rest_factory() -> RailwayPg:
    return get_railway_pg()


supabase_rest: RailwayPg = get_railway_pg()
