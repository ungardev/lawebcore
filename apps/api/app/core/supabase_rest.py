"""HTTP client for Supabase REST API (PostgREST)."""
import httpx
from app.core.config import settings


class SupabaseRest:
    def __init__(self):
        self.base_url = f"{settings.SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0,
        )

    async def close(self):
        await self.client.aclose()

    async def select(
        self,
        table: str,
        select: str = "*",
        filters: list[str] = None,
        order: str = None,
        limit: int = None,
        offset: int = None,
    ) -> list[dict]:
        """SELECT con filtros estilo PostgREST."""
        params = {"select": select}
        if filters:
            for f in filters:
                if "=" in f:
                    col, val = f.split("=", 1)
                    params[col] = val
                else:
                    params[f] = "eq.true"
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        resp = await self.client.get(f"/{table}", params=params)
        resp.raise_for_status()
        result = resp.json()
        return result if isinstance(result, list) else [result] if result else []

    async def select_one(
        self,
        table: str,
        select: str = "*",
        filters: list[str] = None,
    ) -> dict | None:
        """SELECT con limit=1."""
        results = await self.select(table=table, select=select, filters=filters, limit=1)
        return results[0] if results else None

    async def insert(
        self,
        table: str,
        values: dict,
        returning: str = "representation",
        on_conflict: list[str] = None,
        return_repr: bool = None,
    ) -> dict | None:
        """INSERT con soporte para UPSERT via Prefer header."""
        if return_repr is False:
            returning = "minimal"
        elif return_repr is True:
            returning = "representation"
        headers = dict(self.headers)
        prefs = [f"return={returning}"]
        if on_conflict:
            prefs.append(f"resolution=merge-duplicates")
            headers["Prefer"] = ",".join(prefs)
            headers["On-Conflig"] = f"({','.join(on_conflict)})"
        else:
            headers["Prefer"] = ",".join(prefs)
        resp = await self.client.post(f"/{table}", json=values, headers=headers)
        resp.raise_for_status()
        if returning == "minimal":
            return None
        result = resp.json()
        return result if isinstance(result, list) else result

    async def upsert(
        self,
        table: str,
        values: dict,
        on_conflict: list[str],
        returning: str = "representation",
    ) -> dict | None:
        """UPSERT (INSERT with ON CONFLICT)."""
        return await self.insert(table=table, values=values, returning=returning, on_conflict=on_conflict)

    async def update(
        self,
        table: str,
        filters: list[str],
        values: dict,
        returning: str = "representation",
    ) -> dict | None:
        """UPDATE con filtros."""
        params = {}
        for f in filters:
            if "=" in f:
                col, val = f.split("=", 1)
                params[col] = val
            else:
                params[f] = "eq.true"
        headers = dict(self.headers)
        headers["Prefer"] = f"return={returning}"
        resp = await self.client.patch(f"/{table}", params=params, json=values, headers=headers)
        resp.raise_for_status()
        if returning == "minimal":
            return None
        result = resp.json()
        return result if isinstance(result, list) else result

    async def delete(
        self,
        table: str,
        filters: list[str] = None,
    ) -> None:
        """DELETE con filtros."""
        params = {}
        if filters:
            for f in filters:
                if "=" in f:
                    col, val = f.split("=", 1)
                    params[col] = val
                else:
                    params[f] = "eq.true"
        resp = await self.client.delete(f"/{table}", params=params)
        resp.raise_for_status()

    async def rpc(self, function_name: str, params: dict = None):
        """Llamada a función RPC de Postgres."""
        resp = await self.client.post(f"/rpc/{function_name}", json=params or {})
        resp.raise_for_status()
        return resp.json()

    async def table(
        self,
        name: str,
        select: str = "*",
        eq_filters: dict = None,
        is_null_filters: list = None,
        order: str = None,
        limit: int = None,
        offset: int = None,
    ) -> list[dict]:
        """Backwards-compat builder shorthand used across the codebase.
        Translates eq_filters={col:val} and is_null_filters=[col] into
        PostgREST filter strings, then delegates to select()."""
        filters: list[str] = []
        if eq_filters:
            for col, val in eq_filters.items():
                if val is not None and val != "":
                    filters.append(f"{col}=eq.{val}")
        if is_null_filters:
            for col in is_null_filters:
                filters.append(f"{col}=is.null")
        return await self.select(
            table=name,
            select=select,
            filters=filters,
            order=order,
            limit=limit,
            offset=offset,
        )


supabase_rest = SupabaseRest()
