"""Apify Instagram source — wraps ApifyClient as an InstagramSource."""

import structlog
from typing import Any

from discovery.tools.apify_client import ApifyClient
from discovery.tools.instagram_source import InstagramSource

logger = structlog.get_logger(__name__)


class ApifyInstagramSource:
    """Wrap ApifyClient to conform to the InstagramSource Protocol."""

    def __init__(self, apify_client: ApifyClient | None = None):
        self._client = apify_client or ApifyClient()

    @property
    def name(self) -> str:
        return "apify"

    async def search_hashtag(
        self,
        hashtag: str,
        country: str = "VE",
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Use Apify instagram-hashtag-scraper to get posts for a hashtag."""
        items = await self._client.scrape_hashtags_all_sync(
            hashtags=[hashtag],
            results_limit=limit,
        )
        results = []
        for item in items:
            user = self._extract_user(item)
            if not user or not user.get("username"):
                continue
            normalized = self._normalize(item, user)
            results.append(normalized)
        logger.info("apify_source_search_hashtag", hashtag=hashtag, results=len(results))
        return results

    async def search_keyword(
        self,
        keyword: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Use Apify instagram-search-scraper to search users by keyword."""
        items = await self._client.search_instagram_users_by_keyword(
            keyword=keyword,
            limit=limit,
        )
        results = []
        for item in items:
            user = self._extract_user(item)
            if not user or not user.get("username"):
                continue
            normalized = self._normalize(item, user)
            results.append(normalized)
        logger.info("apify_source_search_keyword", keyword=keyword, results=len(results))
        return results

    async def enrich_profile(
        self,
        username: str,
    ) -> dict[str, Any] | None:
        """Apify does not support direct username lookup — return None."""
        logger.debug("apify_source_enrich_not_supported", username=username)
        return None

    async def close(self) -> None:
        await self._client.close()

    def _extract_user(self, item: dict) -> dict:
        if "user" in item and item["user"]:
            return item["user"]
        return item

    def _normalize(self, item: dict, user: dict) -> dict[str, Any]:
        follower_count = user.get("followersCount") or user.get("follower_count") or 0
        following_count = user.get("followsCount") or user.get("following_count") or 0
        posts_count = user.get("postsCount") or user.get("posts_count") or 0

        return {
            "username": user.get("username", "") or item.get("ownerUsername", ""),
            "full_name": user.get("fullName", "") or user.get("full_name", "") or item.get("ownerFullName", ""),
            "biography": user.get("biography", "") or user.get("bio", "") or item.get("caption", ""),
            "bio": user.get("biography", "") or user.get("bio", "") or item.get("caption", ""),
            "avatar_url": (user.get("profilePicUrlHD") or user.get("profilePicUrl") or item.get("displayUrl") or ""),
            "profilePicUrl": user.get("profilePicUrlHD") or user.get("profilePicUrl") or item.get("displayUrl", ""),
            "follower_count": follower_count,
            "followersCount": follower_count,
            "following_count": following_count,
            "followsCount": following_count,
            "posts_count": posts_count,
            "postsCount": posts_count,
            "is_business": bool(user.get("isBusinessAccount") or user.get("is_business") or item.get("isBusinessAccount", False)),
            "isBusinessAccount": bool(user.get("isBusinessAccount") or user.get("is_business") or item.get("isBusinessAccount", False)),
            "is_verified": bool(user.get("is_verified") or user.get("verified") or item.get("verified", False)),
            "verified": bool(user.get("is_verified") or user.get("verified") or item.get("verified", False)),
            "pk": None,
            "country": "",
            "locationName": item.get("locationName", "") or user.get("locationName", ""),
        }
