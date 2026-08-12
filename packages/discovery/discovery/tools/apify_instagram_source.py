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
        """Use apify~instagram-profile-scraper to get full profile with country/locationName.

        This is the key method that HikerAPI cannot replace — Apify's profile scraper
        returns country and locationName fields that HikerAPI does not expose.
        """
        profile = await self._client.search_instagram_profile(
            username=username.lstrip("@"),
        )
        if not profile or not isinstance(profile, dict):
            logger.warning("apify_enrich_profile_failed", username=username)
            return None

        enriched = {
            "username": profile.get("username") or username.lstrip("@"),
            "full_name": profile.get("fullName") or "",
            "fullName": profile.get("fullName") or "",
            "bio": profile.get("biography") or "",
            "biography": profile.get("biography") or "",
            "avatar_url": profile.get("profilePicUrlHD") or profile.get("profilePicUrl") or "",
            "profilePicUrl": profile.get("profilePicUrl") or "",
            "profilePicUrlHD": profile.get("profilePicUrlHD") or "",
            "follower_count": profile.get("followersCount", 0) or 0,
            "followersCount": profile.get("followersCount", 0) or 0,
            "following_count": profile.get("followsCount", 0) or 0,
            "followsCount": profile.get("followsCount", 0) or 0,
            "posts_count": profile.get("postsCount", 0) or 0,
            "postsCount": profile.get("postsCount", 0) or 0,
            "is_business": bool(profile.get("isBusinessAccount", False)),
            "isBusinessAccount": bool(profile.get("isBusinessAccount", False)),
            "is_verified": bool(profile.get("verified", False)),
            "verified": bool(profile.get("verified", False)),
            "pk": profile.get("id") or profile.get("pk"),
            "country": profile.get("country", "") or "",
            "locationName": profile.get("locationName", "") or "",
            "city": profile.get("city") or "",
            "external_url": profile.get("externalUrl") or profile.get("external_url") or "",
            "latestPosts": profile.get("latestPosts", []) or [],
        }

        logger.info(
            "apify_enrich_success",
            username=enriched["username"],
            followers=enriched["followersCount"],
            country=enriched["country"],
            location=enriched["locationName"],
        )
        return enriched

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
            "country": user.get("country", "") or item.get("country", "") or "",
            "locationName": item.get("locationName", "") or user.get("locationName", ""),
        }
