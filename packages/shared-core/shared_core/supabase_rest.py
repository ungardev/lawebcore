"""Database client using asyncpg — connects directly to Railway Postgres."""

import json
import logging
import re
import time
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any

import asyncpg

from shared_core.config import settings


logger = logging.getLogger(__name__)

_ORDER_DIR_PATTERN = re.compile(r"\b(\w+)\.(\w+)\b", re.IGNORECASE)

_POSTGREST_PREFIXES = (
    "eq.", "neq.", "gt.", "gte.", "lt.", "lte.",
    "like.", "ilike.", "in.", "is.", "match.",
    "fts.", "plfts.", "phfts.", "wfts.",
    "cs.", "cd.", "ov.", "sl.", "sr.",
    "nxr.", "nxl.", "adj.", "not.",
)


def _strip_postgrest_op(val: str) -> str:
    for prefix in _POSTGREST_PREFIXES:
        if val.startswith(prefix):
            return val[len(prefix):]
    return val


def _normalize_order(order: str) -> str:
    """Convert 'col.desc' or 'col.asc' to 'col DESC' or 'col ASC'.

    asyncpg's PostgreSQL parser is strict and treats 'col.desc' as
    a table.column reference. Adding explicit space fixes it.
    """
    def _replace_dir(m: re.Match) -> str:
        col, direction = m.group(1), m.group(2).lower()
        if direction in ("asc", "desc"):
            return f"{col} {direction.upper()}"
        return m.group(0)
    return _ORDER_DIR_PATTERN.sub(_replace_dir, order)


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
            logger.info("[supabase_rest] Creating new asyncpg pool for %s", self._dsn.split("@")[-1])
            self._pool = await asyncpg.create_pool(
                self._dsn,
                min_size=2,
                max_size=20,
                command_timeout=30,
                init=self._init_connection,
            )
            logger.info("[supabase_rest] Pool created successfully")
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

    def _parse_filters(self, filters: list[str] | None, param_offset: int = 0) -> tuple[str, list[Any]]:
        if not filters:
            return "", []
        conds = []
        params: list[Any] = []
        for f in filters:
            if "=" in f:
                col, val = f.split("=", 1)
                val = _strip_postgrest_op(val)
                conds.append(f"{col} = ${len(params) + 1 + param_offset}")
                params.append(self._maybe_parse_datetime(val))
            elif f.startswith("!"):
                continue
            elif f.lower().endswith(".is.null"):
                col = f[:-8]
                conds.append(f"{col} IS NULL")
            elif ".gte." in f:
                col, val = f.split(".gte.", 1)
                conds.append(f"{col} >= ${len(params) + 1 + param_offset}")
                params.append(self._maybe_parse_datetime(val))
            elif ".lte." in f:
                col, val = f.split(".lte.", 1)
                conds.append(f"{col} <= ${len(params) + 1 + param_offset}")
                params.append(self._maybe_parse_datetime(val))
            elif ".gt." in f:
                col, val = f.split(".gt.", 1)
                conds.append(f"{col} > ${len(params) + 1 + param_offset}")
                params.append(self._maybe_parse_datetime(val))
            elif ".lt." in f:
                col, val = f.split(".lt.", 1)
                conds.append(f"{col} < ${len(params) + 1 + param_offset}")
                params.append(self._maybe_parse_datetime(val))
            elif ".in." in f:
                col, rest = f.split(".in.", 1)
                vals = rest.strip("()").split(",")
                base = len(params) + 1 + param_offset
                placeholders = [f"${base + i}" for i in range(len(vals))]
                conds.append(f"{col} IN ({','.join(placeholders)})")
                params.extend(self._maybe_parse_datetime(v) for v in vals)
            elif ".ilike." in f:
                col, val = f.split(".ilike.", 1)
                conds.append(f"{col} ILIKE ${len(params) + 1 + param_offset}")
                params.append(f"%{val}%")
            else:
                conds.append(f"{f} = true")
        where = " WHERE " + " AND ".join(conds) if conds else ""
        logger.debug("[supabase_rest._parse_filters] filters=%s -> where=%s params=%s", filters, where, params)
        return where, params

    def _maybe_parse_datetime(self, val: str) -> Any:
        if not isinstance(val, str):
            return val
        if len(val) < 10 or val[4] != "-" or val[7] != "-":
            return val
        try:
            normalized = val.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except ValueError:
            return val

    def _val_to_pg(self, v: Any) -> Any:
        if isinstance(v, dict):
            return json.dumps(v, default=str)
        elif isinstance(v, list):
            return v
        elif isinstance(v, bool):
            return v
        elif v is None:
            return None
        elif isinstance(v, uuid.UUID):
            return str(v)
        elif isinstance(v, datetime):
            return v
        elif isinstance(v, date) and not isinstance(v, datetime):
            return v
        else:
            return v

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
            normalized_order = _normalize_order(order)
            logger.info("[supabase_rest.select] order normalized: %r -> %r", order, normalized_order)
            query += f" ORDER BY {normalized_order}"
        if limit is not None:
            query += f" LIMIT {limit}"
        if offset is not None:
            query += f" OFFSET {offset}"

        logger.info("[supabase_rest.select] EXEC: %s", query)
        logger.info("[supabase_rest.select] PARAMS: %s", params)
        t0 = time.time()
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
            elapsed_ms = (time.time() - t0) * 1000
            logger.info("[supabase_rest.select] OK: %d rows in %.2fms", len(rows), elapsed_ms)
            return [_row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error("[supabase_rest.select] FAILED: %s | query=%s params=%s", e, query, params, exc_info=True)
            raise

    async def select_one(
        self,
        table: str,
        select: str = "*",
        filters: list[str] | None = None,
    ) -> dict | None:
        rows = await self.select(table, select, filters, limit=1)
        return rows[0] if rows else None

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
        logger.info("[supabase_rest.insert] EXEC: %s vals=%s", sql, vals)
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(sql, *vals)
            logger.info("[supabase_rest.insert] OK: %s", dict(row) if row else None)
            return _row_to_dict(row) if row else None
        except Exception as e:
            logger.error("[supabase_rest.insert] FAILED: %s | sql=%s vals=%s", e, sql, vals, exc_info=True)
            raise

    async def upsert_many(
        self,
        table: str,
        records: list[dict],
        on_conflict: list[str],
        returning: str = "representation",
    ) -> list[dict]:
        """Batch upsert. All records must have the same keys. Uses ON CONFLICT DO UPDATE."""
        if not records:
            return []
        pool = await self._ensure_pool()
        cols = list(records[0].keys())
        conflict_cols = ",".join(on_conflict)
        set_parts = [f"{c}=EXCLUDED.{c}" for c in cols if c not in on_conflict]

        rows: list[list[Any]] = []
        placeholder_lists: list[str] = []
        param_offset = 0
        for record in records:
            row_vals = [self._val_to_pg(record.get(c)) for c in cols]
            rows.append(row_vals)
            phs = [f"${param_offset + i + 1}" for i in range(len(cols))]
            placeholder_lists.append(f"({','.join(phs)})")
            param_offset += len(cols)

        all_vals: list[Any] = []
        for row in rows:
            all_vals.extend(row)

        sql = (
            f"INSERT INTO {table} ({','.join(cols)}) "
            f"VALUES {','.join(placeholder_lists)} "
            f"ON CONFLICT ({conflict_cols}) DO UPDATE SET {','.join(set_parts)}"
        )
        if returning == "representation":
            sql += " RETURNING id"
        elif returning == "minimal":
            sql += " RETURNING 1"
        logger.info("[supabase_rest.upsert_many] EXEC: %s", sql)
        try:
            async with pool.acquire() as conn:
                result = await conn.fetch(sql, *all_vals)
            logger.info("[supabase_rest.upsert_many] OK: %d rows", len(result))
            return [dict(r) for r in result]
        except Exception as e:
            logger.error("[supabase_rest.upsert_many] FAILED: %s | sql=%s", e, sql, exc_info=True)
            raise

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
        logger.info("[supabase_rest.upsert] EXEC: %s", sql)
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *vals)
            logger.info("[supabase_rest.upsert] OK: %d rows", len(rows))
            return [_row_to_dict(r) for r in rows] if rows else None
        except Exception as e:
            logger.error("[supabase_rest.upsert] FAILED: %s | sql=%s", e, sql, exc_info=True)
            raise

    async def update(
        self,
        table: str,
        filters: list[str],
        values: dict,
        returning: str = "representation",
    ) -> dict | None:
        pool = await self._ensure_pool()
        set_cols = [f"{k}=${i+1}" for i, k in enumerate(values.keys())]
        vals = [self._val_to_pg(v) for v in values.values()]
        where, wparams = self._parse_filters(filters, param_offset=len(vals))
        sql = f"UPDATE {table} SET {','.join(set_cols)}{where}"
        if returning != "minimal":
            sql += " RETURNING *"
        logger.info("[supabase_rest.update] EXEC: %s vals=%s wparams=%s", sql, vals, wparams)
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *vals, *wparams)
            logger.info("[supabase_rest.update] OK: %d rows", len(rows))
            return [_row_to_dict(r) for r in rows] if rows else None
        except Exception as e:
            logger.error("[supabase_rest.update] FAILED: %s | sql=%s vals=%s wparams=%s", e, sql, vals, wparams, exc_info=True)
            raise

    async def delete(
        self,
        table: str,
        filters: list[str] | None = None,
    ) -> None:
        pool = await self._ensure_pool()
        where, params = self._parse_filters(filters)
        sql = f"DELETE FROM {table}{where}"
        logger.info("[supabase_rest.delete] EXEC: %s params=%s", sql, params)
        try:
            async with pool.acquire() as conn:
                await conn.execute(sql, *params)
            logger.info("[supabase_rest.delete] OK")
        except Exception as e:
            logger.error("[supabase_rest.delete] FAILED: %s | sql=%s params=%s", e, sql, params, exc_info=True)
            raise

    async def rpc(self, function_name: str, params: dict | None = None) -> Any:
        pool = await self._ensure_pool()
        args = params or {}
        if not args:
            sql = f"SELECT * FROM {function_name}()"
            logger.info("[supabase_rest.rpc] EXEC: %s", sql)
            async with pool.acquire() as conn:
                row = await conn.fetchrow(sql)
            logger.info("[supabase_rest.rpc] OK: %s", dict(row) if row else None)
            return _row_to_dict(row) if row else None
        arg_keys = list(args.keys())
        arg_vals = [args[k] for k in arg_keys]
        placeholders = [f"${i+1}" for i in range(len(arg_keys))]
        sql = f"SELECT * FROM {function_name}({','.join(placeholders)})"
        logger.info("[supabase_rest.rpc] EXEC: %s args=%s", sql, args)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, *arg_vals)
        logger.info("[supabase_rest.rpc] OK: %s", dict(row) if row else None)
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
