"""Apify client — scraping de Instagram, TikTok, YouTube vía Apify actors."""

from typing import Any

import httpx

from app.core.config import settings


class ApifyClient:
    """Cliente para Apify API v2."""

    BASE_URL = "https://api.apify.com/v2"
    TIMEOUT = 60.0

    def __init__(self, token: str | None = None):
        self.token = token or settings.APIFY_API_KEY
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.TIMEOUT,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_instagram_by_hashtag(
        self,
        hashtag: str,
        country: str = "VE",
        min_followers: int = 1000,
        max_followers: int = 10_000_000,
    ) -> list[dict[str, Any]]:
        """Busca posts de Instagram por hashtag vía apify/instagram-hashtag-scraper."""
        client = await self._get_client()

        run_input = {
            "hashtags": [hashtag],
            "resultType": "posts",
            "maxItems": 100,
            "filter": {
                "followersCountMin": min_followers,
                "followersCountMax": max_followers,
            },
        }

        response = await client.post(
            "/acts/apify~instagram-hashtag-scraper/runs",
            json={"token": self.token, "uiRunSpec": {"runInput": run_input}},
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]

        return await self._poll_run(client, run_id)

    async def search_instagram_profile(
        self,
        username: str,
    ) -> dict[str, Any] | None:
        """Obtiene datos de perfil de Instagram vía apify/instagram-profile-scraper."""
        client = await self._get_client()

        run_input = {
            "usernames": [username],
            "resultsType": "details",
        }

        response = await client.post(
            "/acts/apify~instagram-profile-scraper/runs",
            json={"token": self.token, "uiRunSpec": {"runInput": run_input}},
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]

        results = await self._poll_run(client, run_id)
        return results[0] if results else None

    async def search_tiktok_by_hashtag(
        self,
        hashtag: str,
        country: str = "VE",
    ) -> list[dict[str, Any]]:
        """Busca posts de TikTok por hashtag vía clockworks/tiktok-scraper."""
        client = await self._get_client()

        run_input = {
            "hashtags": [hashtag],
            "country": country,
            "quantity": 100,
        }

        response = await client.post(
            "/acts/clockworks~tiktok-scraper/runs",
            json={"token": self.token, "uiRunSpec": {"runInput": run_input}},
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]

        return await self._poll_run(client, run_id)

    async def _poll_run(
        self, client: httpx.AsyncClient, run_id: str, max_wait: int = 300
    ) -> list[dict[str, Any]]:
        """Poll hasta que el run complete (max 5 minutos)."""
        import asyncio

        for _ in range(max_wait // 5):
            status_resp = await client.get(f"/runs/{run_id}")
            status_resp.raise_for_status()
            status_data = status_resp.json()
            status = status_data["data"]["status"]

            if status == "RUNNING":
                await asyncio.sleep(5)
                continue
            elif status == "SUCCEEDED":
                dataset_resp = await client.get(f"/runs/{run_id}/dataset/items")
                dataset_resp.raise_for_status()
                return dataset_resp.json()
            else:
                raise RuntimeError(f"Apify run failed: {status}")
        raise TimeoutError(f"Apify run {run_id} timed out after {max_wait}s")


apify_client = ApifyClient()
