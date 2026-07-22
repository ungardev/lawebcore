"""Apify client — scraping de Instagram, TikTok, YouTube vía Apify actors."""

import asyncio
import hashlib
import json
import structlog
from typing import Any

import httpx
import redis.asyncio as redis
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from shared_core.config import settings

logger = structlog.get_logger(__name__)

INSTAGRAM_PROFILE_SCRAPER = "apify~instagram-profile-scraper"
INSTAGRAM_HASHTAG_SCRAPER = "apify/instagram-hashtag-scraper"
INSTAGRAM_SEARCH_SCRAPER = "apify/instagram-search-scraper"
ENGAGEMENT_ANALYTICS_SCRAPER = "easy_scraper/instagram-profile-engagement-analytics"
TIKTOK_SCRAPER = "clockworks~tiktok-scraper"

CACHE_TTL_PROFILES = 86400
CACHE_TTL_SEARCH = 604800


class ApifyClient:
    """Cliente para Apify API v2."""

    BASE_URL = "https://api.apify.com/v2"
    TIMEOUT = 60.0

    def __init__(self, token: str | None = None):
        self.token = token or settings.APIFY_API_KEY
        self._client: httpx.AsyncClient | None = None
        self._redis: redis.Redis | None = None
        self._costs: dict[str, float] = {}
        self.discovery_run_id: str | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.TIMEOUT,
            )
        return self._client

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.ARQ_REDIS_URL, decode_responses=False)
        return self._redis

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _build_cache_key(self, actor_id: str, run_input: dict) -> str:
        stable = json.dumps(run_input, sort_keys=True, default=str)
        h = hashlib.sha1(f"{actor_id}:{stable}".encode()).hexdigest()
        return f"apify:cache:{actor_id}:{h}"

    async def _get_cached(self, cache_key: str) -> list[dict[str, Any]] | None:
        try:
            r = await self._get_redis()
            data = await r.get(cache_key)
            if data:
                logger.info("apify_cache_hit", key=cache_key)
                return json.loads(data)
            logger.info("apify_cache_miss", key=cache_key)
            return None
        except Exception as e:
            logger.warning("apify_cache_error", key=cache_key, error=str(e))
            return None

    async def _set_cached(self, cache_key: str, items: list[dict[str, Any]], ttl: int) -> None:
        try:
            r = await self._get_redis()
            await r.setex(cache_key, ttl, json.dumps(items, default=str))
            logger.info("apify_cache_set", key=cache_key, ttl=ttl, items=len(items))
        except Exception as e:
            logger.warning("apify_cache_set_error", key=cache_key, error=str(e))

    def record_cost(self, discovery_run_id: str, cost_usd: float) -> None:
        self._costs[discovery_run_id] = self._costs.get(discovery_run_id, 0.0) + cost_usd

    def get_total_cost(self, discovery_run_id: str) -> float:
        return self._costs.get(discovery_run_id, 0.0)

    def get_and_clear_cost(self, discovery_run_id: str) -> float:
        cost = self._costs.pop(discovery_run_id, 0.0)
        return cost

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in (429, 500, 502, 503, 504)
        return isinstance(exc, (TimeoutError, asyncio.TimeoutError))

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        reraise=True,
    )
    async def _post_run(self, client: httpx.AsyncClient, actor_id: str, run_input: dict) -> dict:
        response = await client.post(f"/acts/{actor_id}/runs", json=run_input)
        response.raise_for_status()
        return response.json()

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

        cache_key = self._build_cache_key(actor_id, run_input)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        run_data = await self._post_run(client, actor_id, run_input)
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        logger.info(
            "apify_run_started",
            run_id=run_id,
            actor_id=actor_id,
            default_dataset_id=default_dataset_id,
            hashtag=clean_hashtag,
        )

        items = await self._poll_run(client, actor_id, run_id, default_dataset_id, cache_key=cache_key, cache_ttl=CACHE_TTL_PROFILES)
        return items

    async def search_instagram_profile(
        self,
        username: str,
    ) -> dict[str, Any] | None:
        """Obtiene datos de perfil de Instagram vía apify/instagram-profile-scraper."""
        client = await self._get_client()

        run_input = {
            "usernames": [username.lstrip("@")],
            "resultsType": "details",
            "includeAboutSection": True,
        }

        cache_key = self._build_cache_key(INSTAGRAM_PROFILE_SCRAPER, run_input)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached[0] if cached else None

        run_data = await self._post_run(client, INSTAGRAM_PROFILE_SCRAPER, run_input)
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        results = await self._poll_run(client, INSTAGRAM_PROFILE_SCRAPER, run_id, default_dataset_id, cache_key=cache_key, cache_ttl=CACHE_TTL_PROFILES)
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

        run_input = {
            "usernames": [u.lstrip("@") for u in usernames],
            "resultsType": "details",
            "includeAboutSection": True,
        }

        cache_key = self._build_cache_key(INSTAGRAM_PROFILE_SCRAPER, run_input)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            logger.info("apify_batch_cache_hit", usernames=usernames, cached_count=len(cached))
            for item in cached:
                if isinstance(item, dict) and "error" not in item:
                    await self._enrich_profile_with_er(item)
            return [item for item in cached if isinstance(item, dict) and "error" not in item]

        run_data = await self._post_run(client, INSTAGRAM_PROFILE_SCRAPER, run_input)
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        items = await self._poll_run(client, INSTAGRAM_PROFILE_SCRAPER, run_id, default_dataset_id, cache_key=cache_key, cache_ttl=CACHE_TTL_PROFILES)

        valid_results = []
        for item in items:
            if isinstance(item, dict) and "error" not in item:
                await self._enrich_profile_with_er(item)
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

        run_input = {
            "hashtags": [hashtag.lstrip("#")],
            "country": country,
            "quantity": 100,
        }

        run_data = await self._post_run(client, TIKTOK_SCRAPER, run_input)
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        return await self._poll_run(client, TIKTOK_SCRAPER, run_id, default_dataset_id)

    async def search_instagram_users_by_keyword(
        self,
        keyword: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Busca perfiles de Instagram por keyword/usuario vía instagram-search-scraper."""
        client = await self._get_client()

        logger.info(
            "apify_keyword_search_start",
            keyword=keyword,
            limit=limit,
            token_prefix=self.token[:8] if self.token else "EMPTY",
        )

        run_input = {
            "searchType": "users",
            "searchQueries": [keyword],
            "resultsLimit": limit,
            "enhanceUserSearchWithFacebookPage": True,
        }

        cache_key = self._build_cache_key(INSTAGRAM_SEARCH_SCRAPER, run_input)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        run_data = await self._post_run(client, INSTAGRAM_SEARCH_SCRAPER, run_input)
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        results = await self._poll_run(client, INSTAGRAM_SEARCH_SCRAPER, run_id, default_dataset_id, cache_key=cache_key, cache_ttl=CACHE_TTL_SEARCH)
        logger.info(
            "apify_keyword_search_done",
            keyword=keyword,
            results_count=len(results),
        )
        return results

    async def search_trending_hashtags(
        self,
        keyword: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Busca hashtags trending por keyword vía instagram-search-scraper."""
        client = await self._get_client()

        logger.info(
            "apify_hashtag_search_start",
            keyword=keyword,
            limit=limit,
        )

        run_input = {
            "searchType": "hashtag",
            "searchQueries": [keyword],
            "resultsLimit": limit,
        }

        run_data = await self._post_run(client, INSTAGRAM_SEARCH_SCRAPER, run_input)
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        results = await self._poll_run(client, INSTAGRAM_SEARCH_SCRAPER, run_id, default_dataset_id, cache_key=None)
        logger.info(
            "apify_hashtag_search_done",
            keyword=keyword,
            results_count=len(results),
        )
        return results

    async def search_users_by_multiple_keywords(
        self,
        keywords: list[str],
        limit_per_keyword: int = 30,
    ) -> list[dict[str, Any]]:
        """Busca perfiles por múltiples keywords en paralelo usando asyncio.gather."""
        if not keywords:
            return []

        logger.info(
            "apify_multi_keyword_start",
            keywords_count=len(keywords),
            limit_per_keyword=limit_per_keyword,
        )

        tasks = [
            self.search_instagram_users_by_keyword(kw, limit=limit_per_keyword)
            for kw in keywords
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: list[dict[str, Any]] = []
        seen_usernames: set[str] = set()

        for i, res in enumerate(results_list):
            if isinstance(res, Exception):
                logger.warning(
                    "apify_keyword_failed",
                    keyword=keywords[i],
                    error=str(res),
                )
                continue
            for item in res:
                username = item.get("username", item.get("ownerUsername", ""))
                if username and username not in seen_usernames:
                    seen_usernames.add(username)
                    all_results.append(item)

        logger.info(
            "apify_multi_keyword_done",
            keywords_count=len(keywords),
            total_unique_results=len(all_results),
        )
        return all_results

    async def scrape_hashtag_posts(
        self,
        hashtag: str,
        results_limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Obtiene posts de un hashtag con geotags y engagement vía instagram-hashtag-scraper."""
        client = await self._get_client()

        clean_hashtag = hashtag.lstrip("#")

        logger.info(
            "apify_hashtag_posts_start",
            hashtag=clean_hashtag,
            results_limit=results_limit,
        )

        run_input = {
            "hashtag": clean_hashtag,
            "resultsLimit": results_limit,
            "locationName": "Venezuela",
        }

        cache_key = self._build_cache_key(INSTAGRAM_HASHTAG_SCRAPER, run_input)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        run_data = await self._post_run(client, INSTAGRAM_HASHTAG_SCRAPER, run_input)
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        items = await self._poll_run(client, INSTAGRAM_HASHTAG_SCRAPER, run_id, default_dataset_id, cache_key=cache_key, cache_ttl=CACHE_TTL_PROFILES)
        logger.info(
            "apify_hashtag_posts_done",
            hashtag=clean_hashtag,
            results_count=len(items),
        )
        return items

    async def scrape_hashtags_batch(
        self,
        hashtags: list[str],
        results_per_hashtag: int = 30,
    ) -> dict[str, list[dict[str, Any]]]:
        """Hace scrape de múltiples hashtags en paralelo, devuelve dict hashtag -> posts."""
        if not hashtags:
            return {}

        logger.info(
            "apify_hashtags_batch_start",
            hashtags_count=len(hashtags),
            results_per_hashtag=results_per_hashtag,
        )

        tasks = [
            self.scrape_hashtag_posts(tag, results_limit=results_per_hashtag)
            for tag in hashtags
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        batch_results: dict[str, list[dict[str, Any]]] = {}
        for i, res in enumerate(results_list):
            hashtag = hashtags[i]
            if isinstance(res, Exception):
                logger.warning(
                    "apify_hashtag_batch_failed",
                    hashtag=hashtag,
                    error=str(res),
                )
                batch_results[hashtag] = []
            else:
                batch_results[hashtag] = res

        total_posts = sum(len(v) for v in batch_results.values())
        logger.info(
            "apify_hashtags_batch_done",
            hashtags_count=len(hashtags),
            total_posts=total_posts,
        )
        return batch_results

    async def analyze_profile_engagement(
        self,
        usernames: list[str],
        posts_to_analyze: int = 30,
    ) -> list[dict[str, Any]]:
        """Obtiene métricas avanzadas de engagement para perfiles vía engagement-analytics actor."""
        if not usernames:
            return []

        client = await self._get_client()

        logger.info(
            "apify_engagement_analytics_start",
            usernames_count=len(usernames),
            posts_to_analyze=posts_to_analyze,
        )

        run_input = {
            "usernames": [u.lstrip("@") for u in usernames],
            "postsToAnalyze": posts_to_analyze,
        }

        cache_key = self._build_cache_key(ENGAGEMENT_ANALYTICS_SCRAPER, run_input)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        run_data = await self._post_run(client, ENGAGEMENT_ANALYTICS_SCRAPER, run_input)
        run_id = run_data["data"]["id"]
        default_dataset_id = run_data["data"].get("defaultDatasetId")

        results = await self._poll_run(client, ENGAGEMENT_ANALYTICS_SCRAPER, run_id, default_dataset_id, cache_key=cache_key, cache_ttl=CACHE_TTL_PROFILES)
        logger.info(
            "apify_engagement_analytics_done",
            usernames_count=len(usernames),
            results_count=len(results),
        )
        return results

    async def _enrich_profile_with_er(self, profile: dict[str, Any]) -> None:
        """Calcula engagement_rate desde latestPosts (o posts fallback) y lo inyecta en el profile."""
        if profile.get("engagement_rate") is not None:
            return

        followers = profile.get("followersCount", 0) or 0
        if followers == 0:
            profile["engagement_rate"] = None
            return

        posts = profile.get("latestPosts") or []

        if not posts:
            posts = await self._fetch_posts_for_er(profile.get("username", ""))
            if posts:
                logger.info("apify_er_posts_fallback", username=profile.get("username"), posts_count=len(posts))

        if not posts:
            profile["engagement_rate"] = None
            return

        n = len(posts)
        total_likes = sum(p.get("likesCount", 0) or 0 for p in posts)
        total_comments = sum(p.get("commentsCount", 0) or 0 for p in posts)

        if n == 0 or (total_likes == 0 and total_comments == 0):
            profile["engagement_rate"] = None
            return

        er = (total_likes + total_comments) / (followers * n)
        profile["engagement_rate"] = round(er, 6)

    async def _fetch_posts_for_er(self, username: str) -> list[dict[str, Any]]:
        """Fallback: obtiene posts recientes de un perfil para calcular ER."""
        client = await self._get_client()
        run_input = {
            "usernames": [username.lstrip("@")],
            "resultsType": "posts",
            "postsLimit": 12,
        }

        try:
            run_data = await self._post_run(client, INSTAGRAM_PROFILE_SCRAPER, run_input)
            run_id = run_data["data"]["id"]
            default_dataset_id = run_data["data"].get("defaultDatasetId")

            items = await self._poll_run(client, INSTAGRAM_PROFILE_SCRAPER, run_id, default_dataset_id, cache_key=None)
            return items[:12] if items else []
        except Exception as e:
            logger.warning("apify_er_posts_fallback_failed", username=username, error=str(e))
            return []

    async def _poll_run(
        self,
        client: httpx.AsyncClient,
        actor_id: str,
        run_id: str,
        default_dataset_id: str | None,
        max_wait: int = 300,
        cache_key: str | None = None,
        cache_ttl: int = CACHE_TTL_PROFILES,
    ) -> list[dict[str, Any]]:
        """Poll hasta que el run complete (max 5 minutos) con backoff exponencial."""
        import asyncio

        status_codes = (200, 429, 500, 502, 503, 504)
        base_delay = 5

        for i in range(max_wait // 5):
            try:
                status_resp = await client.get(f"/acts/{actor_id}/runs/{run_id}")
                status_resp.raise_for_status()
                status_data = status_resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and i < (max_wait // 5) - 1:
                    delay = base_delay * (2 ** min(i, 5))
                    logger.warning("apify_rate_limited", run_id=run_id, attempt=i+1, backoff_secs=delay)
                    await asyncio.sleep(delay)
                    continue
                raise

            status = status_data.get("data", {}).get("status")

            cost_usd = status_data.get("data", {}).get("usageTotalUsd", 0.0) or 0.0
            if cost_usd > 0 and discovery_run_id:
                self.record_cost(discovery_run_id, cost_usd)

            logger.info("apify_poll", run_id=run_id, actor_id=actor_id, status=status, attempt=i + 1, cost_usd=cost_usd)

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
                    cost_usd=cost_usd,
                    first_item_keys=list(items[0].keys()) if items else [],
                )

                if cache_key and items:
                    await self._set_cached(cache_key, items, cache_ttl)

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
