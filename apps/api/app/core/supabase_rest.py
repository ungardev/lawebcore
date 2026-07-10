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

    async def table(
        self,
        table: str,
        select: str = "*",
        eq_filters: dict = None,
        is_null_filters: list = None,
        limit: int = None,
        order: str = None,
    ):
        params = {"select": select}
        if eq_filters:
            for key, val in eq_filters.items():
                params[key] = f"eq.{val}"
        if is_null_filters:
            for col in is_null_filters:
                params[col] = "is.null"
        if limit:
            params["limit"] = limit
        if order:
            params["order"] = order
        resp = await self.client.get(f"/{table}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def insert(self, table: str, data: dict | list, return_repr: bool = True):
        headers = dict(self.headers)
        if return_repr:
            headers["Prefer"] = "return=representation"
        resp = await self.client.post(f"/{table}", json=data, headers=headers)
        resp.raise_for_status()
        return resp.json() if return_repr else None

    async def update(
        self,
        table: str,
        data: dict,
        eq_filters: dict = None,
        is_null_filters: list = None,
    ):
        params = {}
        if eq_filters:
            params.update({k: f"eq.{v}" for k, v in eq_filters.items()})
        if is_null_filters:
            for col in is_null_filters:
                params[col] = "is.null"
        headers = dict(self.headers)
        headers["Prefer"] = "return=representation"
        resp = await self.client.patch(f"/{table}", params=params, json=data, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, table: str, eq_filters: dict = None, is_null_filters: list = None):
        params = {}
        if eq_filters:
            params.update({k: f"eq.{v}" for k, v in eq_filters.items()})
        if is_null_filters:
            for col in is_null_filters:
                params[col] = "is.null"
        resp = await self.client.delete(f"/{table}", params=params)
        resp.raise_for_status()

    async def rpc(self, function_name: str, params: dict = None):
        resp = await self.client.post(f"/rpc/{function_name}", json=params or {})
        resp.raise_for_status()
        return resp.json()


supabase_rest = SupabaseRest()
