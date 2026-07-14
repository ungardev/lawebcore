"""TikTok Research API client."""

from typing import Any

import httpx

from app.core.config import settings


class TikTokClient:
    """Cliente para TikTok Research API."""

    BASE_URL = "https://open.tiktokapis.com/v2"
    TIMEOUT = 30.0

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.TIKTOK_RESEARCH_API_KEY
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.TIMEOUT,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_content(
        self,
        query: str,
        max_count: int = 20,
        country: str = "VE",
    ) -> list[dict[str, Any]]:
        """Busca contenido por keyword en TikTok."""
        client = await self._get_client()

        query_params = {
            "query": query,
            "max_count": min(max_count, 100),
            "country": country,
            "sort_type": 0,
            "publish_time_range": "183d",
        }

        response = await client.post(
            "/research/search/content/",
            json=query_params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("videos", [])

    async def get_user_info(
        self,
        username: str,
    ) -> dict[str, Any] | None:
        """Obtiene información de perfil público de TikTok."""
        client = await self._get_client()

        response = await client.post(
            "/research/user/info/",
            json={"username": username},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return data.get("data", {})

    async def get_user_videos(
        self,
        username: str,
        max_count: int = 20,
    ) -> list[dict[str, Any]]:
        """Obtiene videos recientes de un usuario de TikTok."""
        client = await self._get_client()

        response = await client.post(
            "/research/user/videos/",
            json={
                "username": username,
                "max_count": min(max_count, 50),
                "fields": [
                    "id",
                    "create_time",
                    "desc",
                    "like_count",
                    "comment_count",
                    "share_count",
                    "view_count",
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("videos", [])


tiktok_client = TikTokClient()
