"""Meta Business API client — Instagram + Facebook vía Graph API."""

from typing import Any

import httpx

from app.core.config import settings


class MetaClient:
    """Cliente para Meta Business Graph API."""

    BASE_URL = "https://graph.facebook.com/v21.0"
    TIMEOUT = 30.0

    def __init__(
        self,
        app_id: str | None = None,
        app_secret: str | None = None,
        access_token: str | None = None,
    ):
        self.app_id = app_id or settings.META_APP_ID
        self.app_secret = app_secret or settings.META_APP_SECRET
        self.access_token = access_token or settings.META_ACCESS_TOKEN
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=self.TIMEOUT,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_access_token_info(self) -> dict[str, Any]:
        """Verifica el token actual y sus permisos."""
        client = await self._get_client()
        params = {
            "input_token": self.access_token,
            "access_token": f"{self.app_id}|{self.app_secret}",
        }
        response = await client.get("/debug_token", params=params)
        response.raise_for_status()
        return response.json()

    async def get_instagram_accounts(self, page_id: str) -> list[dict[str, Any]]:
        """Obtiene cuentas de Instagram asociadas a una Page."""
        client = await self._get_client()
        params = {
            "fields": "instagram_business_account{id,username,name,followers_count,follows_count,media_count}",
            "access_token": self.access_token,
        }
        response = await client.get(f"/{page_id}", params=params)
        response.raise_for_status()
        data = response.json()
        return [data.get("instagram_business_account", {})]

    async def get_media(
        self,
        ig_user_id: str,
        fields: str = "id,caption,media_type,permalink,thumbnail_url,timestamp,like_count,comments_count,reach,saved,share",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Obtiene las últimas publicaciones de un usuario de Instagram."""
        client = await self._get_client()
        params = {
            "fields": fields,
            "access_token": self.access_token,
            "limit": limit,
        }
        response = await client.get(f"/{ig_user_id}/media", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    async def get_media_insights(
        self,
        ig_media_id: str,
    ) -> dict[str, Any]:
        """Obtiene métricas de una publicación específica."""
        client = await self._get_client()
        params = {
            "fields": "insights.metric(likes,comments,shares,saves,reach,impressions,profile_visits,replies)",
            "access_token": self.access_token,
        }
        response = await client.get(f"/{ig_media_id}/insights", params=params)
        response.raise_for_status()
        return response.json()

    async def get_user_insights(
        self,
        ig_user_id: str,
        metric: str = "follower_count,follows_count,media_count",
        period: str = "day",
    ) -> list[dict[str, Any]]:
        """Obtiene métricas agregadas del usuario."""
        client = await self._get_client()
        params = {
            "metric": metric,
            "period": period,
            "access_token": self.access_token,
        }
        response = await client.get(f"/{ig_user_id}/insights", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    async def search_pages(
        self,
        query: str,
        fields: str = "id,name,fan_count,followers_count",
    ) -> list[dict[str, Any]]:
        """Busca páginas de Facebook por nombre (para discovery de influencers)."""
        client = await self._get_client()
        params = {
            "q": query,
            "type": "page",
            "fields": fields,
            "access_token": self.access_token,
        }
        response = await client.get("/search", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])


meta_client = MetaClient()
