"""Apify client — scraping de Instagram, TikTok, YouTube vía Apify actors."""

import asyncio
import structlog
from typing import Any

import httpx

from shared_core.config import settings

logger = structlog.get_logger(__name__)


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

    def _build_client_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def search_instagram_by_hashtag(
        self,
        hashtag: str,
        country: str = "VE",
        min_followers: int = 1000,
        max_followers: int = 10_000_000,
    ) -> list[dict[str, Any]]:
        """Busca posts de Instagram por hashtag vía apify/instagram-scraper."""
        client = await self._get_client()

        clean_hashtag = hashtag.lstrip("#")

        logger.info(
            "apify_instagram_start",
            hashtag=hashtag,
            clean_hashtag=clean_hashtag,
            country=country,
            min_followers=min_followers,
            max_followers=max_followers,
            token_prefix=self.token[:8] if self.token else "EMPTY",
        )

        actor_id = "apify~instagram-scraper"

        run_input = {
            "hashtags": [clean_hashtag],
            "resultsType": "posts",
            "resultsLimit": 30,
            "searchType": "hashtag",
        }

        response = await client.post(
            f"/acts/{actor_id}/runs",
            json=run_input,
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        logger.info(
            "apify_run_started",
            run_id=run_id,
            actor_id=actor_id,
            default_dataset_id=default_dataset_id,
            hashtag=clean_hashtag,
        )

        return await self._poll_run(client, actor_id, run_id, default_dataset_id)

    async def search_instagram_profile(
        self,
        username: str,
    ) -> dict[str, Any] | None:
        """Obtiene datos de perfil de Instagram vía apify/instagram-profile-scraper."""
        client = await self._get_client()

        actor_id = "apify~instagram-profile-scraper"

        run_input = {
            "usernames": [username.lstrip("@")],
            "resultsType": "details",
        }

        response = await client.post(
            f"/acts/{actor_id}/runs",
            json=run_input,
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        results = await self._poll_run(client, actor_id, run_id, default_dataset_id)
        return results[0] if results else None

    async def search_instagram_profiles_batch(
        self,
        usernames: list[str],
    ) -> list[dict[str, Any]]:
        """Busca múltiples perfiles de Instagram en paralelo usando asyncio.gather."""
        if not usernames:
            return []

        batch_size = 10
        batches = [usernames[i:i + batch_size] for i in range(0, len(usernames), batch_size)]

        logger.info(
            "apify_profile_batch_start",
            total_usernames=len(usernames),
            num_batches=len(batches),
            batch_size=batch_size,
        )

        batch_tasks = [
            self._search_instagram_profiles_single_request(batch) for batch in batches
        ]
        batch_results_list = await asyncio.gather(*batch_tasks, return_exceptions=True)

        results: list[dict[str, Any]] = []
        for i, batch_result in enumerate(batch_results_list):
            if isinstance(batch_result, Exception):
                logger.error(
                    "apify_profile_batch_failed",
                    batch_index=i,
                    batch_size=len(batches[i]),
                    error=str(batch_result),
                )
                continue
            results.extend(batch_result)
            logger.info(
                "apify_profile_batch_progress",
                batch_index=i,
                batch_size=len(batches[i]),
                results_in_batch=len(batch_result),
                total_results=len(results),
            )

        logger.info(
            "apify_profile_batch_complete",
            total_usernames=len(usernames),
            total_results=len(results),
        )
        return results

    async def _search_instagram_profiles_single_request(
        self,
        usernames: list[str],
    ) -> list[dict[str, Any]]:
        """Busca un batch de hasta 5 perfiles en UNA llamada al actor."""
        client = await self._get_client()
        actor_id = "apify~instagram-profile-scraper"

        run_input = {
            "usernames": [u.lstrip("@") for u in usernames],
            "resultsType": "details",
        }

        response = await client.post(
            f"/acts/{actor_id}/runs",
            json=run_input,
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        items = await self._poll_run(client, actor_id, run_id, default_dataset_id)

        valid_results = []
        for item in items:
            if isinstance(item, dict) and "error" not in item:
                valid_results.append(item)
            elif isinstance(item, dict) and item.get("error"):
                username = item.get("input", {}).get("username", "unknown")
                logger.warning("apify_profile_error", username=username, error=item.get("error"))

        return valid_results

    async def search_tiktok_by_hashtag(
        self,
        hashtag: str,
        country: str = "VE",
    ) -> list[dict[str, Any]]:
        """Busca posts de TikTok por hashtag vía clockworks/tiktok-scraper."""
        client = await self._get_client()

        actor_id = "clockworks~tiktok-scraper"

        run_input = {
            "hashtags": [hashtag.lstrip("#")],
            "country": country,
            "quantity": 100,
        }

        response = await client.post(
            f"/acts/{actor_id}/runs",
            json=run_input,
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        return await self._poll_run(client, actor_id, run_id, default_dataset_id)

    async def _poll_run(
        self,
        client: httpx.AsyncClient,
        actor_id: str,
        run_id: str,
        default_dataset_id: str | None,
        max_wait: int = 300,
    ) -> list[dict[str, Any]]:
        """Poll hasta que el run complete (max 5 minutos)."""
        import asyncio

        for i in range(max_wait // 5):
            status_resp = await client.get(f"/acts/{actor_id}/runs/{run_id}")
            status_data = status_resp.json()
            status = status_data.get("data", {}).get("status")

            logger.info("apify_poll", run_id=run_id, actor_id=actor_id, status=status, attempt=i + 1)

            if status == "RUNNING":
                await asyncio.sleep(5)
                continue
            elif status == "SUCCEEDED":
                ds_id = default_dataset_id or status_data.get("data", {}).get("defaultDatasetId")
                if not ds_id:
                    logger.error("apify_no_dataset_id", run_id=run_id, status_data=status_data)
                    raise RuntimeError(f"No dataset ID for run {run_id}")

                items = await self._fetch_dataset_items(client, ds_id)
                logger.info(
                    "apify_run_succeeded",
                    run_id=run_id,
                    actor_id=actor_id,
                    dataset_id=ds_id,
                    items_count=len(items),
                    first_item_keys=list(items[0].keys()) if items else [],
                )
                return items
            elif status == "FAILED":
                status_message = status_data.get("data", {}).get("statusMessage", "unknown")
                logger.error("apify_run_failed", run_id=run_id, status_message=status_message, full_status=status_data)
                raise RuntimeError(f"Apify run failed: {status_message}")
            elif status == "ABORTED":
                logger.error("apify_run_aborted", run_id=run_id)
                raise RuntimeError(f"Apify run aborted: {run_id}")
            else:
                logger.warning("apify_run_unexpected_status", run_id=run_id, status=status)
                await asyncio.sleep(5)
                continue

        logger.error("apify_poll_timeout", run_id=run_id, max_wait=max_wait)
        raise TimeoutError(f"Apify run {run_id} timed out after {max_wait}s")

    async def _fetch_dataset_items(
        self, client: httpx.AsyncClient, dataset_id: str
    ) -> list[dict[str, Any]]:
        """Fetch items from a dataset using the correct endpoint."""
        import json

        items_resp = await client.get(f"/datasets/{dataset_id}/items")
        items_text = items_resp.text.strip()

        if not items_text or items_text == "null":
            logger.warning("apify_dataset_empty", dataset_id=dataset_id)
            return []

        try:
            items = json.loads(items_text)
            if isinstance(items, dict) and "error" in items:
                error_type = items.get("error", {}).get("type", "unknown")
                error_desc = items.get("error", {}).get("errorDescription", "")
                logger.error(
                    "apify_dataset_error",
                    dataset_id=dataset_id,
                    error_type=error_type,
                    error_description=error_desc,
                )
                return []
            if not isinstance(items, list):
                logger.warning("apify_dataset_unexpected_format", dataset_id=dataset_id, type=type(items))
                return []
            valid_items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                if "error" in item:
                    error_desc = item.get("errorDescription", item.get("error", "unknown"))
                    input_url = item.get("inputUrl", "")
                    username = "unknown"
                    if "instagram.com/" in input_url:
                        username = input_url.split("instagram.com/")[-1].rstrip("/")
                    logger.warning(
                        "apify_dataset_item_skipped",
                        dataset_id=dataset_id,
                        username=username,
                        input_url=input_url,
                        error=error_desc,
                    )
                    continue
                valid_items.append(item)
            return valid_items
        except json.JSONDecodeError as e:
            logger.error("apify_dataset_json_parse_failed", dataset_id=dataset_id, error=str(e), text_preview=items_text[:200])
            return []


apify_client = ApifyClient()
