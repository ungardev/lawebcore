"""HikerAPI client — Instagram data via https://api.hikerapi.com."""

import asyncio
import hashlib
import json
from typing import Any

import httpx
import structlog
from shared_core.config import settings

from discovery.exceptions import SourceUnavailable, TransientSourceError

logger = structlog.get_logger(__name__)

CACHE_TTL_HASHTAG = 43200
CACHE_TTL_PROFILE = 86400
CACHE_TTL_LOCATION = 30 * 86400


class HikerAPIClient:
    """HikerAPI REST client. Docs: https://api.hikerapi.com/docs."""

    BASE_URL = "https://api.hikerapi.com"
    TIMEOUT = 30.0
    SAFE_INT = True

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.HIKERAPI_API_KEY
        self._client: httpx.AsyncClient | None = None
        self._redis = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "x-access-key": self.api_key,
                    "accept": "application/json",
                },
                timeout=self.TIMEOUT,
            )
        return self._client

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as redis_async
            self._redis = redis_async.from_url(settings.ARQ_REDIS_URL, decode_responses=False)
        return self._redis

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _cache_key(self, prefix: str, params: dict) -> str:
        stable = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.sha1(stable.encode()).hexdigest()
        return f"hikerapi:cache:{prefix}:{h}"

    async def _get_cached(self, cache_key: str) -> dict | None:
        try:
            r = await self._get_redis()
            data = await r.get(cache_key)
            if data:
                logger.info("hikerapi_cache_hit", key=cache_key)
                return json.loads(data)
            logger.info("hikerapi_cache_miss", key=cache_key)
            return None
        except Exception as e:
            logger.warning("hikerapi_cache_error", error=str(e))
            return None

    async def _set_cached(self, cache_key: str, data: Any, ttl: int) -> None:
        try:
            r = await self._get_redis()
            await r.setex(cache_key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning("hikerapi_cache_set_error", error=str(e))

    async def _get_debug(
        self,
        path: str,
        params: dict | None = None,
    ) -> tuple[dict | None, int | None]:
        """GET with full response debug. Returns (data, status_code)."""
        client = await self._get_client()
        try:
            response = await client.get(path, params=params)
            status = response.status_code
            if response.status_code == 429:
                logger.warning("hikerapi_rate_limited", path=path)
                return None, 429
            if response.status_code == 404:
                return None, 404
            if response.status_code in (401, 403):
                logger.error(
                    "hikerapi_auth_error",
                    path=path,
                    status=status,
                    response_body=response.text[:500],
                    hint="Verify x-access-key header is correct and key is active",
                )
                return None, status
            response.raise_for_status()
            data = response.json()
            logger.info(
                "hikerapi_response_debug",
                path=path,
                status=status,
                data_keys=list(data.keys()) if isinstance(data, dict) else type(data).__name__,
                data_preview=str(data)[:300],
            )
            return data, status
        except httpx.HTTPStatusError as e:
            logger.error(
                "hikerapi_http_error",
                path=path,
                status=e.response.status_code,
                response_body=e.response.text[:500] if hasattr(e.response, "text") else "",
            )
            return None, e.response.status_code
        except Exception as e:
            logger.error("hikerapi_request_error", path=path, error=str(e))
            return None, None

    async def _get(
        self,
        path: str,
        params: dict | None = None,
        cache_ttl: int = 0,
    ) -> dict | None:
        from discovery.tools.hikerapi_circuit_breaker import HikerAPICircuitBreaker

        breaker = HikerAPICircuitBreaker(provider="hikerapi")
        if not await breaker.can_proceed():
            raise SourceUnavailable(
                "Circuit breaker open — HikerAPI degradado por errores 5xx recientes.",
                status_code=503,
                provider="hikerapi",
            )

        cache_key = None
        if cache_ttl > 0:
            cache_key = self._cache_key(path, params or {})
            cached = await self._get_cached(cache_key)
            if cached is not None:
                return cached

        client = await self._get_client()
        try:
            response = await client.get(path, params=params)
            if response.status_code == 429:
                logger.warning("hikerapi_rate_limited", path=path)
                raise SourceUnavailable(
                    f"429 Rate Limited — {response.text[:200]}",
                    status_code=429,
                    provider="hikerapi",
                )
            if response.status_code == 404:
                return None
            if response.status_code in (401, 403):
                logger.error(
                    "hikerapi_auth_error",
                    path=path,
                    status=response.status_code,
                    response_body=response.text[:500],
                    hint="Verify x-access-key header is correct and key is active",
                )
                raise SourceUnavailable(
                    f"{response.status_code} {response.text[:200]}",
                    status_code=response.status_code,
                    provider="hikerapi",
                )
            if response.status_code >= 500:
                logger.warning("hikerapi_server_error", path=path, status=response.status_code)
                await breaker.record_failure()
                raise TransientSourceError(
                    f"{response.status_code} server error — {response.text[:200]}",
                    status_code=response.status_code,
                    provider="hikerapi",
                )
            response.raise_for_status()
            await breaker.record_success()
            data = response.json()
            if cache_key and data:
                await self._set_cached(cache_key, data, cache_ttl)
            return data
        except SourceUnavailable:
            raise
        except TransientSourceError:
            raise
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status >= 500:
                await breaker.record_failure()
                raise TransientSourceError(
                    f"HTTP {status} — {e.response.text[:200]}" if hasattr(e.response, "text") else str(e),
                    status_code=status,
                    provider="hikerapi",
                )
            logger.error(
                "hikerapi_http_error",
                path=path,
                status=status,
                response_body=e.response.text[:500] if hasattr(e.response, "text") else "",
            )
            return None
        except httpx.TimeoutException as e:
            await breaker.record_failure()
            raise TransientSourceError(f"Timeout after {self.TIMEOUT}s — {e}", provider="hikerapi")
        except (httpx.HTTPError, ValueError) as e:
            logger.error("hikerapi_request_error", path=path, error=str(e))
            return None

    async def search_hashtag(
        self,
        hashtag: str,
        country: str = "VE",
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """GET /v2/hashtag/medias/top — top posts for a hashtag.

        HikerAPI returns the BEST posts for a hashtag (not random posts like Apify).
        Each post includes the full user object — most posters here are real creators.
        """
        clean = hashtag.lstrip("#")
        results: list[dict[str, Any]] = []
        cursor = None

        info = await self._get("/v2/hashtag/by/name", params={"name": clean, "safe_int": self.SAFE_INT}, cache_ttl=CACHE_TTL_HASHTAG)
        if not info:
            logger.warning("hikerapi_hashtag_not_found", hashtag=clean)
            return []
        hashtag_id = info.get("id")
        media_count = info.get("media_count", 0)
        logger.info("hikerapi_hashtag_info", hashtag=clean, media_count=media_count, id=hashtag_id)
        if media_count < 50:
            logger.warning("hikerapi_hashtag_low_volume", hashtag=clean, media_count=media_count)
            return []

        for _ in range(3):
            params: dict[str, Any] = {"name": clean, "safe_int": self.SAFE_INT}
            if cursor:
                params["page_id"] = cursor

            resp = await self._get("/v2/hashtag/medias/top", params=params, cache_ttl=0)
            if not resp:
                break

            raw_items = self._extract_media_items(resp)
            if not raw_items:
                logger.warning(
                    "hikerapi_hashtag_no_media",
                    hashtag=clean,
                    sections_count=len(resp.get("response", {}).get("sections", [])),
                    response_keys=list(resp.keys()),
                )
                break

            for post in raw_items:
                if len(results) >= limit:
                    break
                user = self._extract_user_from_post(post)
                if not user or not user.get("username"):
                    continue
                normalized = self._normalize_user(user)
                normalized["_source_hashtag"] = clean
                normalized["_post_likers_count"] = post.get("like_count", 0) or post.get("likes_count", 0)
                normalized["_post_comments_count"] = post.get("comment_count", 0) or post.get("comments_count", 0)
                results.append(normalized)

            cursor = resp.get("next_page_id")
            if not cursor or resp.get("more_available") is False:
                break

            await asyncio.sleep(0.3)

        logger.info("hikerapi_hashtag_results", hashtag=clean, results=len(results))
        return results

    async def search_hashtag_recent(
        self,
        hashtag: str,
        page_id: str = "",
        limit: int = 27,
    ) -> list[dict[str, Any]]:
        """GET /v2/hashtag/medias/recent — RECOMMENDED: rising stars in the niche.

        Returns recent posts for a hashtag — captures nano/micro creators in growth
        phase who don't yet appear in top posts. Use alongside search_hashtag (top).
        """
        clean = hashtag.lstrip("#")
        results: list[dict[str, Any]] = []
        cursor = page_id

        info = await self._get("/v2/hashtag/by/name", params={"name": clean, "safe_int": self.SAFE_INT}, cache_ttl=CACHE_TTL_HASHTAG)
        if not info:
            logger.warning("hikerapi_hashtag_recent_not_found", hashtag=clean)
            return results

        for _ in range(2):
            params: dict[str, Any] = {"name": clean, "page_id": cursor, "safe_int": self.SAFE_INT}
            resp = await self._get("/v2/hashtag/medias/recent", params=params, cache_ttl=1800)
            if not resp:
                break

            raw_items = self._extract_media_items(resp)
            for post in raw_items:
                if len(results) >= limit:
                    break
                user = self._extract_user_from_post(post)
                if not user or not user.get("username"):
                    continue
                normalized = self._normalize_user(user)
                normalized["_source_hashtag"] = f"{clean}_recent"
                normalized["_post_likers_count"] = post.get("like_count", 0) or post.get("likes_count", 0)
                normalized["_post_comments_count"] = post.get("comment_count", 0) or post.get("comments_count", 0)
                results.append(normalized)

            cursor = resp.get("next_page_id", "")
            if not cursor:
                break
            await asyncio.sleep(0.3)

        logger.info("hikerapi_hashtag_recent_results", hashtag=clean, results=len(results))
        return results

    async def search_keyword(
        self,
        keyword: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """GET /v3/fbsearch/accounts — search users by keyword (v3 recommended over v2).

        Returns accounts matching the keyword query, filtered to user-type only.
        """
        results: list[dict[str, Any]] = []
        cursor = None

        for _ in range(3):
            params: dict[str, Any] = {
                "query": keyword,
                "page_token": cursor or "",
                "safe_int": self.SAFE_INT,
            }

            resp = await self._get("/v3/fbsearch/accounts", params=params)
            if not resp:
                logger.warning("hikerapi_keyword_no_response", keyword=keyword)
                break

            raw_users = resp.get("users", [])
            if not raw_users:
                logger.warning(
                    "hikerapi_keyword_no_users",
                    keyword=keyword,
                    num_results=resp.get("num_results", 0),
                    has_more=resp.get("has_more"),
                    hint="may be trial-limited or query too specific",
                )
                break

            for u in raw_users:
                if len(results) >= limit:
                    break
                user = u.get("user", {}) or u
                if not user.get("username"):
                    continue
                normalized = self._normalize_user(user)
                results.append(normalized)

            cursor = resp.get("page_token")
            has_more = resp.get("has_more")
            if not cursor or not has_more:
                break

            await asyncio.sleep(0.3)

        logger.info("hikerapi_keyword_results", keyword=keyword, results=len(results))
        return results

    async def enrich_profile(
        self,
        username: str,
    ) -> dict[str, Any] | None:
        """GET /v2/user/by/username — full profile lookup.

        Returns complete profile including is_business, follower_count, biography.
        """
        clean = username.lstrip("@")
        resp = await self._get(
            "/v2/user/by/username",
            params={"username": clean, "safe_int": self.SAFE_INT},
            cache_ttl=CACHE_TTL_PROFILE,
        )
        if not resp:
            logger.warning("hikerapi_profile_not_found", username=clean)
            return None

        user = resp.get("user", {}) or resp
        if not user.get("username"):
            return None

        normalized = self._normalize_user(user)
        logger.info("hikerapi_profile_enriched", username=clean, followers=normalized.get("follower_count"))
        return normalized

    async def search_top_accounts(
        self,
        query: str,
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        """GET /gql/topsearch?flat=true — RECOMMENDED mixed user+media search.

        Replaces /v3/fbsearch/topsearch which has pagination bugs.
        Returns top accounts interleaved with top media. Use flat=true for
        clean items list; discriminate by __typename: XDTUserDict vs XDTMediaDict.
        """
        results: list[dict[str, Any]] = []
        resp = await self._get(
            "/gql/topsearch",
            params={"query": query, "flat": "true", "safe_int": self.SAFE_INT},
            cache_ttl=43200,
        )
        if not resp:
            return []
        rows = resp.get("stream_rows", []) or resp.get("items", []) or []
        for row in rows:
            data = row.get("data", {}) if isinstance(row, dict) else row
            typename = data.get("__typename", "")
            if typename == "XDTUserDict":
                user = data.get("user", {}) or data
                if user.get("username"):
                    normalized = self._normalize_user(user)
                    normalized["_source_topsearch"] = query
                    results.append(normalized)
                    if len(results) >= limit:
                        break
            elif typename == "XDTMediaDict":
                user = data.get("user", {}) or {}
                if user.get("username"):
                    normalized = self._normalize_user(user)
                    normalized["_source_topsearch_media"] = query
                    results.append(normalized)
                    if len(results) >= limit:
                        break
        logger.info("hikerapi_topsearch_results", query=query, results=len(results))
        return results

    async def gql_topsearch(
        self,
        query: str,
        end_cursor: str | None = None,
        flat: bool = True,
    ) -> dict[str, Any]:
        """GET /gql/topsearch — RECOMMENDED for mixed user+media discovery.

        Returns raw stream_rows structure. Use flat=true to get items[] list.
        Discriminate by __typename: XDTUserDict (accounts) vs XDTMediaDict (posts).
        """
        params: dict[str, Any] = {"query": query, "flat": str(flat).lower(), "safe_int": self.SAFE_INT}
        if end_cursor:
            params["end_cursor"] = end_cursor
        return await self._get("/gql/topsearch", params=params, cache_ttl=0) or {}

    async def search_reels_by_keyword(
        self,
        query: str,
        rank_token: str = "discovery_reels",
        reels_max_id: str | None = None,
    ) -> dict[str, Any]:
        """GET /v2/fbsearch/reels — RECOMMENDED: discover creators via reels by keyword.

        Reels are the #1 discovery channel on IG. Returns creators who post
        reels matching the query — captures active nano/micro creators.
        """
        params: dict[str, Any] = {
            "query": query,
            "rank_token": rank_token,
            "safe_int": self.SAFE_INT,
        }
        if reels_max_id:
            params["reels_max_id"] = reels_max_id
        return await self._get("/v2/fbsearch/reels", params=params, cache_ttl=0) or {}

    async def search_accounts_v3(
        self,
        query: str,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """GET /v3/fbsearch/accounts — v3 with proper pagination support.

        Recommended over v2 (which doesn't support paging). Returns users list
        with page_token for next page.
        """
        params: dict[str, Any] = {"query": query, "safe_int": self.SAFE_INT}
        if page_token:
            params["page_token"] = page_token
        return await self._get("/v3/fbsearch/accounts", params=params) or {}

    async def search_followers_of(
        self,
        user_id: int | str,
        query: str,
        force: bool = True,
    ) -> dict[str, Any]:
        """GET /v1/user/search/followers — network expansion: find similar VE creators.

        Searches within a user's followers for those matching the query keyword.
        Key VE discovery technique: take top seed account, find VE-similar
        creators in their follower base.
        """
        params = {
            "user_id": str(user_id),
            "query": query,
            "force": str(force).lower(),
            "safe_int": self.SAFE_INT,
        }
        return await self._get("/v1/user/search/followers", params=params) or {}

    async def web_profile_info(self, user_id: int | str) -> dict[str, Any]:
        """GET /gql/user/web_profile_info — RECOMMENDED rich profile via GraphQL.

        Best profile info endpoint (raw IG GraphQL). Since Feb 2026, /v1/user/web_profile_info
        fails ~90% with UserNotFound. Use this instead for richer data including
        edge_followed_by, bio_links, friendship_status.
        """
        return await self._get(
            "/gql/user/web_profile_info",
            params={"user_id": str(user_id), "safe_int": self.SAFE_INT},
        ) or {}

    async def get_user_about(self, user_id: int | str) -> dict[str, Any] | None:
        """GET /v1/user/about — fraud detection signals for a user.

        Returns structural signals that complement AI-based bot detection:
        - former_usernames: list of previous usernames (bots frequently change username)
        - account_age_days: days since account creation (new accounts = higher risk)
        - country: ISO country code from account registration

        Cost: $0.0006 per call. Call for top 20 ranked candidates per run.
        """
        resp = await self._get(
            "/v1/user/about",
            params={"id": str(user_id)},
            cache_ttl=86400,
        )
        if not resp:
            logger.warning("hikerapi_user_about_not_found", user_id=user_id)
            return None
        user_data = resp.get("user", {}) or resp
        if not user_data.get("pk") and not user_data.get("id"):
            logger.warning("hikerapi_user_about_no_pk", user_id=user_id)
            return None
        former_usernames = user_data.get("former_usernames", []) or []
        return {
            "former_usernames": former_usernames,
            "former_usernames_count": len(former_usernames),
            "account_age_days": user_data.get("account_age_days") or user_data.get("account_age") or 0,
            "country": user_data.get("country") or "",
        }

    async def search_location(self, query: str) -> list[dict[str, Any]]:
        """GET /v1/fbsearch/places — Find location IDs by city/country query.

        Returns a list of location objects with pk (location ID) needed for
        location_medias_top and location_medias_recent.
        """
        resp = await self._get(
            "/v1/fbsearch/places",
            params={"query": query},
            cache_ttl=CACHE_TTL_LOCATION,
        )
        if not resp:
            logger.warning("hikerapi_location_search_empty", query=query)
            return []
        items = resp if isinstance(resp, list) else []
        logger.info("hikerapi_location_search_done", query=query, locations_found=len(items))
        return items

    async def location_medias_top(
        self,
        location_id: int | str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """GET /v1/location/medias/top — Top posts at a specific location.

        Gets the most popular posts geotagged at a specific location.
        Use search_location first to get location_id.
        """
        resp = await self._get(
            "/v1/location/medias/top",
            params={"location_pk": str(location_id)},
        )
        if not resp:
            return []
        items = resp.get("response", {}).get("items", []) if isinstance(resp, dict) else []
        logger.info("hikerapi_location_medias_top_done", location_id=location_id, items=len(items))
        return items[:limit]

    async def location_medias_recent(
        self,
        location_id: int | str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """GET /v1/location/medias/recent/chunk — Recent posts at a specific location.

        Gets the most recent posts geotagged at a specific location.
        Captures nano/micro creators who recently posted from that location.
        """
        resp = await self._get(
            "/v1/location/medias/recent/chunk",
            params={"location_pk": str(location_id)},
        )
        if not resp:
            return []
        items = resp.get("response", {}).get("items", []) if isinstance(resp, dict) else []
        logger.info("hikerapi_location_medias_recent_done", location_id=location_id, items=len(items))
        return items[:limit]

    async def suggested_profiles(
        self,
        username: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """GET /v2/user/suggested/profiles — 'Similar accounts' via IG algorithm.

        Uses the profile's numeric pk to fetch accounts suggested by Instagram's
        algorithm as similar. No cache — dynamic per query.
        REQUIRES numeric user_id (pk), not username. Falls back to enrich_profile
        to resolve pk first.
        """
        profile = await self.enrich_profile(username)
        if not profile or not profile.get("pk"):
            logger.warning("hikerapi_suggested_no_pk", username=username)
            return []
        pk_id = profile["pk"]
        results: list[dict[str, Any]] = []
        resp = await self._get(
            "/v2/user/suggested/profiles",
            params={"user_id": str(pk_id), "expand_suggestion": "true", "safe_int": self.SAFE_INT},
        )
        if not resp:
            return []
        for sp in resp.get("suggested_profiles", [])[:limit]:
            username_val = sp.get("username") or (sp.get("user", {}) or {}).get("username", "")
            if not username_val:
                continue
            normalized = self._normalize_user(sp.get("user", sp) if sp.get("user") else sp)
            normalized["_source_suggested"] = username
            results.append(normalized)
        logger.info("hikerapi_suggested_results", seed=username, results=len(results))
        return results

    def _extract_media_items(self, resp: dict) -> list[dict]:
        """Extrae media objects de la estructura anidada de /v2/hashtag/medias/top.

        Estructuras descubiertas via test_hikerapi --raw:
        - layout_type="one_by_two_left" / "two_column" / etc:
            layout_content = {X: {clips: {items: [{media: {...}}, ...]}}}
        - layout_type="media_grid":
            layout_content = {medias: [{media: {...}}, ...]}
        - feed_type="clips" con fill_items (lista directa):
            layout_content = {'one_by_two_item': {...}, 'fill_items': [{'media': {...}}, ...]}
        """
        media_items = []
        sections = resp.get("response", {}).get("sections", [])
        for section in sections:
            layout_content = section.get("layout_content", {})
            if not isinstance(layout_content, dict):
                continue

            for media_wrapper in layout_content.get("medias", []):
                if isinstance(media_wrapper, dict):
                    media = media_wrapper.get("media")
                    if isinstance(media, dict):
                        media_items.append(media)
                    elif "pk" in media_wrapper or "id" in media_wrapper:
                        media_items.append(media_wrapper)

            for layout_key, layout_value in layout_content.items():
                if layout_key == "medias":
                    continue
                if isinstance(layout_value, list):
                    for item in layout_value:
                        if not isinstance(item, dict):
                            continue
                        if "media" in item and isinstance(item["media"], dict):
                            media_items.append(item["media"])
                        elif "pk" in item or "id" in item:
                            media_items.append(item)
                    continue
                if not isinstance(layout_value, dict):
                    continue
                clips = layout_value.get("clips")
                if not isinstance(clips, dict):
                    continue
                for item in clips.get("items", []):
                    if not isinstance(item, dict):
                        continue
                    if "media" in item and isinstance(item["media"], dict):
                        media_items.append(item["media"])
                    elif "pk" in item or "id" in item:
                        media_items.append(item)
        return media_items

    def _extract_user_from_post(self, post: dict) -> dict | None:
        user = post.get("user")
        if not user:
            users = post.get("users")
            if isinstance(users, list) and users and isinstance(users[0], dict):
                user = users[0]
            elif isinstance(users, dict):
                user = users
        if not user:
            caption = post.get("caption")
            if isinstance(caption, dict):
                user = caption.get("user")
        return user if isinstance(user, dict) else None

    def _normalize_user(self, user: dict) -> dict[str, Any]:
        pk = user.get("pk") or user.get("id") or user.get("user_id")
        follower_count = user.get("follower_count", 0) or 0
        following_count = user.get("following_count", 0) or 0
        media_count = user.get("media_count", 0) or user.get("posts_count", 0) or 0

        hd_pic = user.get("hd_profile_pic_url_info", {}).get("url", "") if isinstance(user.get("hd_profile_pic_url_info"), dict) else ""
        profile_pic = user.get("profile_pic_url", "") or hd_pic

        country_raw = (
            user.get("country_code")
            or user.get("country")
            or ((user.get("account_type") or {}).get("country") if isinstance(user.get("account_type"), dict) else None)
            or ((user.get("user") or {}).get("country_code") if isinstance(user.get("user"), dict) else None)
            or ((user.get("hikerapi_country") or {}).get("iso_code") if isinstance(user.get("hikerapi_country"), dict) else None)
            or ""
        )
        country_iso = ""
        if country_raw:
            country_iso = str(country_raw).upper()[:2]

        return {
            "username": user.get("username", ""),
            "full_name": user.get("full_name", "") or user.get("fullName", ""),
            "biography": user.get("biography", ""),
            "bio": user.get("biography", ""),
            "avatar_url": hd_pic or profile_pic,
            "profilePicUrl": profile_pic,
            "profilePicUrlHD": hd_pic,
            "follower_count": follower_count,
            "followersCount": follower_count,
            "following_count": following_count,
            "followsCount": following_count,
            "posts_count": media_count,
            "postsCount": media_count,
            "is_business": bool(user.get("is_business", False)),
            "isBusinessAccount": bool(user.get("is_business", False)),
            "is_verified": bool(user.get("is_verified", False)),
            "verified": bool(user.get("is_verified", False)),
            "is_private": bool(user.get("is_private", False)),
            "pk": str(pk) if pk else None,
            "country": country_iso,
            "locationName": user.get("location_name", "") or user.get("city", ""),
        }


hikerapi_client = HikerAPIClient()
