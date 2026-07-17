"""Metricool API client — analytics de redes sociales."""

from datetime import date
from typing import Any

import httpx

from shared_core.config import settings


class MetricoolClient:
    """Cliente para Metricool API REST."""

    BASE_URL = "https://api.metricool.com/v2"
    TIMEOUT = 30.0

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
    ):
        self.client_id = client_id or settings.METRICOOL_CLIENT_ID
        self.client_secret = client_secret or settings.METRICOOL_CLIENT_SECRET
        self.access_token = access_token or settings.METRICOOL_ACCESS_TOKEN
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=self.TIMEOUT,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_analytics(
        self,
        channel: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Obtiene analytics de un canal (instagram, tiktok, youtube, twitter)."""
        client = await self._get_client()
        params = {
            "channel": channel,
            "dateFrom": start_date.isoformat(),
            "dateTo": end_date.isoformat(),
        }
        response = await client.get("/analytics/evolution", params=params)
        response.raise_for_status()
        return response.json()

    async def get_best_posts(
        self,
        channel: str,
        start_date: date,
        end_date: date,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Obtiene los mejores posts de un canal."""
        client = await self._get_client()
        params = {
            "channel": channel,
            "dateFrom": start_date.isoformat(),
            "dateTo": end_date.isoformat(),
            "maxResults": limit,
        }
        response = await client.get("/analytics/posts/best", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", []) or data.get("posts", [])

    async def get_audience(
        self,
        channel: str,
    ) -> dict[str, Any]:
        """Obtiene demographics y audience breakdown de un canal."""
        client = await self._get_client()
        response = await client.get(f"/analytics/audience?channel={channel}")
        response.raise_for_status()
        return response.json()

    async def get_influencers(
        self,
        channel: str = "instagram",
        min_followers: int = 1000,
        max_followers: int = 10_000_000,
        niche: str | None = None,
    ) -> list[dict[str, Any]]:
        """Busca influencers analizados por Metricool."""
        client = await self._get_client()
        params: dict[str, Any] = {
            "channel": channel,
            "minFollowers": min_followers,
            "maxFollowers": max_followers,
        }
        if niche:
            params["keyword"] = niche
        response = await client.get("/analytics/influencers", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", []) or []


metricool_client = MetricoolClient()
