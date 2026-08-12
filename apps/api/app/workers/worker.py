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
from datetime import datetime, timedelta, timezone
import os
from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings

from shared_core import settings
from shared_core import supabase_rest

from app.core.discovery_cost_tracker import get_discovery_cost_tracker
from app.core.metrics import (
    lens_active_runs,
    lens_candidates_total,
    lens_pipeline_duration_seconds,
)
from discovery.query_builder import query_builder
from discovery.schemas import BriefStructured, Platform
from discovery.memory import conversation_memory
from discovery.tools import (
    apify_client,
    hikerapi_client,
    meta_client,
    metricool_client,
    multi_actor_instagram_client,
    tiktok_client,
    youtube_client,
    classify_tier,
    build_rationale,
)
from discovery.tools.source_registry import get_instagram_source
from discovery.scoring.lens_score import lens_score
from discovery.scoring.niche import niche_relevance
from discovery.tools.geo_boost import geo_score, has_hard_geo_signal
from discovery.profile_generator import get_or_create_profile
from discovery.candidate_analyzer import candidate_analyzer

logger = structlog.get_logger(__name__)

MAX_HANDLES_TO_ENRICH = 50
MAX_POSTS_PER_HASHTAG = 20
TIER_MIN_FOLLOWERS = 5_000
TIER_MAX_FOLLOWERS = 50_000
MIN_FOLLOWERS_BOT_CHECK = 1000


async def startup(ctx):
    """Initialize worker context (DB, Redis) and start health server."""
    logger.info("workers_starting", env=settings.API_ENV, version="0.1.0")
    ctx["redis"] = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
    if os.environ.get("STANDALONE_WORKER") == "true":
        from app.workers.health_server import run_health_server
        import asyncio
        asyncio.create_task(run_health_server())


async def shutdown(ctx):
    """Cleanup on shutdown."""
    logger.info("workers_stopping")
    await apify_client.close()
    await meta_client.close()
    await youtube_client.close()
    await metricool_client.close()
    await tiktok_client.close()


# ---- Progress reporting helpers ----

async def _get_conversation_id_for_run(run_id: str) -> str | None:
    """Busca el conversation_id asociado a un discovery_run."""
    try:
        conv = await supabase_rest.select_one(
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
    try:
        await _run_set_status(run_id, "running")
        lens_active_runs.inc()

        print(f"[discovery_run_task] START run_id={run_id}", flush=True)

        run = await supabase_rest.select_one(
            table="discovery_runs",
            select="*",
            filters=[f"id=eq.{run_id}"],
        )

        if not run:
            print(f"[discovery_run_task] ABORT: Run {run_id} not found", flush=True)
            return {"error": f"Run {run_id} not found"}

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
        })

        profiles: dict[str, dict] = {}
        step1_handles: set[str] = set()
        step2_handles: set[str] = set()
        source_name = os.getenv("INSTAGRAM_SOURCE", "hikerapi")
        instagram_source = get_instagram_source(source_name)

        async def _fetch_step1():
            results = []
            for tag in plan.hashtag_queries:
                try:
                    items = await instagram_source.search_hashtag(tag, limit=MAX_POSTS_PER_HASHTAG)
                    results.extend(items)
                except Exception as e:
                    logger.warning("source_hashtag_error", source=source_name, hashtag=tag, error=str(e))
            return results

        async def _fetch_step2():
            results = []
            for kw in plan.keyword_queries:
                try:
                    items = await instagram_source.search_keyword(kw, limit=15)
                    results.extend(items)
                except Exception as e:
                    logger.warning("source_keyword_error", source=source_name, keyword=kw, error=str(e))
            return results

        print(f"[discovery_run_task] STEP 1+2: Running with source={source_name}", flush=True)
        step1_result, step2_result = await asyncio.gather(
            _fetch_step1(),
            _fetch_step2(),
            return_exceptions=True,
        )

        hashtag_items: list[dict] = []
        keyword_items: list[dict] = []
        step1_failed = False
        step2_failed = False

        if isinstance(step1_result, Exception):
            logger.error("step1_hashtag_failed", error=str(step1_result))
            step1_failed = True
            print(f"[STEP 1] FAILED: {step1_result}", flush=True)
        else:
            hashtag_items = step1_result
            print(f"[STEP 1] {len(hashtag_items)} posts from {len(plan.hashtag_queries)} hashtags source={source_name}", flush=True)
            logger.info("step1_hashtag_done", hashtag_posts=len(hashtag_items), source=source_name)

        if isinstance(step2_result, Exception):
            logger.error("step2_keyword_failed", error=str(step2_result))
            step2_failed = True
            print(f"[STEP 2] FAILED: {step2_result}", flush=True)
        else:
            keyword_items = step2_result
            print(f"[STEP 2] {len(keyword_items)} users from {len(plan.keyword_queries)} keywords source={source_name}", flush=True)
            logger.info("step2_keyword_done", keyword_users=len(keyword_items), source=source_name)

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
            }

        unique_handles = list(profiles.keys())
        logger.info("step1_and_2_done", unique_profiles=len(unique_handles), hashtag_posts=len(hashtag_items), keyword_users=len(keyword_items))
        step_status = "completados" if not (step1_failed or step2_failed) else "parcialmente completados"

        if not unique_handles and not step1_failed and not step2_failed:
            print(f"[FALLBACK] No candidates from niche queries. Trying broad keywords...", flush=True)
            await _save_progress_message(
                run_id,
                "Los hashtags específicos no encontraron candidatos. Ampliando búsqueda con términos generales...",
            )
            industry = (brief.industry or "").lower()
            broad_keywords: list[str] = []
            if industry in ("mascotas", "pet", "animals"):
                broad_keywords = ["mascotas", "perros", "pets", "doglover", "mascota", "cuidado animal"]
            elif industry in ("food", "comida", "bebida"):
                broad_keywords = ["comida", "cocina", "recetas", "foodie", "gastronomia", "chef"]
            elif industry in ("moda", "fashion", "vestuario"):
                broad_keywords = ["moda", "fashion", "estilo", "outfit", "tendencias"]
            elif industry in ("fitness", "gym", "salud"):
                broad_keywords = ["fitness", "gym", "ejercicio", "salud", "entrenamiento"]
            elif industry in ("belleza", "beauty", "cosmeticos"):
                broad_keywords = ["belleza", "makeup", "beauty", "skincare", "cosmeticos"]
            else:
                broad_keywords = ["lifestyle", "vzla", "venezuela", "caracas"]

            fallback_items: list[dict] = []
            for kw in broad_keywords:
                try:
                    items = await instagram_source.search_keyword(kw, limit=20)
                    fallback_items.extend(items)
                    print(f"[FALLBACK] keyword={kw} returned={len(items)} items", flush=True)
                except Exception as e:
                    print(f"[FALLBACK] keyword={kw} error={e}", flush=True)

            for item in fallback_items:
                handle = item.get("username", "")
                if not handle:
                    continue
                step1_handles.add(handle)
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
                    "locationName": "",
                    "location": "",
                    "pk": item.get("pk"),
                }

            unique_handles = list(profiles.keys())
            print(f"[FALLBACK] Total candidates after fallback: {len(unique_handles)}", flush=True)

        prefiltered_handles = []
        stores_prefiltered = 0
        low_followers_prefiltered = 0
        private_prefiltered = 0
        for handle in unique_handles:
            p = profiles.get(handle, {})
            followers = p.get("followersCount") or p.get("follower_count") or 0
            is_biz = p.get("isBusinessAccount") or p.get("is_business") or False
            is_priv = p.get("is_private", False)
            if followers < plan.min_followers:
                low_followers_prefiltered += 1
                continue
            if is_biz and followers < 50000:
                stores_prefiltered += 1
                continue
            if is_priv and followers < 10000:
                private_prefiltered += 1
                continue
            prefiltered_handles.append(handle)

        logger.info(
            "step1_prefiltered",
            total=len(unique_handles),
            after_prefilter=len(prefiltered_handles),
            stores_filtered=stores_prefiltered,
            low_followers_filtered=low_followers_prefiltered,
            private_filtered=private_prefiltered,
        )

        await _save_progress_message(
            run_id,
            f"✅ Encontré {len(unique_handles)} perfiles candidatos. "
            f"Filtrando tiendas y cuentas sin seguidores suficientes...",
        )

        await _run_update_metadata(run_id, {
            "completed_steps": ["step1_hashtag_search", "step2_keyword_search"],
            "total_unique_handles": len(unique_handles),
            "prefiltered_handles": len(prefiltered_handles),
            "stores_prefiltered": stores_prefiltered,
            "current_step": "step3_profile_enrichment",
        })

        handles_to_enrich = prefiltered_handles[:MAX_HANDLES_TO_ENRICH]
        print(f"[discovery_run_task] STEP 3: Profile enrichment ({len(handles_to_enrich)} profiles)", flush=True)

        async def _prefilter_profiles(
            profiles: dict[str, dict],
            geo_indicators: list[str],
            niche_keywords: list[str],
            top_n: int,
            elite_data: dict[str, Any] | None = None,
        ) -> list[tuple[str, float]]:
            from discovery.scoring.niche import niche_relevance
            from discovery.tools.geo_boost import geo_score, has_hard_geo_signal

            anti_bot_signals: list[str] = []
            niche_benchmarks: dict[str, Any] = {}
            if elite_data and isinstance(elite_data, dict):
                anti_bot_signals = elite_data.get("anti_bot_signals", [])
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
                commerce_signals = (
                    ("tienda" in bio_lower or "shop" in bio_lower) +
                    ("ventas" in bio_lower or "pedidos" in bio_lower) +
                    ("catálogo" in bio_lower or "mayor y detal" in bio_lower) +
                    ("envíos" in bio_lower or "delivery" in bio_lower) +
                    ("comprar" in bio_lower or "adquirir" in bio_lower) +
                    ("whatsapp" in bio_lower or "telf" in bio_lower or "teléfono" in bio_lower) +
                    ("precio" in bio_lower or "oferta" in bio_lower or "descuento" in bio_lower) +
                    ("horario" in bio_lower or "sucursal" in bio_lower or "local" in bio_lower) +
                    ("market" in bio_lower or "boutique" in bio_lower or "almacén" in bio_lower)
                )
                creator_signals = (
                    ("creador" in bio_lower or "content creator" in bio_lower or "reviewer" in bio_lower) +
                    ("vlogger" in bio_lower or "youtuber" in bio_lower or "tiktoker" in bio_lower) +
                    ("streamer" in bio_lower or "entrenador" in bio_lower or "coach" in bio_lower) +
                    ("atleta" in bio_lower or "deportista" in bio_lower or "fitness" in bio_lower) +
                    ("influencer" in bio_lower or "blogger" in bio_lower or "periodista" in bio_lower) +
                    ("presentador" in bio_lower or "comunicador" in bio_lower or "actor" in bio_lower) +
                    ("cantante" in bio_lower or "músico" in bio_lower or "artista" in bio_lower) +
                    ("creativo" in bio_lower or "emprendedor" in bio_lower and not commerce_signals) +
                    ("diseñador" in bio_lower or "fotógrafo" in bio_lower or "artista" in bio_lower)
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

        if handles_to_enrich:
            try:
                if source_name == "hikerapi":
                    logger.info("step3_using_hikerapi_enrichment", handles_count=len(handles_to_enrich))
                    enriched_profiles = []
                    for handle in handles_to_enrich:
                        try:
                            profile = await hikerapi_client.enrich_profile(handle)
                            if profile:
                                enriched_profiles.append(profile)
                            await asyncio.sleep(1.0)
                        except Exception as e:
                            logger.warning("hikerapi_enrich_error", handle=handle, error=str(e))
                    if enriched_profiles:
                        await _save_progress_message(
                            run_id,
                            f"✅ Enriquecí {len(enriched_profiles)} perfiles con datos completos "
                            f"(seguidores, engagement, biografía). Analizando calidad...",
                        )
                    else:
                        step3_degraded = True
                        step3_error = "HikerAPI returned empty result"
                        await _save_progress_message(
                            run_id,
                            "⚠️ Tuve un problema técnico obteniendo datos completos. "
                            "Continuando con datos básicos para no retrasar tu búsqueda...",
                        )
                else:
                    raise ValueError(
                        f"INSTAGRAM_SOURCE='{source_name}' is not supported. "
                        "Only HikerAPI is available. Set INSTAGRAM_SOURCE=hikerapi or leave unset."
                    )
            except Exception as e:
                step3_degraded = True
                step3_error = str(e)
                logger.warning("step3_enrichment_failed", run_id=run_id, error=str(e))
                await _save_progress_message(
                    run_id,
                    "⚠️ Tuve un problema técnico con algunos perfiles. "
                    "Continuando con los datos que tenemos...",
                )

        for e in enriched_profiles:
            handle = e.get("username", "")
            if not handle or handle not in profiles:
                continue
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
                "locationName": e.get("locationName", profiles[handle].get("locationName", "")),
                "location": e.get("locationName", profiles[handle].get("location", "")),
                "latestPosts": e.get("latestPosts", []),
                "engagement_rate": e.get("engagement_rate"),
            })

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
            "completed_steps": ["step1_hashtag_search", "step2_keyword_search", "step3_profile_enrichment"],
        })

        print(f"[discovery_run_task] STEP 4: Scoring {len(profiles)} profiles", flush=True)

        exclude_handles = set(h.lower() for h in (plan.exclude_handles or []))
        if exclude_handles:
            original_count = len(profiles)
            profiles = {k: v for k, v in profiles.items() if k.lower() not in exclude_handles}
            print(f"[discovery_run_task] STEP 4: Excluded {original_count - len(profiles)} handles, scoring {len(profiles)} remaining", flush=True)

        cross_ref_handles = step1_handles & step2_handles
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
        target_country = (brief.audience_countries or ["VE"])[0].upper()
        political_keywords = (
            "político", "política", "politología", "politólogo",
            "gobierno", "gobierno de", "gobierno nacional",
            "maduro", "madurista", "maduristas",
            "chavismo", "chavista", "chavistas", "chávez", "chavez",
            "oposición", "opositor", "opositores", "oposición",
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

            bio = p.get("biography") or p.get("bio") or ""
            profile_country = (p.get("country") or "").strip().upper()
            if profile_country and profile_country != target_country:
                geo_country_mismatch += 1
                continue

            non_ve_signals = (
                "españa", "spain", "salamanca", "madrid", "barcelona", "valencia es",
                "dominicana", "santo domingo", "santiago rd",
                "méxico", "colombia", "argentina", "chile", "perú",
                "estados unidos", "usa ", "miami", "nyc", "texas",
                "kenwood españa", "embajador kenwood",
            )
            bio_geo = f"{bio.lower()} {handle.lower()} {p.get('full_name', '').lower()}"
            if any(sig in bio_geo for sig in non_ve_signals):
                geo_country_mismatch += 1
                continue

            handle_lower = handle.lower()
            non_ve_handle_tlds = (
                ".rd", ".do", ".mx", ".ar", ".co", ".cl", ".pe",
                ".ec", ".pa", ".uy", ".py", ".bo", ".cr",
                "_rd", "_do", "_mx", "_ar", "_co", "_cl", "_pe",
                "_ec", "_pa", "_uy", "_py", "_bo", "_cr",
            )
            if any(handle_lower.endswith(tld) for tld in non_ve_handle_tlds):
                geo_country_mismatch += 1
                continue

            geo_indicators = profile_data.get("geo_indicators", [])
            geo = geo_score(p, geo_indicators) if geo_indicators else 0.5
            if geo_indicators and geo == 0.0:
                if not has_hard_geo_signal(p, target_country):
                    geo_no_signal += 1
                    continue

            bio_or_username = f"{bio.lower()} {handle.lower()}"
            if any(kw in bio_or_username for kw in political_keywords):
                political_filtered += 1
                continue

            cross_referenced = hashtag_appearances.get(handle, 0) >= 2
            score_val = lens_score(p, profile_data, cross_referenced=cross_referenced)
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
                },
                "fetched_at": datetime.now(timezone.utc),
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
            },
            top_5=top_5_summary,
        )

        MIN_MATCH_SCORE = 20
        exclude_stores = getattr(brief, "exclude_stores", True)
        qualified = [
            c for c in scored
            if (c.get("match_score") or 0) >= MIN_MATCH_SCORE
            and (not exclude_stores or not c.get("is_tienda"))
        ]

        TARGET_CANDIDATES = 50
        to_analyze = qualified[:TARGET_CANDIDATES]

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
            print(f"[discovery_run_task] STEP 5: Skipping AI analysis (analyze_with_ai=False), using rule-based scores", flush=True)
            analyzed = to_analyze

        await _run_update_metadata(run_id, {
            "current_step": "step5_ai_analysis",
            "completed_steps": [
                "step1_hashtag_search",
                "step2_keyword_search",
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
            "completed_at": datetime.now(timezone.utc),
        })
        await _run_update_metadata(run_id, {
            "current_step": "completed",
            "candidates_found": total,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "step3_degraded": step3_degraded,
            "step3_error": step3_error,
        })

        conv = await supabase_rest.select_one(
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

        apify_cost = apify_client.get_and_clear_cost(run_id)
        if apify_cost > 0:
            tracker.record_apify_cost(
                run_id=run_id,
                actor_id="discovery_pipeline",
                cost_usd=apify_cost,
                metadata={"run_id": run_id},
            )

        cost_summary = tracker.get_run_summary(run_id)
        total_cost = cost_summary["total_usd"]

        await supabase_rest.update(
            table="discovery_runs",
            values={"actual_cost_usd": total_cost},
            filters=[f"id=eq.{run_id}"],
        )
        await tracker.flush(run_id)

        lens_active_runs.dec()
        lens_candidates_total.labels(status="inserted").inc(total)
        return {"run_id": run_id, "candidates": total}

    except Exception as e:
        logger.error("discovery_run_failed", run_id=run_id, error=str(e), exc_info=True)
        await _run_set_status(run_id, "failed", error=str(e))
        try:
            tracker = get_discovery_cost_tracker()
            apify_cost = apify_client.get_and_clear_cost(run_id)
            if apify_cost > 0:
                tracker.record_apify_cost(run_id=run_id, actor_id="discovery_pipeline", cost_usd=apify_cost)
            await tracker.flush(run_id)
        except Exception:
            pass
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
        result = await supabase_rest.upsert_many(
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
                await supabase_rest.insert(
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
    values = {"status": status, "started_at": datetime.now(timezone.utc)}
    if error:
        values["error"] = error
    await supabase_rest.update(
        table="discovery_runs",
        filters=[f"id=eq.{run_id}"],
        values=values,
    )


async def _run_update(run_id: str, values: dict) -> None:
    await supabase_rest.update(
        table="discovery_runs",
        filters=[f"id=eq.{run_id}"],
        values=values,
    )


async def _run_update_metadata(run_id: str, metadata: dict) -> None:
    """Atomic metadata update using PostgreSQL JSONB merge operator."""
    try:
        await supabase_rest.rpc(
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

    influencer = await supabase_rest.select_one(
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

    runs = await supabase_rest.select(
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
    job_timeout = 600
