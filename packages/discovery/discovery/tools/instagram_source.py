"""Instagram source interface — abstraction layer for Apify, HikerAPI, etc."""

from typing import Any, Protocol

from discovery.schemas import BriefStructured


class InstagramSource(Protocol):
    """Contract for Instagram data sources. All implementations must provide these methods."""

    name: str

    async def search_hashtag(
        self,
        hashtag: str,
        country: str = "VE",
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Search posts by hashtag and return normalized profile dicts.

        Returns list of dicts with at minimum:
        {
            "username": str,
            "full_name": str,
            "biography": str,
            "bio": str,
            "follower_count": int,
            "followersCount": int,
            "following_count": int,
            "followsCount": int,
            "posts_count": int,
            "postsCount": int,
            "is_business": bool,
            "isBusinessAccount": bool,
            "is_verified": bool,
            "verified": bool,
            "avatar_url": str,
            "profilePicUrl": str,
            "pk": str | None,
            "country": str,
            "locationName": str,
        }
        """
        ...

    async def search_keyword(
        self,
        keyword: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search users by keyword and return normalized profile dicts."""
        ...

    async def enrich_profile(
        self,
        username: str,
    ) -> dict[str, Any] | None:
        """Fetch full profile data for a single username.

        Returns the same normalized dict as search_hashtag, or None if not found.
        """
        ...

    async def close(self) -> None:
        """Cleanup resources (http clients, redis, etc.)."""
        ...
