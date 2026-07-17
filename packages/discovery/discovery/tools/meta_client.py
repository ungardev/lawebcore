"""Meta Business API client — Instagram + Facebook vía Graph API."""

from typing import Any

import structlog

import httpx

from shared_core.config import settings

logger = structlog.get_logger(__name__)


class MetaClient:
    """Cliente para Meta Business Graph API."""

    BASE_URL = "https://graph.facebook.com/v21.0"
    TIMEOUT = 30.0

    FACEBOOK_NICHE_CATEGORIES = {
        "fitness": ["Sports & Fitness", "Gym", "Health & Wellness", "Personal Training"],
        "moda": ["Clothing (Brand)", "Fashion", "Style", "Fashion Designer"],
        "belleza": ["Beauty", "Cosmetics", "Hair & Beauty", "Makeup Artist"],
        "tecnologia": ["Technology", "Computers", "Software", "Electronics"],
        "comida": ["Food & Dining", "Restaurant", "Chef", "Food Blogger"],
        "viajes": ["Travel", "Hotel Resort", "Tourism", "Travel Agency"],
        "gaming": ["Games", "Gaming", "Video Game", "Twitch Streamer"],
        "musica": ["Music", "Musician", "Band", "Singer"],
        "arte": ["Art", "Artist", "Art Gallery", "Painter"],
        "emprendimiento": ["Entrepreneur", "Business", "Coach", "Motivational Speaker"],
    }

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
        client = await self._get_client()
        params = {
            "input_token": self.access_token,
            "access_token": f"{self.app_id}|{self.app_secret}",
        }
        response = await client.get("/debug_token", params=params)
        response.raise_for_status()
        return response.json()

    async def discover_pages(
        self,
        niches: list[str],
        country: str = "VE",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        client = await self._get_client()
        results: list[dict[str, Any]] = []
        country_code = country.upper()

        search_queries = self._build_search_queries(niches, country_code)

        for query in search_queries[:limit]:
            try:
                params = {
                    "q": query,
                    "type": "page",
                    "fields": "id,name,fan_count,followers_count,about,category,instagram_business_account{username,followers_count}",
                    "access_token": self.access_token,
                }
                response = await client.get("/search", params=params)
                response.raise_for_status()
                data = response.json()

                for page in data.get("data", []):
                    page["search_query"] = query
                    page["source"] = "facebook_search"
                    results.append(page)

                logger.info(
                    "meta_page_search",
                    query=query,
                    results_count=len(data.get("data", [])),
                )

            except httpx.HTTPStatusError as e:
                logger.warning("meta_page_search_failed", query=query, error=str(e))
                continue
            except Exception as e:
                logger.warning("meta_page_search_error", query=query, error=str(e))
                continue

        deduplicated = self._deduplicate_pages(results)
        logger.info("meta_discovery_complete", total_pages=len(deduplicated))
        return deduplicated

    def _build_search_queries(self, niches: list[str], country: str) -> list[str]:
        queries = []
        country_name = self._country_code_to_name(country)

        for niche in niches:
            niche_lower = niche.lower()
            queries.append(f"{niche} {country_name}")

            if niche_lower in self.FACEBOOK_NICHE_CATEGORIES:
                for category in self.FACEBOOK_NICHE_CATEGORIES[niche_lower]:
                    queries.append(f"{category} {country_name}")
                    queries.append(f"{niche} {category}")

            queries.append(f"{niche} Venezuela")

        return list(dict.fromkeys(queries))[:30]

    def _country_code_to_name(self, code: str) -> str:
        mapping = {
            "VE": "Venezuela",
            "CO": "Colombia",
            "MX": "Mexico",
            "AR": "Argentina",
            "CL": "Chile",
            "PE": "Peru",
            "EC": "Ecuador",
            "BO": "Bolivia",
            "PA": "Panama",
            "DO": "Dominican Republic",
            "CR": "Costa Rica",
            "UY": "Uruguay",
            "PY": "Paraguay",
            "GT": "Guatemala",
            "HN": "Honduras",
            "SV": "El Salvador",
            "NI": "Nicaragua",
        }
        return mapping.get(code.upper(), code)

    def _deduplicate_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = set()
        unique = []
        for page in pages:
            page_id = page.get("id")
            if page_id and page_id not in seen:
                seen.add(page_id)
                unique.append(page)
        return unique

    async def get_instagram_account_from_page(self, page_id: str) -> dict[str, Any] | None:
        client = await self._get_client()
        try:
            params = {
                "fields": "instagram_business_account{id,username,name,followers_count,follows_count,media_count,profile_picture_url,biography}",
                "access_token": self.access_token,
            }
            response = await client.get(f"/{page_id}", params=params)
            response.raise_for_status()
            data = response.json()

            ig_account = data.get("instagram_business_account")
            if ig_account:
                return {
                    "platform": "instagram",
                    "platform_user_id": ig_account.get("id"),
                    "handle": ig_account.get("username"),
                    "full_name": ig_account.get("name"),
                    "followers": ig_account.get("followers_count"),
                    "following": ig_account.get("follows_count"),
                    "posts_count": ig_account.get("media_count"),
                    "avatar_url": ig_account.get("profile_picture_url"),
                    "bio": ig_account.get("biography"),
                    "source_page_id": page_id,
                }
            return None
        except Exception as e:
            logger.warning("meta_ig_from_page_failed", page_id=page_id, error=str(e))
            return None

    async def get_instagram_accounts(self, page_id: str) -> list[dict[str, Any]]:
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
