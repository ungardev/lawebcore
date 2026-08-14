"""
ARQ worker for La Web Core async jobs.
Handles:
- AI embedding generation
- AI generation tasks (brief, post-mortem, etc.)
- Campaign automation triggers
- Scheduled report generation
- Discovery run execution (HikerAPI, Meta, TikTok, YouTube)
- Integration syncs
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings
from discovery.candidate_analyzer import candidate_analyzer
from discovery.memory import conversation_memory
from discovery.query_builder import query_builder
from discovery.schemas import BriefStructured, Platform
from discovery.scoring.lens_score import lens_score
from discovery.scoring.niche import niche_relevance
from discovery.tools import (
    build_rationale,
    classify_tier,
    meta_client,
    metricool_client,
    tiktok_client,
    youtube_client,
)
from discovery.tools.geo_boost import geo_score, has_hard_geo_signal
from discovery.tools.hikerapi_client import HikerAPIClient
from shared_core import railway_pg, settings

from app.core.discovery_cost_tracker import get_discovery_cost_tracker
from app.core.metrics import (
    lens_active_runs,
    lens_candidates_total,
)

logger = structlog.get_logger(__name__)

_replay_miss_count_for_run: int = 0

MAX_HANDLES_TO_ENRICH = 50
MAX_POSTS_PER_HASHTAG = 20
TIER_MIN_FOLLOWERS = 5_000
TIER_MAX_FOLLOWERS = 50_000
MIN_FOLLOWERS_BOT_CHECK = 1000

TIER_DISTRIBUTION = {"NANO": 0.55, "MICRO": 0.30, "MID": 0.10, "MACRO": 0.05}

VE_GEO_SUFFIXES = ["venezuela", "vzla"]

MAX_REELS_PER_QUERY = 3
MAX_FOLLOWER_EXPANSION_PER_SEED = 5

ENRICHMENT_INCLUDE_ABOUT = os.getenv("HIKERAPI_INCLUDE_ABOUT", "false").lower() == "true"

DEFAULT_COMMERCE_SIGNAL_KEYWORDS = [
    ["tienda", "shop"],
    ["ventas", "pedidos"],
    ["catálogo", "mayor y detal"],
    ["envíos", "delivery"],
    ["comprar", "adquirir"],
    ["whatsapp", "telf", "teléfono"],
    ["precio", "oferta", "descuento"],
    ["horario", "sucursal", "local"],
    ["market", "boutique", "almacén"],
]
DEFAULT_CREATOR_SIGNAL_KEYWORDS = [
    ["creador", "content creator", "reviewer"],
    ["vlogger", "youtuber", "tiktoker"],
    ["streamer", "entrenador", "coach"],
    ["atleta", "deportista", "fitness"],
    ["influencer", "blogger", "periodista"],
    ["presentador", "comunicador", "actor"],
    ["cantante", "músico", "artista"],
    ["creativo", "emprendedor"],
    ["diseñador", "fotógrafo"],
]
DEFAULT_EXCLUSION_KEYWORDS = [
    "político", "política", "politología", "politólogo",
    "gobierno", "gobierno de", "gobierno nacional",
    "maduro", "madurista", "maduristas",
    "chavismo", "chavista", "chavistas", "chávez", "chavez",
    "oposición", "opositor", "opositores",
    "ventevenezuela", "vente venezuela",
    "voluntadpopular", "voluntad popular",
    "asambleanacional", "asamblea nacional",
    "tribunalsupremo", "tribunal supremo",
    "elecciones", "fraude electoral", "fraude",
    "votar", "voto", "candidato", "candidata",
    "protesta", "manifestación", "marcha",
    "dictadura", "dictador", "régimen", "regimen",
    "embargo", "sanción", "sanciones", "bloqueo",
    "libertad", "libertades",
    "venezuelalibre", "venezuela libre",
]


def _tier_of(followers: int) -> str:
    if followers < 10_000:
        return "NANO"
    if followers < 100_000:
        return "MICRO"
    if followers < 500_000:
        return "MID"
    return "MACRO"


def _rerank_diversified(scored: list[dict], target_n: int = 80) -> list[dict]:
    buckets: dict[str, list[dict]] = {"NANO": [], "MICRO": [], "MID": [], "MACRO": []}
    for c in scored:
        buckets[_tier_of(c.get("followers") or 0)].append(c)
    for bucket in buckets.values():
        bucket.sort(key=lambda x: x.get("match_score") or 0, reverse=True)
    final: list[dict] = []
    for tier, pct in TIER_DISTRIBUTION.items():
        quota = max(1, int(target_n * pct))
        final.extend(buckets[tier][:quota])
    if len(final) < target_n:
        remaining = sorted(
            [c for b in buckets.values() for c in b if c not in final],
            key=lambda x: x.get("match_score") or 0,
            reverse=True,
        )
        final.extend(remaining[: target_n - len(final)])
    return final[:target_n]


async def startup(ctx):
    """Initialize worker context (DB, Redis) and start health server."""
    logger.info("workers_starting", env=settings.API_ENV, version="0.1.0")
    ctx["redis"] = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
    if os.environ.get("STANDALONE_WORKER") == "true":
        import asyncio

        from app.workers.health_server import run_health_server
        asyncio.create_task(run_health_server())


async def shutdown(ctx):
    """Cleanup on shutdown."""
    logger.info("workers_stopping")
    await meta_client.close()
    await youtube_client.close()
    await metricool_client.close()
    await tiktok_client.close()


# ---- Progress reporting helpers ----

async def _get_conversation_id_for_run(run_id: str) -> str | None:
    """Busca el conversation_id asociado a un discovery_run."""
    try:
        conv = await railway_pg.select_one(
            table="discovery_conversations",
            select="id",
            filters=[f"discovery_run_id=eq.{run_id}"],
        )
        return conv.get("id") if conv else None
    except Exception as e:
        logger.warning("get_conversation_id_failed", run_id=run_id, error=str(e))
        return None


async def _save_progress_message(
    run_id: str,
    content: str,
    tool: str = "discovery_pipeline",
) -> None:
    """Guarda un mensaje de progreso en el conversation asociado al run."""
    from uuid import UUID as pyUUID
    try:
        conv_id = await _get_conversation_id_for_run(run_id)
        if not conv_id:
            logger.debug("no_conversation_for_run", run_id=run_id)
            return
        await conversation_memory.save_message(
            conversation_id=pyUUID(conv_id),
            role="assistant",
            content=content,
        )
    except Exception as e:
        logger.warning("save_progress_message_failed", run_id=run_id, error=str(e))


# ---- Discovery tasks ----

async def discovery_run_task(ctx, run_id: str) -> dict:
    """
    Ejecuta un discovery_run completo replicando extract_purina_real_apify.py v4.

    STEP 1: Hashtag search (single sync call — all hashtags at once)
    STEP 2: Keyword search (single sync call — all keywords at once)
    STEP 3: Profile enrichment (single sync call — up to 80 profiles)
    STEP 4: Scoring con geo_score + lens_score + cross_ref
    """
    from discovery.exceptions import ReplayMiss, SourceUnavailable
    global _replay_miss_count_for_run
    _replay_miss_count_for_run = 0
    try:
        await _run_set_status(run_id, "running")
        lens_active_runs.inc()

        print(f"[discovery_run_task] START run_id={run_id}", flush=True)

        run = await railway_pg.select_one(
            table="discovery_runs",
            select="*",
            filters=[f"id=eq.{run_id}"],
        )

        if not run:
            print(f"[discovery_run_task] ABORT: Run {run_id} not found", flush=True)
            return {"error": f"Run {run_id} not found"}

        from discovery.exceptions import BudgetExhausted, SourceUnavailable
        from discovery.tools.hikerapi_circuit_breaker import HikerAPICircuitBreaker

        from app.core.budget_fuse import BudgetFuse

        budget_fuse = BudgetFuse(
            monthly_budget_usd=settings.MONTHLY_BUDGET_USD,
            max_calls_per_run=settings.MAX_CALLS_PER_RUN,
            alert_threshold=settings.BUDGET_ALERT_THRESHOLD,
            cost_per_call_usd=settings.HIKERAPI_COST_PER_CALL_USD,
        )
        circuit_breaker = HikerAPICircuitBreaker(provider="hikerapi")

        try:
            await budget_fuse.assert_budget_available(run_id, provider="hikerapi")
        except BudgetExhausted as e:
            error_msg = str(e)
            await _run_set_status(run_id, "failed", error=error_msg)
            await _save_progress_message(
                run_id,
                f"🔴 Presupuesto mensual agotado: ${e.current_usd:.4f} de ${e.budget_usd:.2f}. "
                f"Recarga en hikerapi.com/billing para continuar.",
            )
            lens_active_runs.dec()
            return {"run_id": run_id, "error": error_msg, "candidates": 0}

        if not await circuit_breaker.can_proceed():
            raise SourceUnavailable(
                "Circuit breaker open — HikerAPI degradado por errores 5xx recientes. "
                "Espera unos minutos o contacta a soporte.",
                status_code=503,
                provider="hikerapi",
            )

        brief_parsed = run.get("brief_parsed", {})
        if isinstance(brief_parsed, str):
            import json
            brief_parsed = json.loads(brief_parsed)

        brief = BriefStructured(**brief_parsed)
        plan = await query_builder.build(brief)
        profile_data = plan.profile

        await _run_update_metadata(run_id, {
            "current_step": "step1_hashtag_search",
            "completed_steps": [],
            "keywords_count": len(plan.keyword_queries),
            "hashtags_count": len(plan.hashtag_queries),
            "candidates_found": 0,
            "replay_miss_count": 0,
        })

        profiles: dict[str, dict] = {}
        step1_handles: set[str] = set()
        step2_handles: set[str] = set()
        step3_handles: set[str] = set()
        step4_handles: set[str] = set()
        instagram_source = HikerAPIClient()
        instagram_source.run_id = run_id
        instagram_source.budget_fuse = budget_fuse

        location_items: list[dict] = []
        step0_handles: set[str] = set()
        step0_api_calls = 0
        step0_enabled = os.getenv("HIKERAPI_STEP0_LOCATION", "false").lower() == "true"

        if step0_enabled and hasattr(instagram_source, "search_location") and brief.audience_cities:
            logger.info("step0_location_search_starting", cities=brief.audience_cities)
            print(f"[STEP0] Location search starting with cities={brief.audience_cities}", flush=True)

            location_profiles: dict[str, dict] = {}
            cities_searched = 0
            locations_found = 0

            for city in brief.audience_cities[:6]:
                query = f"{city} Venezuela"
                try:
                    locations = await instagram_source.search_location(query)
                    step0_api_calls += 1
                    cities_searched += 1
                    if not locations:
                        continue

                    for loc in locations[:3]:
                        loc_pk = loc.get("location", {}).get("pk") or loc.get("pk")
                        if not loc_pk:
                            continue
                        locations_found += 1

                        for media_func, limit, src_label in [
                            (instagram_source.location_medias_top, 20, "top"),
                            (instagram_source.location_medias_recent, 20, "recent"),
                        ]:
                            try:
                                medias = await media_func(loc_pk, limit=limit)
                                step0_api_calls += 1
                                for media in medias:
                                    user = instagram_source._extract_user_from_post(media) if hasattr(instagram_source, "_extract_user_from_post") else (media.get("user") or {})
                                    if not user or not user.get("username"):
                                        continue
                                    normalized = instagram_source._normalize_user(user)
                                    normalized["_source_location"] = f"{city}__{src_label}"
                                    normalized["_source_city"] = city
                                    location_profiles[normalized["username"]] = normalized
                            except Exception as e:
                                logger.warning("step0_location_media_error", city=city, loc_pk=loc_pk, error=str(e))
                except Exception as e:
                    logger.warning("step0_location_search_error", city=city, error=str(e))

            for handle, p in location_profiles.items():
                step0_handles.add(handle)
                if handle in profiles:
                    continue
                profiles[handle] = {
                    "username": handle,
                    "full_name": p.get("full_name", ""),
                    "fullName": p.get("full_name", ""),
                    "bio": p.get("bio", ""),
                    "biography": p.get("bio", ""),
                    "avatar_url": p.get("avatar_url", "") or p.get("profilePicUrl", ""),
                    "profilePicUrl": p.get("profilePicUrl", "") or p.get("avatar_url", ""),
                    "follower_count": p.get("follower_count", 0),
                    "followersCount": p.get("followersCount", 0),
                    "following_count": p.get("following_count", 0),
                    "followsCount": p.get("followsCount", 0),
                    "posts_count": p.get("posts_count", 0),
                    "postsCount": p.get("postsCount", 0),
                    "is_business": p.get("is_business", False),
                    "isBusinessAccount": p.get("isBusinessAccount", False),
                    "is_verified": p.get("is_verified", False),
                    "verified": p.get("verified", False),
                    "pk": p.get("pk"),
                    "locationName": p.get("_source_city", ""),
                    "_source_location": p.get("_source_location", ""),
                }

            location_items = list(location_profiles.values())
            logger.info(
                "step0_location_search_done",
                cities_searched=cities_searched,
                locations_found=locations_found,
                profiles_added=len(location_items),
                api_calls_used=step0_api_calls,
            )
            print(f"[STEP0] Location search done: {len(location_items)} profiles from {cities_searched} cities, {locations_found} locations, {step0_api_calls} API calls", flush=True)


        async def _fetch_step1():
            from discovery.exceptions import SourceUnavailable
            results = []
            for tag in plan.hashtag_queries[:3]:
                try:
                    items = await instagram_source.search_hashtag(tag, limit=MAX_POSTS_PER_HASHTAG)
                    results.extend(items)
                except SourceUnavailable:
                    raise
                except Exception as e:
                    logger.warning("source_hashtag_error", source="hikerapi", hashtag=tag, error=str(e))
            return results

        async def _fetch_step1_recent():
            from discovery.exceptions import SourceUnavailable
            results = []
            for tag in plan.hashtag_queries[:2]:
                try:
                    items = await instagram_source.search_hashtag_recent(tag, limit=20)
                    results.extend(items)
                except SourceUnavailable:
                    raise
                except Exception as e:
                    logger.warning("source_hashtag_recent_error", source="hikerapi", hashtag=tag, error=str(e))
            return results

        async def _fetch_step2():
            from discovery.exceptions import SourceUnavailable
            results = []
            target_country = (brief.audience_countries or ["VE"])[0].upper()
            geo_suffixes = VE_GEO_SUFFIXES[:2]
            for kw in plan.keyword_queries[:3]:
                try:
                    items = await instagram_source.search_keyword(kw, limit=10)
                    results.extend(items)
                except SourceUnavailable:
                    raise
                except Exception as e:
                    logger.warning("source_keyword_error", source="hikerapi", keyword=kw, error=str(e))
                if target_country == "VE":
                    for geo in geo_suffixes:
                        combined_kw = f"{kw} {geo}"
                        try:
                            items = await instagram_source.search_keyword(combined_kw, limit=10)
                            results.extend(items)
                        except SourceUnavailable:
                            raise
                        except Exception as e:
                            logger.warning("source_keyword_geo_error", keyword=combined_kw, error=str(e))
            return results

        async def _fetch_step3():
            from discovery.exceptions import SourceUnavailable
            results = []
            for kw in plan.keyword_queries[:1]:
                try:
                    items = await instagram_source.search_top_accounts(kw, limit=10)
                    results.extend(items)
                except SourceUnavailable:
                    raise
                except Exception as e:
                    logger.warning("hikerapi_topsearch_error", keyword=kw, error=str(e))
            return results

        async def _fetch_step4():
            from discovery.exceptions import SourceUnavailable
            seeds = list(step1_handles | step2_handles)[:1]
            results = []
            for handle in seeds:
                try:
                    items = await instagram_source.suggested_profiles(handle, limit=10)
                    results.extend(items)
                    await asyncio.sleep(0.5)
                except SourceUnavailable:
                    raise
                except Exception as e:
                    logger.warning("hikerapi_suggested_error", handle=handle, error=str(e))
            return results

        async def _fetch_step2p5():
            from discovery.exceptions import SourceUnavailable
            results = []
            seeds = (plan.keyword_queries or [])[:1]
            for kw in seeds:
                try:
                    data = await instagram_source.search_reels_by_keyword(kw)
                    modules = data.get("reels_serp_modules", [])
                    for module in modules:
                        clips = module.get("clips", [])[:MAX_REELS_PER_QUERY]
                        for clip in clips:
                            media = clip.get("media", {}) or clip.get("user", {})
                            if isinstance(media, dict) and media.get("username"):
                                normalized = instagram_source._normalize_user(media) if hasattr(instagram_source, "_normalize_user") else media
                                normalized["_source_reels"] = kw
                                results.append(normalized)
                except SourceUnavailable:
                    raise
                except Exception as e:
                    logger.warning("source_reels_error", keyword=kw, error=str(e))
            logger.info("step2p5_reels_done", results=len(results))
            return results

        print("[discovery_run_task] STEP 1+2+2.5+3+4: Running", flush=True)
        step1_result, step2_result = await asyncio.gather(
            _fetch_step1(),
            _fetch_step2(),
            return_exceptions=True,
        )
        for res in (step1_result, step2_result):
            if isinstance(res, SourceUnavailable):
                raise res
            if isinstance(res, ReplayMiss):
                _replay_miss_count_for_run += 1

        step1_recent_result, step2p5_result = await asyncio.gather(
            _fetch_step1_recent(),
            _fetch_step2p5(),
            return_exceptions=True,
        )
        for res in (step1_recent_result, step2p5_result):
            if isinstance(res, SourceUnavailable):
                raise res
            if isinstance(res, ReplayMiss):
                _replay_miss_count_for_run += 1

        hashtag_items: list[dict] = []
        keyword_items: list[dict] = []
        hashtag_recent_items: list[dict] = []
        reels_items: list[dict] = []
        topsearch_items: list[dict] = []
        suggested_items: list[dict] = []


        if isinstance(step1_result, Exception):
            logger.error("step1_hashtag_failed", error=str(step1_result))
            print(f"[STEP1] FAILED: {step1_result}", flush=True)
        else:
            hashtag_items = step1_result
            print(f"[STEP1] {len(hashtag_items)} posts from hashtags source=hikerapi", flush=True)
            logger.info("step1_hashtag_done", hashtag_posts=len(hashtag_items), source="hikerapi")

        if isinstance(step2_result, Exception):
            logger.error("step2_keyword_failed", error=str(step2_result))
            print(f"[STEP2] FAILED: {step2_result}", flush=True)
        else:
            keyword_items = step2_result
            print(f"[STEP2] {len(keyword_items)} users from keywords source=hikerapi", flush=True)
            logger.info("step2_keyword_done", keyword_users=len(keyword_items), source="hikerapi")

        if isinstance(step1_recent_result, Exception):
            logger.error("step1_recent_failed", error=str(step1_recent_result))
        else:
            hashtag_recent_items = step1_recent_result
            print(f"[STEP1_RECENT] {len(hashtag_recent_items)} posts from recent hashtag search", flush=True)
            logger.info("step1_recent_done", hashtag_recent_posts=len(hashtag_recent_items))

        if isinstance(step2p5_result, Exception):
            logger.error("step2p5_reels_failed", error=str(step2p5_result))
        else:
            reels_items = step2p5_result
            print(f"[STEP2p5_REELS] {len(reels_items)} creators from reels search", flush=True)
            logger.info("step2p5_reels_done", reels_creators=len(reels_items))

        for item in hashtag_items:
            handle = item.get("username") or item.get("ownerUsername", "")
            if not handle:
                continue
            step1_handles.add(handle)
            if handle in profiles:
                continue
            profiles[handle] = {
                "username": handle,
                "full_name": item.get("full_name", "") or item.get("ownerFullName", ""),
                "fullName": item.get("full_name", "") or item.get("ownerFullName", ""),
                "bio": item.get("bio", "") or item.get("biography", ""),
                "biography": item.get("biography", "") or item.get("bio", ""),
                "avatar_url": item.get("avatar_url") or item.get("profilePicUrl", "") or item.get("displayUrl", ""),
                "profilePicUrl": item.get("profilePicUrl", "") or item.get("avatar_url", ""),
                "follower_count": item.get("follower_count", 0),
                "followersCount": item.get("followersCount", 0),
                "following_count": item.get("following_count", 0),
                "followsCount": item.get("followsCount", 0),
                "posts_count": item.get("posts_count", 0),
                "postsCount": item.get("postsCount", 0),
                "is_business": item.get("is_business", False),
                "isBusinessAccount": item.get("isBusinessAccount", False),
                "is_verified": item.get("is_verified", False),
                "verified": item.get("verified", False),
                "locationName": item.get("locationName", "") or "",
                "location": item.get("locationName", "") or "",
                "pk": item.get("pk"),
                "is_private": item.get("is_private", False),
            }

        for item in keyword_items:
            handle = item.get("username", "")
            if not handle:
                continue
            step2_handles.add(handle)
            if handle in profiles:
                continue
            profiles[handle] = {
                "username": handle,
                "full_name": item.get("full_name", ""),
                "fullName": item.get("full_name", ""),
                "bio": item.get("bio", ""),
                "biography": item.get("biography", ""),
                "avatar_url": item.get("avatar_url", "") or item.get("profilePicUrl", ""),
                "profilePicUrl": item.get("profilePicUrl", "") or item.get("avatar_url", ""),
                "follower_count": item.get("follower_count", 0),
                "followersCount": item.get("followersCount", 0),
                "following_count": item.get("following_count", 0),
                "followsCount": item.get("followsCount", 0),
                "posts_count": item.get("posts_count", 0),
                "postsCount": item.get("postsCount", 0),
                "is_business": item.get("is_business", False),
                "isBusinessAccount": item.get("isBusinessAccount", False),
                "is_verified": item.get("is_verified", False),
                "verified": item.get("verified", False),
                "pk": item.get("pk"),
                "is_private": item.get("is_private", False),
            }

        step3_result, step4_result = await asyncio.gather(
            _fetch_step3(),
            _fetch_step4(),
            return_exceptions=True,
        )
        for res in (step3_result, step4_result):
            if isinstance(res, SourceUnavailable):
                raise res
            if isinstance(res, ReplayMiss):
                _replay_miss_count_for_run += 1

        if isinstance(step3_result, Exception):
            logger.error("step3_topsearch_failed", error=str(step3_result))
        else:
            topsearch_items = step3_result
            print(f"[STEP3] {len(topsearch_items)} accounts from topsearch", flush=True)
            logger.info("step3_topsearch_done", topsearch_accounts=len(topsearch_items))

        if isinstance(step4_result, Exception):
            logger.error("step4_suggested_failed", error=str(step4_result))
        else:
            suggested_items = step4_result
            print(f"[STEP4] {len(suggested_items)} accounts from suggested", flush=True)
            logger.info("step4_suggested_done", suggested_accounts=len(suggested_items))

        for item in topsearch_items:
            handle = item.get("username", "")
            if not handle:
                continue
            step3_handles.add(handle)
            if handle in profiles:
                continue
            profiles[handle] = {
                "username": handle,
                "full_name": item.get("full_name", ""),
                "fullName": item.get("full_name", ""),
                "bio": item.get("bio", ""),
                "biography": item.get("biography", ""),
                "avatar_url": item.get("avatar_url", "") or item.get("profilePicUrl", ""),
                "profilePicUrl": item.get("profilePicUrl", "") or item.get("avatar_url", ""),
                "follower_count": item.get("follower_count", 0),
                "followersCount": item.get("followersCount", 0),
                "following_count": item.get("following_count", 0),
                "followsCount": item.get("followsCount", 0),
                "posts_count": item.get("posts_count", 0),
                "postsCount": item.get("postsCount", 0),
                "is_business": item.get("is_business", False),
                "isBusinessAccount": item.get("isBusinessAccount", False),
                "is_verified": item.get("is_verified", False),
                "verified": item.get("verified", False),
                "pk": item.get("pk"),
                "locationName": item.get("locationName", "") or "",
            }

        for item in suggested_items:
            handle = item.get("username", "")
            if not handle:
                continue
            step4_handles.add(handle)
            if handle in profiles:
                continue
            profiles[handle] = {
                "username": handle,
                "full_name": item.get("full_name", ""),
                "fullName": item.get("full_name", ""),
                "bio": item.get("bio", ""),
                "biography": item.get("biography", ""),
                "avatar_url": item.get("avatar_url", "") or item.get("profilePicUrl", ""),
                "profilePicUrl": item.get("profilePicUrl", "") or item.get("avatar_url", ""),
                "follower_count": item.get("follower_count", 0),
                "followersCount": item.get("followersCount", 0),
                "following_count": item.get("following_count", 0),
                "followsCount": item.get("followsCount", 0),
                "posts_count": item.get("posts_count", 0),
                "postsCount": item.get("postsCount", 0),
                "is_business": item.get("is_business", False),
                "isBusinessAccount": item.get("isBusinessAccount", False),
                "is_verified": item.get("is_verified", False),
                "verified": item.get("verified", False),
                "pk": item.get("pk"),
                "locationName": item.get("locationName", "") or "",
            }

        for item in hashtag_recent_items:
            handle = item.get("username", "") or item.get("ownerUsername", "")
            if not handle:
                continue
            step1_handles.add(handle)
            if handle in profiles:
                continue
            profiles[handle] = {
                "username": handle,
                "full_name": item.get("full_name", "") or item.get("ownerFullName", ""),
                "fullName": item.get("full_name", "") or item.get("ownerFullName", ""),
                "bio": item.get("bio", "") or item.get("biography", ""),
                "biography": item.get("biography", "") or item.get("bio", ""),
                "avatar_url": item.get("avatar_url") or item.get("profilePicUrl", "") or item.get("displayUrl", ""),
                "profilePicUrl": item.get("profilePicUrl", "") or item.get("avatar_url", ""),
                "follower_count": item.get("follower_count", 0),
                "followersCount": item.get("followersCount", 0),
                "following_count": item.get("following_count", 0),
                "followsCount": item.get("followsCount", 0),
                "posts_count": item.get("posts_count", 0),
                "postsCount": item.get("postsCount", 0),
                "is_business": item.get("is_business", False),
                "isBusinessAccount": item.get("isBusinessAccount", False),
                "is_verified": item.get("is_verified", False),
                "verified": item.get("verified", False),
                "locationName": item.get("locationName", "") or "",
                "location": item.get("locationName", "") or "",
                "pk": item.get("pk"),
            }

        for item in reels_items:
            handle = item.get("username", "")
            if not handle:
                continue
            step2_handles.add(handle)
            if handle in profiles:
                continue
            profiles[handle] = {
                "username": handle,
                "full_name": item.get("full_name", ""),
                "fullName": item.get("full_name", ""),
                "bio": item.get("bio", ""),
                "biography": item.get("biography", ""),
                "avatar_url": item.get("avatar_url", "") or item.get("profilePicUrl", ""),
                "profilePicUrl": item.get("profilePicUrl", "") or item.get("avatar_url", ""),
                "follower_count": item.get("follower_count", 0),
                "followersCount": item.get("followersCount", 0),
                "following_count": item.get("following_count", 0),
                "followsCount": item.get("followsCount", 0),
                "posts_count": item.get("posts_count", 0),
                "postsCount": item.get("postsCount", 0),
                "is_business": item.get("is_business", False),
                "isBusinessAccount": item.get("isBusinessAccount", False),
                "is_verified": item.get("is_verified", False),
                "verified": item.get("verified", False),
                "pk": item.get("pk"),
                "locationName": item.get("locationName", "") or "",
            }

        unique_handles = list(profiles.keys())
        print(f"[DIAG] steps 1-5 complete: hashtag_items={len(hashtag_items)}, hashtag_recent={len(hashtag_recent_items)}, keyword_items={len(keyword_items)}, reels_items={len(reels_items)}, topsearch={len(topsearch_items)}, suggested={len(suggested_items)}, unique_handles={len(unique_handles)}", flush=True)
        logger.info("steps_1_to_5_done", unique_profiles=len(unique_handles), hashtag_posts=len(hashtag_items), hashtag_recent=len(hashtag_recent_items), keyword_users=len(keyword_items), reels_creators=len(reels_items), topsearch_accounts=len(topsearch_items), suggested_accounts=len(suggested_items))

        await _save_progress_message(
            run_id,
            f"✅ Encontré {len(unique_handles)} perfiles candidatos (hashtags={len(hashtag_items)}, recent={len(hashtag_recent_items)}, keywords={len(keyword_items)}, reels={len(reels_items)}). "
            f"Filtrando tiendas y cuentas sin seguidores suficientes...",
        )

        await _run_update_metadata(run_id, {
            "completed_steps": ["step1_hashtag_search", "step1_recent_hashtag_search", "step2_keyword_search", "step2p5_reels_search"],
            "total_unique_handles": len(unique_handles),
            "current_step": "step3_profile_enrichment",
        })

        print("[discovery_run_task] STEP 3: Profile enrichment", flush=True)

        async def _prefilter_profiles(
            profiles: dict[str, dict],
            geo_indicators: list[str],
            niche_keywords: list[str],
            top_n: int,
            elite_data: dict[str, Any] | None = None,
        ) -> list[tuple[str, float]]:
            from discovery.scoring.niche import niche_relevance
            from discovery.tools.geo_boost import geo_score

            niche_benchmarks: dict[str, Any] = {}
            if elite_data and isinstance(elite_data, dict):
                _anti_bot_signals = elite_data.get("anti_bot_signals", [])
                niche_benchmarks = elite_data.get("niche_benchmarks", {})

            min_followers = niche_benchmarks.get("min_followers", plan.min_followers) if niche_benchmarks else plan.min_followers
            effective_top_n = min(top_n, niche_benchmarks.get("max_handles_to_enrich", top_n) if niche_benchmarks else top_n)

            scored: list[tuple[str, float]] = []
            bot_flags: dict[str, int] = {}
            for handle, p in profiles.items():
                followers = p.get("followersCount") or p.get("follower_count") or 0
                following = p.get("followsCount") or p.get("following_count") or 0
                posts_count = p.get("postsCount") or p.get("posts_count") or 0

                if followers > 0:
                    if followers < min_followers:
                        bot_flags[handle] = bot_flags.get(handle, 0) + 1

                    ff_ratio = following / followers if following > 0 else 0
                    if ff_ratio > 10 and followers < 5000:
                        bot_flags[handle] = bot_flags.get(handle, 0) + 2
                    if ff_ratio > 20:
                        bot_flags[handle] = bot_flags.get(handle, 0) + 3

                    if posts_count < 10 and followers > 5000:
                        bot_flags[handle] = bot_flags.get(handle, 0) + 1

                bio = p.get("biography") or p.get("bio") or ""
                geo = geo_score(
                    {"biography": bio, "country": "", "username": handle, "full_name": p.get("full_name", ""), "locationName": p.get("locationName", "")},
                    geo_indicators,
                    target_country=brief.audience_countries[0] if brief.audience_countries else None,
                )
                niche = niche_relevance(
                    {"biography": bio, "username": handle, "full_name": p.get("full_name", "")},
                    {"niche_keywords": niche_keywords, "hashtags": [], "keywords": niche_keywords},
                )
                rough = 0.5 * geo + 0.5 * niche

                bot_penalty = bot_flags.get(handle, 0)
                if bot_penalty >= 3:
                    rough *= 0.3
                elif bot_penalty >= 2:
                    rough *= 0.6
                elif bot_penalty >= 1:
                    rough *= 0.85

                is_business = p.get("isBusinessAccount") or p.get("is_business")
                bio_lower = bio.lower()

                commerce_keyword_groups = profile_data.get(
                    "commerce_signal_keywords", DEFAULT_COMMERCE_SIGNAL_KEYWORDS
                )
                commerce_signals = sum(
                    any(kw in bio_lower for kw in group)
                    for group in commerce_keyword_groups
                )

                creator_keyword_groups = profile_data.get(
                    "creator_signal_keywords", DEFAULT_CREATOR_SIGNAL_KEYWORDS
                )
                creator_signals = sum(
                    any(kw in bio_lower for kw in group)
                    for group in creator_keyword_groups
                )
                if is_business and commerce_signals > 0:
                    rough *= 0.35
                elif commerce_signals >= 3:
                    rough *= 0.5
                elif commerce_signals >= 1:
                    rough *= 0.75
                elif creator_signals >= 2:
                    rough *= 1.3
                elif creator_signals == 1:
                    rough *= 1.15

                scored.append((handle, rough))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:effective_top_n]

        elite_data = profile_data.get("elite_data") if profile_data else None
        prefilter_before = len(unique_handles)
        prefilter_handles = await _prefilter_profiles(
            profiles,
            profile_data.get("geo_indicators", []),
            profile_data.get("niche_keywords", []),
            MAX_HANDLES_TO_ENRICH,
            elite_data,
        )
        handles_to_enrich = [h for h, _ in prefilter_handles]
        logger.info(
            "prefilter_stats",
            run_id=run_id,
            before=prefilter_before,
            after=len(handles_to_enrich),
            top_score=prefilter_handles[0][1] if prefilter_handles else None,
        )

        enriched_profiles: list[dict] = []
        step3_degraded = False
        step3_error: str | None = None
        hikerapi_enrich_semaphore = asyncio.Semaphore(5)

        if handles_to_enrich:
            logger.info(
                "step3_hikerapi_pure_enrichment_start",
                handles_count=len(handles_to_enrich),
            )
            try:
                async def _enrich_one(handle: str) -> dict | None:
                    from discovery.exceptions import BudgetExhausted, SourceUnavailable
                    try:
                        if not await circuit_breaker.can_proceed():
                            raise SourceUnavailable(
                                "Circuit breaker open — HikerAPI degradado.",
                                status_code=503,
                                provider="hikerapi",
                            )
                        if not await budget_fuse.reserve_and_record(run_id, "hikerapi"):
                            raise BudgetExhausted(
                                f"Límite de {settings.MAX_CALLS_PER_RUN} llamadas alcanzado.",
                                current_usd=None,
                                budget_usd=settings.MONTHLY_BUDGET_USD,
                            )
                        async with hikerapi_enrich_semaphore:
                            profile = await instagram_source.enrich_profile(handle)
                        if profile and profile.get("pk") and ENRICHMENT_INCLUDE_ABOUT and hasattr(instagram_source, "get_user_about"):
                            try:
                                about_data = await instagram_source.get_user_about(profile["pk"])
                                if about_data:
                                    profile["about"] = about_data
                            except SourceUnavailable:
                                raise
                            except Exception as e:
                                logger.warning("hikerapi_user_about_error", handle=handle, error=str(e))
                        return profile
                    except SourceUnavailable:
                        raise
                    except Exception as e:
                        logger.warning("hikerapi_enrich_error", handle=handle, error=str(e))
                        return None

                enrichment_results = await asyncio.gather(
                    *[_enrich_one(h) for h in handles_to_enrich],
                    return_exceptions=True,
                )
                for res in enrichment_results:
                    if isinstance(res, SourceUnavailable):
                        raise res
                    if isinstance(res, ReplayMiss):
                        _replay_miss_count_for_run += 1
                enriched_profiles = [
                    p for p in enrichment_results
                    if isinstance(p, dict) and p.get("username")
                ]
                logger.info(
                    "step3_hikerapi_enrichment_done",
                    enriched=len(enriched_profiles),
                    requested=len(handles_to_enrich),
                    with_about_country=sum(1 for p in enriched_profiles if (p.get("about") or {}).get("country")),
                    ve_countries=sum(1 for p in enriched_profiles if (p.get("about") or {}).get("country", "").upper() == "VE"),
                )
            except Exception as e:
                step3_degraded = True
                step3_error = str(e)
                logger.warning("step3_enrichment_failed", error=str(e))

            if not enriched_profiles:
                step3_degraded = True
                step3_error = "HikerAPI enrichment returned empty"
                await _save_progress_message(
                    run_id,
                    "⚠️ No pude enriquecer perfiles vía HikerAPI. Continuando con datos básicos...",
                )
            else:
                await _save_progress_message(
                    run_id,
                    f"✅ Enriquecí {len(enriched_profiles)} perfiles con HikerAPI...",
                )

        for e in enriched_profiles:
            handle = e.get("username", "")
            if not handle or handle not in profiles:
                continue
            about_data = e.get("about")
            profiles[handle].update({
                "follower_count": e.get("followersCount", 0) or 0,
                "followersCount": e.get("followersCount", 0) or 0,
                "following_count": e.get("followsCount", 0) or 0,
                "followsCount": e.get("followsCount", 0) or 0,
                "posts_count": e.get("postsCount", 0) or 0,
                "postsCount": e.get("postsCount", 0) or 0,
                "is_business": e.get("isBusinessAccount", False),
                "isBusinessAccount": e.get("isBusinessAccount", False),
                "is_verified": e.get("verified", False),
                "verified": e.get("verified", False),
                "bio": e.get("biography", profiles[handle].get("bio", "")),
                "biography": e.get("biography", profiles[handle].get("biography", "")),
                "full_name": e.get("fullName", profiles[handle].get("full_name", "")),
                "fullName": e.get("fullName", profiles[handle].get("fullName", "")),
                "avatar_url": e.get("profilePicUrlHD") or e.get("profilePicUrl") or profiles[handle].get("avatar_url", ""),
                "profilePicUrl": e.get("profilePicUrlHD") or e.get("profilePicUrl") or profiles[handle].get("profilePicUrl", ""),
                "country": e.get("country", ""),
                "is_private": e.get("is_private", profiles[handle].get("is_private", False)),
                "locationName": e.get("locationName", profiles[handle].get("locationName", "")),
                "location": e.get("locationName", profiles[handle].get("location", "")),
                "latestPosts": e.get("latestPosts", []),
                "engagement_rate": e.get("engagement_rate"),
            })
            if about_data:
                profiles[handle]["about"] = about_data

        logger.info(
            "step3_enrichment_done",
            enriched=len(enriched_profiles),
            total_profiles=len(profiles),
        )

        # NOTE: Engagement Analytics (easyapi~instagram-profile-engagement-analytics) is disabled
        # The actor returns 404 errors. Engagement rate is already calculated from profile scraper data.
        # if enriched_profiles:
        #     handles_for_analytics = list({e.get("username") for e in enriched_profiles if e.get("username")})
        #     if handles_for_analytics:
        #         try:
        #             analytics_results = await apify_client.analyze_profile_engagement(
        #                 usernames=handles_for_analytics,
        #                 posts_to_analyze=30,
        #                 discovery_run_id=run_id,
        #             )
        #             analytics_map = {r.get("username"): r for r in analytics_results if r.get("username")}
        #             for e in enriched_profiles:
        #                 handle = e.get("username", "")
        #                 if handle in analytics_map:
        #                     e["engagement_analytics"] = analytics_map[handle]
        #             logger.info(
        #                 "step3_engagement_analytics_done",
        #                 profiles_analyzed=len(handles_for_analytics),
        #                 results_received=len(analytics_results),
        #             )
        #         except Exception as exc:
        #             logger.warning("step3_engagement_analytics_failed", run_id=run_id, error=str(exc))

        await _run_update_metadata(run_id, {
            "current_step": "step4_scoring",
            "completed_steps": ["step1_hashtag_search", "step1_recent_hashtag_search", "step2_keyword_search", "step2p5_reels_search", "step3_profile_enrichment"],
        })

        print(f"[discovery_run_task] STEP 4: Scoring {len(profiles)} profiles", flush=True)

        exclude_handles = set(h.lower() for h in (plan.exclude_handles or []))
        if exclude_handles:
            original_count = len(profiles)
            profiles = {k: v for k, v in profiles.items() if k.lower() not in exclude_handles}
            print(f"[discovery_run_task] STEP 4: Excluded {original_count - len(profiles)} handles, scoring {len(profiles)} remaining", flush=True)

        _cross_ref_handles = step1_handles & step2_handles
        hashtag_appearances: dict[str, int] = {}
        for h in step1_handles:
            hashtag_appearances[h] = hashtag_appearances.get(h, 0) + 1
        scored: list[dict] = []
        bots_filtered = 0
        untracked_no_followers = 0
        low_followers_skipped = 0
        geo_country_mismatch = 0
        geo_no_signal = 0
        political_filtered = 0
        geo_passed = 0
        target_country = (brief.audience_countries or ["VE"])[0].upper()
        exclusion_keywords = profile_data.get(
            "exclusion_keywords", DEFAULT_EXCLUSION_KEYWORDS
        )
        for handle, p in profiles.items():
            followers = p.get("followersCount") or p.get("follower_count") or 0
            if followers == 0:
                untracked_no_followers += 1
                continue
            if followers < plan.min_followers:
                low_followers_skipped += 1
                continue
            if followers > TIER_MAX_FOLLOWERS:
                low_followers_skipped += 1
                continue

            latest = p.get("latestPosts") or []
            er = 0.0
            likes_avg = 0.0
            comments_avg = 0.0
            if latest and followers > 0:
                likes_avg = sum((post.get("likesCount") or 0) for post in latest) / max(len(latest), 1)
                comments_avg = sum((post.get("commentsCount") or 0) for post in latest) / max(len(latest), 1)
                er = (likes_avg + comments_avg) / followers

            p["engagement_rate"] = er

            if er > 0.30:
                bots_filtered += 1
                continue
            if er < 0.005 and followers > 5000:
                bots_filtered += 1
                continue

            about = p.get("about") or {}
            about_country = (about.get("country") or "").strip().upper()
            handle_lower = handle.lower().lstrip("@")

            non_ve_handle_tlds = (
                ".rd", ".do", ".mx", ".ar", ".co", ".cl", ".pe",
                ".ec", ".pa", ".uy", ".py", ".bo", ".cr",
                "_rd", "_do", "_mx", "_ar", "_co", "_cl", "_pe",
                "_ec", "_pa", "_uy", "_py", "_bo", "_cr",
                "rd_", "do_", "mx_", "ar_", "co_", "cl_", "pe_",
                "mx_", "ar_", "co_", "pe_", "cl_",
            )
            if any(handle_lower.endswith(tld) for tld in non_ve_handle_tlds):
                geo_country_mismatch += 1
                continue

            if about_country and about_country != target_country:
                geo_country_mismatch += 1
                continue

            non_ve_signals = (
                "españa", "spain", "salamanca", "madrid", "barcelona", "valencia es",
                "dominicana", "santo domingo", "santiago rd",
                "méxico", "colombia", "argentina", "chile", "perú",
                "estados unidos", "usa ", "miami", "nyc", "texas",
                "kenwood españa", "embajador kenwood",
            )
            bio = p.get("biography") or p.get("bio") or ""
            bio_geo = f"{bio.lower()} {handle.lower()} {p.get('full_name', '').lower()}"
            if any(sig in bio_geo for sig in non_ve_signals):
                geo_country_mismatch += 1
                continue

            geo_indicators = profile_data.get("geo_indicators", [])
            geo = geo_score(p, geo_indicators, target_country=brief.audience_countries[0] if brief.audience_countries else None) if geo_indicators else 0.5
            if about_country == "VE":
                geo = max(geo, 0.85)
            if geo_indicators and geo < 0.4 and not has_hard_geo_signal(p, target_country):
                geo_no_signal += 1
                continue

            bio_or_username = f"{bio.lower()} {handle.lower()}"
            if any(kw in bio_or_username for kw in exclusion_keywords):
                political_filtered += 1
                continue

            geo_passed += 1
            cross_referenced = hashtag_appearances.get(handle, 0) >= 2
            score_val = lens_score(
                p, profile_data,
                cross_referenced=cross_referenced,
                target_country=brief.audience_countries[0] if brief.audience_countries else None,
            )

            former_usernames_count = about.get("former_usernames_count", 0) or 0
            account_age_days = about.get("account_age_days", 0) or 0
            fraud_penalty = 1.0
            if former_usernames_count >= 3:
                fraud_penalty = 0.80
            elif former_usernames_count == 2 or account_age_days > 0 and account_age_days < 90:
                fraud_penalty = 0.90
            if fraud_penalty < 1.0:
                score_val = round(score_val * fraud_penalty, 1)
                logger.debug("fraud_penalty_applied", handle=handle, former_usernames=former_usernames_count, account_age_days=account_age_days, penalty=fraud_penalty, original_score=score_val / fraud_penalty, final_score=score_val)

            tier = classify_tier(followers)
            real_niche = niche_relevance(p, profile_data)
            tienda_keywords_hard = (
                "tienda", "shop", "store", "petshop", "pet shop", "pets shop",
                "ventas", "vendemos", "pedidos", "envíos", "delivery", "deliveries",
                "catálogo", "catalogo", "precios", "oferta", "descuento", "promoción",
                "comprar", "compras", "adquirir", "adquisición",
                "whatsapp", "escríbenos", "contáctanos", "contaco", "telf", "teléfono", "telefono",
                "horario", "horarios", "sucursal", "sucursales", "local", "tienda física",
                "envíos a todo el país", "envios a todo el pais",
                "pago en dólares", "pago en euros", "transferencia", "zelle", "paypal",
                "marca oficial", "distribuidor", "distribuidora", "agente autorizado",
                "mayor y detal", "menudeo", "por mayor", "al mayor",
                "stock", "inventario", "bodega", "almacén", "almacen",
                "mascotienda", "petstore", "pet.store", "petstore.ve", "pet world",
                "vetstore", "veterinaria store", "tienda veterinaria",
                "cachorro en venta", "cachorros en venta", "venta de cachorros",
                "criadero", "cria", "cría", "breeder", "kennel",
                "cápsulas", "capsulas", "granos", "molido", "seleccionamos a mano",
                "selección a mano", "nuestro café", "nuestra marca",
                "cursos online", "curso de repostería", "clases de cocina", "aprende repostería",
                "haz click aquí", "link en bio", "clic abajo enlace", "contáctanos al",
                "embajador kenwood", "embajador officiel",
                "nuestra marca", "fabricamos", "elaboramos", "producimos",
                "nuestra tienda", "punto de venta", "pdv",
                "delivery propio", "envío gratis", "envío a domicilio",
                "productos artesanales", "artesanal",
                "panadería profesional", "pastelería profesional",
            )
            username_lower = handle.lower()
            is_tienda = any(kw in bio.lower() for kw in tienda_keywords_hard)
            if not is_tienda:
                tienda_username_patterns = (
                    "shop", "store", "tienda", "petshop", "pet_", "pet-",
                    "ve_shop", "ve.store", "_ve_", "vzla_shop", ".ve",
                    "petworld", "petplanet", "petlife", "petlovers",
                    "mascotienda", "petland", "petsclub",
                )
                is_tienda = any(p in username_lower for p in tienda_username_patterns)
            country_val = p.get("country") or (profile_data.get("countries", [""])[0] if profile_data.get("countries") else "")
            is_verified = bool(p.get("verified") or p.get("is_verified"))
            is_business = bool(p.get("isBusinessAccount") or p.get("is_business"))
            credibility = (20 if is_business else 0) + (20 if is_verified else 0)
            creator_signals = sum(1 for kw in (
                "creador", "content creator", "reviewer", "vlogger",
                "youtuber", "tiktoker", "streamer", "entrenador",
                "coach", "atleta", "deportista", "fitness",
                "influencer", "blogger", "periodista", "presentador",
                "comunicador", "actor", "cantante", "músico", "artista",
                "creativo", "emprendedor", "diseñador", "fotógrafo",
                "veterinario", "veterinaria", "vet", "médico animal",
                "pet photographer", "dog photographer", "fotógrafo canino",
                "adiestrador", "adiestramiento", "dog trainer", "canine trainer",
                "peluquero canino", "groomer", "pet groomer", "dog groomer",
                "refugio", "rescate", "rescatista", "animal rescue",
                "refugio animal", "adopción", "adopcion responsable",
                "dog mom", "dog dad", "pet parent", "pet mom", "pet dad",
                "golden retriever", "labrador", "husky", "pastor alemán",
                "beagle", "bulldog", "poodle", "dálmata", "dalmata",
                "cachorro", "cachorros", "cachorritos", "puppy", "puppies",
                "kanine", "canine", "dog", "dogs", "pet", "pets",
            ) if kw in bio.lower())
            is_creator = creator_signals > 0 and not is_tienda and not is_business
            if is_creator:
                score_val = score_val * 1.15
            elif is_tienda:
                score_val = score_val * 0.7
            scored.append({
                "run_id": run_id,
                "platform": "instagram",
                "handle": handle,
                "full_name": p.get("fullName") or p.get("full_name"),
                "bio": bio,
                "avatar_url": p.get("profilePicUrlHD") or p.get("profilePicUrl") or p.get("avatar_url") or (f"https://instagram.com/{handle}/profile_picture" if handle else ""),
                "country": country_val,
                "city": p.get("locationName") or p.get("location") or "",
                "followers": followers,
                "following": p.get("followsCount") or p.get("following_count") or 0,
                "posts_count": p.get("postsCount") or p.get("posts_count") or 0,
                "avg_likes": round(likes_avg) if latest else None,
                "avg_comments": round(comments_avg) if latest else None,
                "avg_views": None,
                "engagement_rate": round(er, 6),
                "audience_credibility": credibility,
                "audience_quality": 50,
                "audience_gender_split": {},
                "audience_age_buckets": {},
                "match_score": round(score_val, 2),
                "niche_relevance": round(real_niche * 100, 2),
                "geo_relevance": round(geo * 100, 1),
                "audience_relevance": None,
                "content_quality": None,
                "expected_reach": int(followers * 0.7),
                "expected_engagement": int(followers * er),
                "roi_estimate": None,
                "rationale": build_rationale(p, tier, followers, er, target_country=target_country),
                "tier": tier,
                "is_tienda": is_tienda,
                "status": "new",
                "raw_payload": {
                    "lens_score": round(score_val, 2),
                    "tier": tier,
                    "er_calculated": round(er, 6),
                    "geo_score": geo,
                    "cross_referenced": cross_referenced,
                    "is_verified": is_verified,
                    "is_business": is_business,
                    "is_creator": is_creator,
                    "creator_signals": creator_signals,
                    "hd_profile_pic_url": p.get("hdProfilePicUrl") or p.get("profilePicUrlHD"),
                    "avg_likes_calc": round(likes_avg) if latest else None,
                    "avg_comments_calc": round(comments_avg) if latest else None,
                    "posts_analyzed": len(latest) if latest else 0,
                    "engagement_analytics": p.get("engagement_analytics"),
                    "fraud_signals": {
                        "former_usernames_count": former_usernames_count,
                        "account_age_days": account_age_days,
                        "fraud_penalty": fraud_penalty,
                    },
                },
                "fetched_at": datetime.now(UTC),
            })

        scored.sort(key=lambda c: c.get("match_score") or 0, reverse=True)

        score_distribution = {
            "total_scored": len(scored),
            "scores_above_50": sum(1 for c in scored if (c.get("match_score") or 0) >= 50),
            "scores_35_to_50": sum(1 for c in scored if 35 <= (c.get("match_score") or 0) < 50),
            "scores_25_to_35": sum(1 for c in scored if 25 <= (c.get("match_score") or 0) < 35),
            "scores_below_25": sum(1 for c in scored if (c.get("match_score") or 0) < 25),
        }
        top_5 = scored[:5]
        top_5_summary = [
            {
                "handle": c.get("handle"),
                "match_score": c.get("match_score"),
                "geo": c.get("geo_relevance"),
                "niche": c.get("niche_relevance"),
                "er": c.get("engagement_rate"),
                "followers": c.get("followers"),
                "is_tienda": c.get("is_tienda"),
            }
            for c in top_5
        ]
        logger.info(
            "scoring_diagnostic",
            run_id=run_id,
            distribution=score_distribution,
            skipped={
                "untracked_no_followers": untracked_no_followers,
                "low_followers_skipped": low_followers_skipped,
                "bots_filtered": bots_filtered,
                "geo_country_mismatch": geo_country_mismatch,
                "geo_no_signal": geo_no_signal,
                "political_filtered": political_filtered,
                "geo_passed": geo_passed,
            },
            top_5=top_5_summary,
        )

        min_match_score = 5
        exclude_stores = getattr(brief, "exclude_stores", True)

        passed_score = [c for c in scored if (c.get("match_score") or 0) >= min_match_score]
        passed_store = [c for c in passed_score if not c.get("is_tienda")]
        qualified = [c for c in passed_score if (not exclude_stores or not c.get("is_tienda"))]

        logger.info(
            "scoring_filter_breakdown",
            run_id=run_id,
            total_scored=len(scored),
            passed_score_min=len(passed_score),
            passed_tienda_filter=len(passed_store),
            qualified_final=len(qualified),
            exclude_stores=exclude_stores,
            min_match_score=min_match_score,
        )
        print(f"[SCORING] {len(scored)} scored → {len(passed_score)} score≥{min_match_score} → {len(qualified)} qualified (tienda_excluded={exclude_stores})", flush=True)

        target_n = 80
        to_analyze = _rerank_diversified(qualified, target_n)

        analyze_with_ai = getattr(brief, "analyze_with_ai", True)
        if analyze_with_ai:
            print(f"[discovery_run_task] STEP 5: AI analysis with DeepSeek ({len(to_analyze)} candidates)", flush=True)
            tracker = get_discovery_cost_tracker()

            def record_deepseek_cost(cost_usd: float, tokens_in: int, tokens_out: int) -> None:
                tracker.record_deepseek_cost(
                    run_id=run_id,
                    cost_usd=cost_usd,
                    tokens_input=tokens_in,
                    tokens_output=tokens_out,
                    operation="candidate_analysis",
                    metadata={"candidates_count": len(to_analyze)},
                )

            analyzed = await candidate_analyzer.analyze_candidates_batch(
                candidates=to_analyze,
                brief=brief,
                profile_data=profile_data,
                cost_callback=record_deepseek_cost,
            )
            for candidate in analyzed:
                if candidate.get("ai_rationale"):
                    candidate["rationale"] = candidate["ai_rationale"]
        else:
            print("[discovery_run_task] STEP 5: Skipping AI analysis (analyze_with_ai=False), using rule-based scores", flush=True)
            analyzed = to_analyze

        await _run_update_metadata(run_id, {
            "current_step": "step5_ai_analysis",
            "completed_steps": [
                "step1_hashtag_search",
                "step1_recent_hashtag_search",
                "step2_keyword_search",
                "step2p5_reels_search",
                "step3_profile_enrichment",
                "step4_scoring",
            ],
        })

        qualified = analyzed

        logger.info(
            "scoring_done",
            total_profiles=len(profiles),
            ve_candidates=len(scored),
            qualified=len(qualified),
            tiendas_filtered=len(scored) - len([c for c in scored if not c.get("is_tienda")]),
            bots_filtered=bots_filtered,
            top_score=qualified[0].get("match_score") if qualified else None,
        )

        if len(qualified) == 0:
            logger.warning(
                "discovery_run_no_qualified_candidates",
                run_id=run_id,
                profiles_scored=len(profiles),
                ve_candidates=len(scored),
            )
            await _save_progress_message(
                run_id,
                "⚠️ Esta vez no encontré candidatos que califiquen. "
                "Probemos con hashtags más específicos o ajustes al brief...",
            )
        else:
            await _save_progress_message(
                run_id,
                f"✅ Listo. {len(qualified)} creadores calificados para tu campaña. "
                f"El mejor candidato tiene {qualified[0].get('match_score', 0):.0f}/100 de match.",
            )

        inserted_count = await _deduplicate_and_insert_candidates(qualified, run_id)
        total = inserted_count

        print(f"[discovery_run_task] DONE run_id={run_id} total_candidates={total}", flush=True)
        final_status = "partial" if step3_degraded else "completed"
        await _run_update(run_id, {
            "status": final_status,
            "total_candidates": total,
            "completed_at": datetime.now(UTC),
        })
        await _run_update_metadata(run_id, {
            "current_step": "completed",
            "candidates_found": total,
            "completed_at": datetime.now(UTC).isoformat(),
            "step3_degraded": step3_degraded,
            "step3_error": step3_error,
            "replay_miss_count": _replay_miss_count_for_run,
        })

        conv = await railway_pg.select_one(
            table="discovery_conversations",
            select="id",
            filters=[f"discovery_run_id=eq.{run_id}"],
        )
        if conv:
            from uuid import UUID as pyUUID

            from discovery.memory import conversation_memory
            top_candidates = qualified[:10]
            summary_lines = [
                f"- **{c['handle']}** ({c['platform']}): "
                f"Score {c.get('match_score', 0):.0f}/100, "
                f"{c.get('followers', 0):,} seguidores, "
                f"ER {c.get('engagement_rate', 0):.1%}"
                for c in top_candidates
            ]
            if total == 0:
                content = (
                    f"Escaneé {len(profiles)} perfiles y {len(scored)} pasaron el filtro geográfico, "
                    f"pero ninguno califica en nicho o calidad (las tiendas y perfiles genéricos fueron filtrados). "
                    f"Intenta con hashtags más específicos de tu nicho o ajusta el brief."
                )
            else:
                content = (
                    f"Terminé la búsqueda con pipeline de 4 capas. "
                    f"Encontré {total} candidatos para tu brief.\n\n"
                    + ("Aquí están los más relevantes:\n" + "\n".join(summary_lines) + "\n\n"
                    if summary_lines else "")
                    + "Puedes ver todos en la lista de candidatos."
                )
            await conversation_memory.save_message(
                conversation_id=pyUUID(conv["id"]),
                role="assistant",
                content=content,
            )
            await conversation_memory.update_conversation(
                conversation_id=pyUUID(conv["id"]),
                updates={"current_step": "candidates_review"},
            )

        logger.info("discovery_run_completed", run_id=run_id, candidates=total)

        tracker = get_discovery_cost_tracker()

        cost_summary = tracker.get_run_summary(run_id)
        total_cost = cost_summary["total_usd"]

        await railway_pg.update(
            table="discovery_runs",
            values={"actual_cost_usd": total_cost},
            filters=[f"id=eq.{run_id}"],
        )
        await tracker.flush(run_id)
        await budget_fuse.reset_run_counter(run_id)

        lens_active_runs.dec()
        lens_candidates_total.labels(status="inserted").inc(total)
        return {"run_id": run_id, "candidates": total}

    except SourceUnavailable as e:
        logger.error(
            "discovery_run_source_unavailable",
            run_id=run_id,
            provider=e.provider,
            status_code=e.status_code,
            error=e.message,
        )
        error_msg = (
            f"Fuente de datos no disponible ({e.provider}, HTTP {e.status_code}): {e.message}. "
            "Revisa: hikerapi.com/billing"
        )
        await _run_set_status(run_id, "failed", error=error_msg)
        try:
            await _save_progress_message(
                run_id,
                f"🔴 La búsqueda falló por un problema con HikerAPI: HTTP {e.status_code}. "
                f"Detalles: {e.message}. "
                f"Recarga créditos en hikerapi.com/billing y vuelve a intentarlo.",
            )
        except Exception:
            pass
        try:
            tracker = get_discovery_cost_tracker()
            await tracker.flush(run_id)
        except Exception:
            pass
        await budget_fuse.reset_run_counter(run_id)
        lens_active_runs.dec()
        return {"run_id": run_id, "error": error_msg, "candidates": 0}

    except ReplayMiss as e:
        _replay_miss_count_for_run += 1
        logger.warning("discovery_replay_miss", run_id=run_id, endpoint=e.endpoint, count=_replay_miss_count_for_run)
        await _run_update_metadata(run_id, {"replay_miss_count": _replay_miss_count_for_run})
        await _run_set_status(run_id, "partial", error=f"Replay miss: {e.message} (+{_replay_miss_count_for_run - 1} more silent)")
        await budget_fuse.reset_run_counter(run_id)
        lens_active_runs.dec()
        return {"run_id": run_id, "candidates": 0}

    except Exception as e:
        logger.error("discovery_run_failed", run_id=run_id, error=str(e), exc_info=True)
        await _run_set_status(run_id, "failed", error=str(e))
        try:
            tracker = get_discovery_cost_tracker()
            await tracker.flush(run_id)
        except Exception:
            pass
        await budget_fuse.reset_run_counter(run_id)
        lens_active_runs.dec()
        raise


async def _execute_platform_query(platform: Platform, query, run_progress: dict | None = None) -> list[dict]:
    """Deprecated: platform-specific queries now go through HikerAPI via discovery_run_task.

    This function is kept as a stub to avoid breaking any external callers.
    Raises NotImplementedError if called.
    """
    raise NotImplementedError(
        "Platform-specific query execution via this path is deprecated. "
        "All discovery now routes through HikerAPI in discovery_run_task."
    )


def _raw_to_candidate_dict(raw: dict, platform: Platform) -> dict:
    """Convierte payload raw a dict compatible con discovery_candidates.

    Maneja tres formatos de Instagram:
    - Enriched data (profile scraper + post engagement): _from_profile=True, tiene followersCount + likesCount
    - Profile data (de profile scraper): username, followersCount, biography
    - Post data (de hashtag scraper): ownerUsername, likesCount, commentsCount
    """
    if platform == Platform.INSTAGRAM:
        from_profile = raw.get("_from_profile", False)
        has_followers = "followersCount" in raw and raw.get("followersCount")

        if from_profile or has_followers:
            followers = raw.get("followersCount", 0) or 0
            following = raw.get("followsCount", 0) or 0
            posts_count = raw.get("postsCount", 0) or 0
            verified = raw.get("isVerified", False) or raw.get("verified", False)
            business = raw.get("isBusinessAccount", False)

            credibility = 50
            if verified:
                credibility += 20
            if business:
                credibility += 15
            credibility = min(credibility, 100)

            likes = raw.get("likesCount", 0) or 0
            comments = raw.get("commentsCount", 0) or 0
            engagement_rate = 0.0
            if likes > 0 and followers > 0:
                engagement_rate = round((likes + comments) / max(followers, 1), 6)
            elif posts_count > 0:
                engagement_rate = round((likes + comments) / max(posts_count, 1), 6)

            country = ""
            about = raw.get("about", {})
            if about:
                country = about.get("country", "") or ""
            elif raw.get("country"):
                country = raw.get("country", "")

            return {
                "platform": platform.value,
                "platform_user_id": str(raw.get("userId", raw.get("id", ""))),
                "handle": raw.get("username", raw.get("ownerUsername", "")),
                "full_name": raw.get("fullName", raw.get("ownerFullName", "")),
                "bio": raw.get("biography", raw.get("caption", "")),
                "avatar_url": raw.get("profilePicUrlHD") or raw.get("profilePicUrl") or raw.get("displayUrl", ""),
                "followers": followers,
                "following": following,
                "posts_count": posts_count,
                "avg_likes": likes or None,
                "avg_comments": comments or None,
                "engagement_rate": engagement_rate or None,
                "country": country,
                "city": "",
                "url": f"https://instagram.com/{raw.get('username', raw.get('ownerUsername', ''))}",
                "audience_gender_split": {},
                "audience_age_buckets": {},
                "audience_credibility": credibility,
                "audience_quality": 50,
                "raw_payload": raw,
            }
        else:
            likes = raw.get("likesCount", 0) or 0
            comments = raw.get("commentsCount", 0) or 0
            posts_count_raw = raw.get("postsCount", 0) or 0
            engagement_rate = 0.0
            if likes > 0 and posts_count_raw > 0:
                engagement_rate = round((likes + comments) / max(posts_count_raw, 1), 6)

            return {
                "platform": platform.value,
                "platform_user_id": str(raw.get("ownerId", "")),
                "handle": raw.get("ownerUsername", ""),
                "full_name": raw.get("ownerFullName", ""),
                "bio": raw.get("caption", ""),
                "avatar_url": raw.get("profilePicUrlHD") or raw.get("profilePicUrl") or raw.get("displayUrl", ""),
                "followers": 0,
                "following": 0,
                "posts_count": 0,
                "avg_likes": likes,
                "avg_comments": comments,
                "engagement_rate": engagement_rate,
                "country": "",
                "city": "",
                "url": raw.get("url", f"https://instagram.com/{raw.get('ownerUsername', '')}"),
                "audience_gender_split": {},
                "audience_age_buckets": {},
                "audience_credibility": 50,
                "audience_quality": 50,
                "raw_payload": raw,
            }
    elif platform == Platform.TIKTOK:
        author = raw.get("author", {})
        stats = raw.get("stats", {})
        return {
            "handle": author.get("uniqueId", raw.get("handle", "")),
            "full_name": author.get("nickname", ""),
            "followers": stats.get("followerCount", 0),
            "posts_count": stats.get("videoCount", 0),
            "avg_views": raw.get("videoView", 0),
            "engagement_rate": 0.05,
            "country": raw.get("region", "VE"),
            "url": raw.get("shareUrl", ""),
        }
    elif platform == Platform.YOUTUBE:
        snippet = raw.get("snippet", {})
        stats = raw.get("channel_details", {}).get("statistics", {})
        return {
            "handle": snippet.get("channelTitle", ""),
            "full_name": snippet.get("channelTitle", ""),
            "bio": snippet.get("description", ""),
            "avatar_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "followers": int(stats.get("subscriberCount", 0)),
            "posts_count": int(stats.get("videoCount", 0)),
            "engagement_rate": 0.02,
            "url": f"https://youtube.com/channel/{raw.get('id', '')}",
        }
    return {"handle": "unknown"}


async def _deduplicate_and_insert_candidates(candidates: list[dict], run_id: str) -> int:
    """Inserta candidatos en lote. Fallback individual si el lote falla.
    Returns the number of successfully inserted candidates."""
    import uuid as _uuid

    for c in candidates:
        if "id" not in c or c.get("id") is None:
            c["id"] = str(_uuid.uuid4())

    inserted = 0
    failed = 0

    try:
        result = await railway_pg.upsert_many(
            table="discovery_candidates",
            records=candidates,
            on_conflict=["run_id", "platform", "handle"],
            returning="minimal",
        )
        inserted = len(result)
        logger.info(
            "candidates_insert_summary",
            run_id=run_id,
            attempted=len(candidates),
            inserted=inserted,
            failed=0,
            batch=True,
        )
    except Exception as batch_exc:
        logger.warning(
            "candidate_batch_insert_failed_falling_back_to_individual",
            run_id=run_id,
            error=str(batch_exc),
        )
        for c in candidates:
            try:
                await railway_pg.insert(
                    table="discovery_candidates",
                    values=c,
                    returning="minimal",
                )
                inserted += 1
            except Exception as exc:
                failed += 1
                logger.error(
                    "candidate_insert_failed",
                    run_id=run_id,
                    handle=c.get("handle"),
                    platform=c.get("platform"),
                    error=str(exc),
                    exc_info=True,
                )
        logger.info(
            "candidates_insert_summary",
            run_id=run_id,
            attempted=len(candidates),
            inserted=inserted,
            failed=failed,
            batch=False,
        )
    return inserted


async def _run_set_status(run_id: str, status: str, error: str | None = None) -> None:
    values = {"status": status, "started_at": datetime.now(UTC)}
    if error:
        values["error"] = error
    await railway_pg.update(
        table="discovery_runs",
        filters=[f"id=eq.{run_id}"],
        values=values,
    )


async def _run_update(run_id: str, values: dict) -> None:
    await railway_pg.update(
        table="discovery_runs",
        filters=[f"id=eq.{run_id}"],
        values=values,
    )


async def _run_update_metadata(run_id: str, metadata: dict) -> None:
    """Atomic metadata update using PostgreSQL JSONB merge operator."""
    try:
        await railway_pg.rpc(
            "discovery_runs_merge_metadata",
            {"p_run_id": run_id, "p_metadata": metadata},
        )
    except Exception as e:
        logger.warning(
            f"[run {run_id}] metadata update skipped: {e}"
        )


# ---- Existing tasks ----

async def sync_hypeauditor_task(ctx, influencer_id: str) -> dict:
    """Pull fresh metrics from Hypeauditor for an influencer."""
    logger.info("sync_hypeauditor_task", influencer_id=influencer_id)

    if not settings.HYPEAUDITOR_API_KEY:
        return {"error": "HYPEAUDITOR_API_KEY not configured"}

    influencer = await railway_pg.select_one(
        table="influencers",
        select="id,full_name,primary_handle",
        filters=[f"id=eq.{influencer_id}"],
    )

    if not influencer:
        return {"error": "Influencer not found"}

    return {"influencer_id": influencer_id, "synced": False, "reason": "HypeAuditor not implemented"}


async def sync_metricool_task(ctx, channel: str = "instagram") -> dict:
    """Sincroniza métricas desde Metricool para un canal."""
    logger.info("sync_metricool_task", channel=channel)

    if not settings.METRICOOL_ACCESS_TOKEN:
        return {"synced": 0, "reason": "METRICOOL_ACCESS_TOKEN not configured"}

    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=30)
        analytics = await metricool_client.get_analytics(
            channel=channel,
            start_date=start_date,
            end_date=end_date,
        )
        return {"channel": channel, "analytics": analytics, "synced": True}
    except Exception as e:
        logger.error("metricool_sync_failed", channel=channel, error=str(e))
        return {"synced": False, "error": str(e)}


async def scheduled_reports_cron(ctx) -> None:
    """Run scheduled reports daily at 9 AM."""
    logger.info("scheduled_reports_cron_running")

    runs = await railway_pg.select(
        table="scheduled_reports",
        select="id,name,query_config,delivery_channels",
        filters=["is_active=eq.true"],
        limit=50,
    )

    for run in runs:
        try:
            logger.info("executing_scheduled_report", report_id=run["id"], name=run["name"])
        except Exception as e:
            logger.error("scheduled_report_failed", report_id=run["id"], error=str(e))


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
    functions = [
        discovery_run_task,
        sync_hypeauditor_task,
        sync_metricool_task,
    ]
    cron_jobs = [
        cron(scheduled_reports_cron, hour=9, minute=0),
        cron(sync_metricool_task, hour=2, minute=0),
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 1200
