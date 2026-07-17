"""YouTube Data API v3 client."""

from typing import Any

import httpx

from shared_core.config import settings


class YouTubeClient:
    """Cliente para YouTube Data API v3."""

    BASE_URL = "https://www.googleapis.com/youtube/v3"
    TIMEOUT = 30.0

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.YOUTUBE_DATA_API_KEY
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                params={"key": self.api_key},
                timeout=self.TIMEOUT,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_channels(
        self,
        query: str,
        region: str = "VE",
        relevance_language: str = "es",
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Busca canales de YouTube por keyword."""
        client = await self._get_client()

        search_params = {
            "part": "snippet",
            "q": query,
            "type": "channel",
            "regionCode": region,
            "relevanceLanguage": relevance_language,
            "maxResults": min(max_results, 50),
        }

        response = await client.get("/search", params=search_params)
        response.raise_for_status()
        data = response.json()

        channels = []
        for item in data.get("items", []):
            channel_id = item["snippet"]["channelId"]
            details = await self._get_channel_details(client, channel_id)
            channels.append({**item, "channel_details": details})

        return channels

    async def _get_channel_details(
        self, client: httpx.AsyncClient, channel_id: str
    ) -> dict[str, Any]:
        """Obtiene estadísticas detalladas de un canal."""
        params = {
            "part": "snippet,statistics,brandingSettings,contentDetails",
            "id": channel_id,
        }
        response = await client.get("/channels", params=params)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            return items[0] if items else {}
        return {}

    async def get_channel_videos(
        self,
        channel_id: str,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Obtiene videos recientes de un canal."""
        client = await self._get_client()

        playlist_params = {
            "part": "contentDetails",
            "channelId": channel_id,
            "maxResults": max_results,
            "order": "date",
        }
        playlist_resp = await client.get("/playlistItems", params=playlist_params)
        playlist_resp.raise_for_status()
        playlist_data = playlist_resp.json()

        video_ids = [
            item["contentDetails"]["videoId"]
            for item in playlist_data.get("items", [])
            if "videoId" in item["contentDetails"]
        ]

        if not video_ids:
            return []

        videos_params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids[:50]),
        }
        videos_resp = await client.get("/videos", params=videos_params)
        videos_resp.raise_for_status()
        return videos_resp.json().get("items", [])

    async def get_video_metrics(self, video_id: str) -> dict[str, Any]:
        """Obtiene métricas de un video específico."""
        client = await self._get_client()
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": video_id,
        }
        response = await client.get("/videos", params=params)
        response.raise_for_status()
        items = response.json().get("items", [])
        return items[0] if items else {}


youtube_client = YouTubeClient()
