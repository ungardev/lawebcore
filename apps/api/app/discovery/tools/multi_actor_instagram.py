"""Multi-actor Instagram discovery client.

Tries multiple actors in sequence until one returns valid results.
This provides resilience against individual actor failures or Instagram restrictions.

VERIFIED ACTORS (tested with real API calls):
1. apify~instagram-scraper - Official Apify actor (160M+ runs)
2. reGe1ST3OBgYZSsZJ - Instagram Hashtag Scraper (4M+ runs) - VERIFIED WORKING
3. HOQ7J8VpusAOEbb6p - Instagram Hashtag Scraper Pro No Cookies (30k runs)
"""

import asyncio
import structlog
from typing import Any

import httpx

from app.core.config import settings

logger = structlog.get_logger(__name__)


INSTAGRAM_ACTORS = [
    {
        "id": "apify~instagram-scraper",
        "name": "apify_instagram_scraper",
        "priority": 1,
        "description": "Official Apify Instagram scraper - posts by hashtag",
    },
    {
        "id": "reGe1ST3OBgYZSsZJ",
        "name": "instagram_hashtag_scraper",
        "priority": 2,
        "description": "Instagram Hashtag Scraper - 4M+ runs, verified working",
    },
    {
        "id": "HOQ7J8VpusAOEbb6p",
        "name": "instagram_hashtag_scraper_pro_no_cookies",
        "priority": 3,
        "description": "Instagram Hashtag Scraper Pro No Cookies - 30k runs",
    },
]


class MultiActorInstagramClient:
    """Instagram discovery using multiple actors in fallback chain."""

    BASE_URL = "https://api.apify.com/v2"
    TIMEOUT = 120.0

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

    async def discover_by_hashtag(
        self,
        hashtag: str,
        country: str = "VE",
        results_limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Discover Instagram posts/accounts by hashtag using multi-actor fallback.

        Tries actors in priority order until one returns valid results.
        Returns list of raw posts/accounts from the first successful actor.
        """
        clean_hashtag = hashtag.lstrip("#")
        country_code = country.upper()

        logger.info(
            "multi_actor_instagram_start",
            hashtag=clean_hashtag,
            country=country_code,
            results_limit=results_limit,
        )

        actors_to_try = [
            ("apify~instagram-scraper", "hashtag_search", self._discover_apify_official),
            ("reGe1ST3OBgYZSsZJ", "hashtag_search", self._discover_hashtag_scraper),
            ("HOQ7J8VpusAOEbb6p", "hashtag_search", self._discover_pro_no_cookies),
        ]

        last_error = None
        for actor_id, method_name, method_fn in actors_to_try:
            try:
                logger.info(
                    "multi_actor_trying",
                    actor_id=actor_id,
                    hashtag=clean_hashtag,
                    method=method_name,
                )

                results = await method_fn(
                    clean_hashtag=clean_hashtag,
                    country=country_code,
                    results_limit=results_limit,
                )

                if results and len(results) > 0:
                    valid_results = [r for r in results if self._is_valid_post(r)]
                    if valid_results:
                        logger.info(
                            "multi_actor_success",
                            actor_id=actor_id,
                            results_count=len(valid_results),
                            first_handle=self._extract_handle_from_post(valid_results[0]),
                        )
                        return valid_results

                logger.warning(
                    "multi_actor_empty_results",
                    actor_id=actor_id,
                    results_count=len(results) if results else 0,
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    "multi_actor_failed",
                    actor_id=actor_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                continue

        logger.error(
            "multi_actor_all_failed",
            hashtag=clean_hashtag,
            country=country_code,
            last_error=str(last_error),
        )

        return []

    async def _discover_apify_official(
        self,
        clean_hashtag: str,
        country: str,
        results_limit: int,
    ) -> list[dict[str, Any]]:
        """Use apify~instagram-scraper for hashtag discovery."""
        client = await self._get_client()
        actor_id = "apify~instagram-scraper"

        run_input = {
            "hashtags": [clean_hashtag],
            "resultsType": "posts",
            "resultsLimit": results_limit,
            "searchType": "hashtag",
        }

        response = await client.post(
            f"/acts/{actor_id}/runs",
            json=run_input,
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]
        dataset_id = run_data["data"].get("defaultDatasetId")

        logger.info("apify_official_run_started", run_id=run_id, actor_id=actor_id)

        items = await self._poll_run(client, actor_id, run_id, dataset_id)

        valid_items = []
        for item in items:
            if self._is_valid_post(item):
                valid_items.append(item)
            else:
                logger.debug("apify_official_filtered_item", item_keys=list(item.keys()))

        return valid_items

    async def _discover_hashtag_scraper(
        self,
        clean_hashtag: str,
        country: str,
        results_limit: int,
    ) -> list[dict[str, Any]]:
        """Use reGe1ST3OBgYZSsZJ (Instagram Hashtag Scraper) for discovery.

        This actor is verified to work and returns real influencer data.
        Tested: #fitnessvenezuela returned 18 unique handles.
        """
        client = await self._get_client()
        actor_id = "reGe1ST3OBgYZSsZJ"

        run_input = {
            "hashtags": [clean_hashtag],
            "resultsLimit": results_limit,
        }

        response = await client.post(
            f"/acts/{actor_id}/runs",
            json=run_input,
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]
        dataset_id = run_data["data"].get("defaultDatasetId")

        logger.info("hashtag_scraper_run_started", run_id=run_id, actor_id=actor_id)

        items = await self._poll_run(client, actor_id, run_id, dataset_id)

        valid_items = []
        for item in items:
            if self._is_valid_post(item):
                valid_items.append(item)

        logger.info(
            "hashtag_scraper_results",
            actor_id=actor_id,
            total_items=len(items),
            valid_items=len(valid_items),
        )

        return valid_items

    async def _discover_pro_no_cookies(
        self,
        clean_hashtag: str,
        country: str,
        results_limit: int,
    ) -> list[dict[str, Any]]:
        """Use HOQ7J8VpusAOEbb6p (Instagram Hashtag Scraper Pro No Cookies).

        This actor explicitly states no Instagram cookies required.
        """
        client = await self._get_client()
        actor_id = "HOQ7J8VpusAOEbb6p"

        run_input = {
            "hashtags": [clean_hashtag],
            "resultsLimit": results_limit,
        }

        response = await client.post(
            f"/acts/{actor_id}/runs",
            json=run_input,
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]
        dataset_id = run_data["data"].get("defaultDatasetId")

        logger.info("pro_no_cookies_run_started", run_id=run_id, actor_id=actor_id)

        items = await self._poll_run(client, actor_id, run_id, dataset_id)

        valid_items = []
        for item in items:
            if self._is_valid_post(item):
                valid_items.append(item)

        return valid_items

    async def _poll_run(
        self,
        client: httpx.AsyncClient,
        actor_id: str,
        run_id: str,
        dataset_id: str | None,
        max_wait: int = 180,
    ) -> list[dict[str, Any]]:
        """Poll until run completes."""
        import json

        for i in range(max_wait // 5):
            status_resp = await client.get(f"/acts/{actor_id}/runs/{run_id}")
            status_data = status_resp.json()
            status = status_data.get("data", {}).get("status")

            logger.debug("actor_poll", run_id=run_id, actor_id=actor_id, status=status, attempt=i + 1)

            if status == "RUNNING":
                await asyncio.sleep(5)
                continue
            elif status == "SUCCEEDED":
                ds_id = dataset_id or status_data.get("data", {}).get("defaultDatasetId")
                if not ds_id:
                    logger.warning("actor_no_dataset", run_id=run_id)
                    return []

                items_resp = await client.get(f"/datasets/{ds_id}/items")
                items_text = items_resp.text.strip()

                if not items_text or items_text == "null":
                    return []

                try:
                    items = json.loads(items_text)
                    if isinstance(items, dict) and "error" in items:
                        logger.warning("actor_dataset_error", error=items.get("error"))
                        return []
                    if isinstance(items, list):
                        valid = []
                        for item in items:
                            if isinstance(item, dict) and "error" not in item:
                                valid.append(item)
                        return valid
                    return []
                except json.JSONDecodeError:
                    return []
            elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                status_message = status_data.get("data", {}).get("statusMessage", status)
                logger.warning("actor_run_failed", run_id=run_id, status=status, message=status_message)
                return []
            else:
                await asyncio.sleep(5)
                continue

        logger.warning("actor_poll_timeout", run_id=run_id, max_wait=max_wait)
        return []

    def _is_valid_post(self, item: dict[str, Any]) -> bool:
        """Check if an item is a valid post (not an error)."""
        if not isinstance(item, dict):
            return False
        if "error" in item:
            return False
        if "ownerUsername" in item or "username" in item:
            return True
        if "shortCode" in item or "id" in item:
            return True
        return False

    def _extract_handle_from_post(self, post: dict[str, Any]) -> str:
        """Extract username/handle from a post dict."""
        return post.get("ownerUsername") or post.get("username") or post.get("handle", "unknown")


multi_actor_instagram_client = MultiActorInstagramClient()
