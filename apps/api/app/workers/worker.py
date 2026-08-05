"""
ARQ worker for La Web Core async jobs.
Handles:
- AI embedding generation
- AI generation tasks (brief, post-mortem, etc.)
- Campaign automation triggers
- Scheduled report generation
- Discovery run execution (Apify, Meta, TikTok, YouTube)
- Integration syncs
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings

from shared_core import settings
from shared_core import supabase_rest

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
    meta_client,
    metricool_client,
    multi_actor_instagram_client,
    tiktok_client,
    youtube_client,
    classify_tier,
    build_rationale,
)
from discovery.scoring.lens_score import lens_score
from discovery.scoring.niche import niche_relevance
from discovery.tools.geo_boost import geo_score
from discovery.profile_generator import get_or_create_profile
from discovery.candidate_analyzer import candidate_analyzer

logger = structlog.get_logger(__name__)

APIFY_SEMAPHORE = asyncio.Semaphore(5)
MAX_HANDLES_TO_ENRICH = 25
MAX_POSTS_PER_HASHTAG = 50
MIN_FOLLOWERS_BOT_CHECK = 1000


async def startup(ctx):
    """Initialize worker context (DB, Redis) and start health server."""
    logger.info("workers_starting", env=settings.API_ENV, version="0.1.0")
    ctx["redis"] = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
    import os
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
    import uuid as uuid_lib
    from uuid import UUID as pyUUID
    try:
        conv_id = await _get_conversation_id_for_run(run_id)
        if not conv_id:
            logger.debug("no_conversation_for_run", run_id=run_id)
            return
        tool_id = str(uuid_lib.uuid4())
        await conversation_memory.save_message(
            conversation_id=pyUUID(conv_id),
            role="assistant",
            content=content,
            tool_calls=[{"id": tool_id, "name": tool, "status": "completed"}],
            tool_results=[{"tool_call_id": tool_id, "success": True, "output": {}}],
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

        async def _fetch_step1():
            return await apify_client.scrape_hashtags_all_sync(plan.hashtag_queries, results_limit=50, force_fresh=False, discovery_run_id=run_id)

        async def _fetch_step2():
            return await apify_client.search_users_by_keywords_sync(plan.keyword_queries, limit_per_keyword=30, force_fresh=False, discovery_run_id=run_id)

        print(f"[discovery_run_task] STEP 1+2: Running hashtag + keyword search in parallel", flush=True)
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
        else:
            hashtag_items = step1_result
            logger.info("step1_hashtag_done", hashtag_posts=len(hashtag_items))

        if isinstance(step2_result, Exception):
            logger.error("step2_keyword_failed", error=str(step2_result))
            step2_failed = True
        else:
            keyword_items = step2_result
            logger.info("step2_keyword_done", keyword_users=len(keyword_items))

        for item in hashtag_items:
            handle = item.get("ownerUsername") or item.get("username")
            if not handle:
                continue
            step1_handles.add(handle)
            if handle in profiles:
                continue
            profiles[handle] = {
                "username": handle,
                "full_name": item.get("ownerFullName", "") or item.get("fullName", ""),
                "fullName": item.get("ownerFullName", "") or item.get("fullName", ""),
                "bio": item.get("caption", "") or item.get("biography", ""),
                "biography": item.get("caption", "") or item.get("biography", ""),
                "avatar_url": item.get("profilePicUrlHD") or item.get("profilePicUrl", "") or item.get("displayUrl", ""),
                "profilePicUrl": item.get("profilePicUrlHD") or item.get("profilePicUrl", "") or item.get("displayUrl", ""),
                "follower_count": 0,
                "followersCount": 0,
                "following_count": 0,
                "followsCount": 0,
                "posts_count": 0,
                "postsCount": 0,
                "is_business": False,
                "isBusinessAccount": False,
                "is_verified": False,
                "verified": False,
                "locationName": item.get("locationName", "") or "",
                "location": item.get("locationName", "") or "",
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
                "full_name": item.get("fullName", ""),
                "fullName": item.get("fullName", ""),
                "bio": item.get("biography", ""),
                "biography": item.get("biography", ""),
                "avatar_url": item.get("profilePicUrlHD") or item.get("profilePicUrl", ""),
                "profilePicUrl": item.get("profilePicUrlHD") or item.get("profilePicUrl", ""),
                "follower_count": 0,
                "followersCount": 0,
                "following_count": 0,
                "followsCount": 0,
                "posts_count": 0,
                "postsCount": 0,
                "is_business": item.get("isBusinessAccount", False),
                "isBusinessAccount": item.get("isBusinessAccount", False),
                "is_verified": item.get("verified", False),
                "verified": item.get("verified", False),
            }

        unique_handles = list(profiles.keys())
        logger.info("step1_and_2_done", unique_profiles=len(unique_handles), hashtag_posts=len(hashtag_items), keyword_users=len(keyword_items))
        step_status = "completados" if not (step1_failed or step2_failed) else "parcialmente completados"
        await _save_progress_message(
            run_id,
            f"✅ **Steps 1+2 {step_status}**: Encontré **{len(unique_handles)} perfiles únicos** "
            f"({len(hashtag_items)} via hashtags + {len(keyword_items)} via keywords). "
            f"Enriqueciendo los top {min(MAX_HANDLES_TO_ENRICH, len(unique_handles))} con datos de Instagram...",
        )

        await _run_update_metadata(run_id, {
            "completed_steps": ["step1_hashtag_search", "step2_keyword_search"],
            "total_unique_handles": len(unique_handles),
            "current_step": "step3_profile_enrichment",
        })

        handles_to_enrich = unique_handles[:MAX_HANDLES_TO_ENRICH]
        print(f"[discovery_run_task] STEP 3: Profile enrichment ({len(handles_to_enrich)} profiles)", flush=True)

        async def _prefilter_profiles(
            profiles: dict[str, dict],
            geo_indicators: list[str],
            niche_keywords: list[str],
            top_n: int,
            elite_data: dict[str, Any] | None = None,
        ) -> list[tuple[str, float]]:
            from discovery.scoring.niche import niche_relevance
            from discovery.tools.geo_boost import geo_score

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
                enriched_profiles = await apify_client.enrich_profiles_sync(handles_to_enrich, force_fresh=False, discovery_run_id=run_id)
                if not enriched_profiles:
                    step3_degraded = True
                    step3_error = "Apify returned empty result"
                    await _save_progress_message(
                        run_id,
                        f"⚠️ **Step 3/4 degradado**: Apify no devolvió datos enriquecidos "
                        f"({len(handles_to_enrich)} perfiles intentados). "
                        f"Continuando con datos básicos...",
                    )
                else:
                    await _save_progress_message(
                        run_id,
                        f"✅ **Step 3/4 completado**: Enriqueí **{len(enriched_profiles)}/{len(handles_to_enrich)} perfiles** "
                        f"con datos reales de Instagram (followers, ER, bio, etc.)",
                    )
            except Exception as e:
                step3_degraded = True
                step3_error = str(e)
                logger.warning("step3_enrichment_failed", run_id=run_id, error=str(e))
                await _save_progress_message(
                    run_id,
                    f"⚠️ **Step 3/4 degradado**: Error enriqueciendo perfiles con Apify. "
                    f"Continuando con datos básicos. Detalle: {str(e)[:100]}",
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
            })

        logger.info(
            "step3_enrichment_done",
            enriched=len(enriched_profiles),
            total_profiles=len(profiles),
        )

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
        scored: list[dict] = []
        bots_filtered = 0
        target_country = (brief.audience_countries or ["VE"])[0].upper()
        for handle, p in profiles.items():
            followers = p.get("followersCount") or p.get("follower_count") or 0
            if followers < plan.min_followers:
                continue

            latest = p.get("latestPosts") or []
            er = 0.0
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

            geo_indicators = profile_data.get("geo_indicators", [])
            geo = geo_score(p, geo_indicators) if geo_indicators else 0.5
            cross_referenced = handle in cross_ref_handles
            score_val = lens_score(p, profile_data, cross_referenced=cross_referenced)
            tier = classify_tier(followers)

            if geo >= 0.85:
                bio = p.get("biography") or p.get("bio") or ""
                real_niche = niche_relevance(p, profile_data)
                is_tienda = any(
                    kw in bio.lower()
                    for kw in ("tienda", "shop", "ventas", "pedidos", "catálogo",
                               "mayor y detal", "envíos", "mercado libre", "delivery",
                               "comprar aquí", "adquirir", "whatsapp", "telf", "teléfono")
                )
                country_val = p.get("country") or (profile_data.get("countries", [""])[0] if profile_data.get("countries") else "")
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
                    "avg_likes": None,
                    "avg_comments": None,
                    "avg_views": None,
                    "engagement_rate": round(er, 6),
                    "audience_credibility": (20 if p.get("isBusinessAccount") or p.get("is_business") else 0) + (20 if p.get("verified") or p.get("is_verified") else 0),
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
                    },
                    "fetched_at": datetime.now(timezone.utc),
                })

        scored.sort(key=lambda c: c.get("match_score") or 0, reverse=True)

        MIN_MATCH_SCORE = 35
        exclude_stores = getattr(brief, "exclude_stores", True)
        qualified = [
            c for c in scored
            if (c.get("match_score") or 0) >= MIN_MATCH_SCORE
            and (not exclude_stores or not c.get("is_tienda"))
        ]

        TARGET_CANDIDATES = 50
        to_analyze = qualified[:TARGET_CANDIDATES]

        print(f"[discovery_run_task] STEP 5: AI analysis with DeepSeek ({len(to_analyze)} candidates)", flush=True)
        analyzed = await candidate_analyzer.analyze_candidates_batch(
            candidates=to_analyze,
            brief=brief,
            profile_data=profile_data,
        )

        for candidate in analyzed:
            if candidate.get("ai_rationale"):
                candidate["rationale"] = candidate["ai_rationale"]

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
                f"⚠️ Escané {len(profiles)} perfiles y {len(scored)} pasaron el filtro geográfico, "
                f"pero ninguno califica en nicho o calidad. Intenta hashtags más específicos.",
            )
        else:
            await _save_progress_message(
                run_id,
                f"✅ **Step 5/5 completado**: {len(qualified)} candidatos calificados "
                f"(de {len(scored)} que pasaron el filtro geográfico). "
                f"Top score: {qualified[0].get('match_score', 0):.0f}/100",
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

        apify_cost = apify_client.get_and_clear_cost(run_id)
        if apify_cost > 0:
            await supabase_rest.update(
                table="discovery_runs",
                values={"actual_cost_usd": apify_cost},
                filters=[f"id=eq.{run_id}"],
            )
            await supabase_rest.insert("api_costs", {
                "provider": "apify",
                "operation": "discovery_pipeline",
                "entity_id": run_id,
                "cost_usd": apify_cost,
                "request_count": 3,
                "metadata": {"run_id": run_id},
            })

        lens_active_runs.dec()
        lens_candidates_total.labels(status="inserted").inc(total)
        return {"run_id": run_id, "candidates": total}

    except Exception as e:
        logger.error("discovery_run_failed", run_id=run_id, error=str(e), exc_info=True)
        await _run_set_status(run_id, "failed", error=str(e))
        lens_active_runs.dec()
        raise


async def _execute_platform_query(platform: Platform, query, run_progress: dict | None = None) -> list[dict]:
    """Ejecuta una query en la plataforma específica."""
    if platform == Platform.INSTAGRAM:
        if query.query_type == "hashtag_search":
            raw_posts = await multi_actor_instagram_client.discover_by_hashtag(
                hashtag=query.params["hashtag"],
                country=query.params.get("country", "VE"),
                results_limit=MAX_POSTS_PER_HASHTAG,
            )

            if raw_posts:
                unique_handles = list(set(
                    p.get("ownerUsername")
                    for p in raw_posts
                    if p.get("ownerUsername")
                ))[:MAX_HANDLES_TO_ENRICH]
                logger.info("instagram_enriching_profiles", handles_count=len(unique_handles))

                profile_map: dict[str, dict] = {}
                if unique_handles:
                    try:
                        async with APIFY_SEMAPHORE:
                            profiles = await apify_client.search_instagram_profiles_batch(unique_handles)
                        if profiles is None:
                            logger.warning("Apify returned None for batch, skipping profile enrichment")
                            profile_map = {}
                        else:
                            for p in profiles:
                                username = p.get("username", "")
                                if username:
                                    profile_map[username] = p
                    except Exception as exc:
                        logger.warning("instagram_profile_enrichment_failed", error=str(exc))

                enriched_posts = []
                for post in raw_posts:
                    handle = post.get("ownerUsername", "")
                    profile = profile_map.get(handle, {})
                    if profile:
                        merged = {**post, **profile, "_from_profile": True}
                    else:
                        merged = {**post, "_from_profile": False}
                    enriched_posts.append(merged)

                return enriched_posts
            return raw_posts

        elif query.query_type == "profile_search":
            result = await apify_client.search_instagram_profile(
                username=query.params.get("keyword", ""),
            )
            return [result] if result else []
    elif platform == Platform.TIKTOK:
        if query.query_type == "hashtag_search":
            return await tiktok_client.search_content(
                query=query.params["hashtag"],
                country=query.params.get("country", "VE"),
                max_count=30,
            )
    elif platform == Platform.YOUTUBE:
        if query.query_type == "channel_search":
            return await youtube_client.search_channels(
                query=query.params.get("query", ""),
                region=query.params.get("region", "VE"),
                max_results=10,
            )
    return []


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
