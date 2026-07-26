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
from datetime import datetime, timedelta

import structlog
from arq import cron
from arq.connections import RedisSettings

from shared_core import settings
from shared_core import supabase_rest
from discovery.query_builder import query_builder
from discovery.result_ranker import result_ranker
from discovery.result_ranker import (
    calculate_ica,
    calculate_geo_foco_real,
    calculate_engagement_velocity,
    calculate_business_intent,
    calculate_lwfa_composite,
)
from discovery.schemas import BriefStructured, CandidateMetrics, Platform
from discovery.tools import (
    apify_client,
    meta_client,
    metricool_client,
    multi_actor_instagram_client,
    tiktok_client,
    youtube_client,
)

logger = structlog.get_logger(__name__)

APIFY_SEMAPHORE = asyncio.Semaphore(3)
MAX_HANDLES_TO_ENRICH = 80
MAX_POSTS_PER_HASHTAG = 50


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


# ---- Discovery tasks ----

async def discovery_run_task(ctx, run_id: str) -> dict:
    """
    Ejecuta un discovery_run completo con pipeline de 4 capas:

    STEP 1: Keyword Discovery — instagram-search-scraper (usuarios por keyword)
    STEP 2: Hashtag Deep Dive — instagram-hashtag-scraper (posts con geotags)
    STEP 3: Profile Enrichment — instagram-profile-scraper (followers, latestPosts, country)
    STEP 4: Engagement Analytics — engagement-analytics actor (LWFA KPIs)
    STEP 5: LWFA Scoring — 4 KPIs exclusivos + composite score
    """
    try:
        await _run_set_status(run_id, "running")

        print(f"[discovery_run_task] START run_id={run_id}", flush=True)

        apify_client.discovery_run_id = run_id

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
        plan = query_builder.build(brief)

        await _run_update_metadata(run_id, {
            "current_step": "step1_keyword_discovery",
            "completed_steps": [],
            "keywords_count": len(plan.keyword_queries),
            "hashtags_count": len(plan.hashtag_queries),
            "candidates_found": 0,
        })

        all_profiles: list[dict] = []
        seen_handles: set[str] = set()

        all_candidates: list[dict] = []
        analytics_by_handle: dict[str, dict] = {}
        posts_by_hashtag: dict[str, list[dict]] = {}

        try:
            await _run_update_metadata(run_id, {"current_step": "step1_keyword_discovery"})
            users_from_keywords = await apify_client.search_users_by_multiple_keywords(
                plan.keyword_queries,
                limit_per_keyword=30,
            )
            logger.info(
                "step1_keyword_discovery_done",
                users_found=len(users_from_keywords),
            )
            for u in users_from_keywords:
                h = u.get("username", "")
                if h and h not in seen_handles:
                    seen_handles.add(h)
                    all_profiles.append(u)

            await _run_update_metadata(run_id, {
                "completed_steps": ["step1_keyword_discovery"],
                "step1_profiles": len(all_profiles),
                "current_step": "step2_hashtag_discovery",
            })

            await _run_update_metadata(run_id, {"current_step": "step2_hashtag_deep_dive"})
            posts_by_hashtag = await apify_client.scrape_hashtags_batch(
                plan.hashtag_queries,
                results_per_hashtag=30,
            )
            total_hashtag_posts = sum(len(v) for v in posts_by_hashtag.values())
            logger.info(
                "step2_hashtag_deep_dive_done",
                hashtags_scraped=len(posts_by_hashtag),
                total_posts=total_hashtag_posts,
            )

            for hashtag, posts in posts_by_hashtag.items():
                for post in posts:
                    h = post.get("ownerUsername", "")
                    if h and h not in seen_handles:
                        seen_handles.add(h)
                        all_profiles.append(post)

            await _run_update_metadata(run_id, {
                "completed_steps": ["step1_keyword_discovery", "step2_hashtag_deep_dive"],
                "total_unique_handles": len(all_profiles),
                "current_step": "step3_profile_enrichment",
            })

            await _run_update_metadata(run_id, {"current_step": "step3_profile_enrichment"})
            handles_to_enrich = list(seen_handles)[:MAX_HANDLES_TO_ENRICH]
            logger.info(
                "step3_enriching_profiles",
                handles_count=len(handles_to_enrich),
            )

            enriched_profiles: list[dict] = []
            if handles_to_enrich:
                async with APIFY_SEMAPHORE:
                    enriched_profiles = await apify_client.search_instagram_profiles_batch(
                        handles_to_enrich
                    )
            profile_map = {p.get("username", ""): p for p in enriched_profiles if p.get("username")}

            logger.info(
                "step3_profile_enrichment_done",
                enriched=len(profile_map),
                total_handles=len(handles_to_enrich),
            )

            await _run_update_metadata(run_id, {
                "completed_steps": [
                    "step1_keyword_discovery",
                    "step2_hashtag_deep_dive",
                    "step3_profile_enrichment",
                ],
                "enriched_profiles": len(profile_map),
                "current_step": "step4_engagement_analytics",
            })

            top_handles_for_analytics = sorted(
                profile_map.keys(),
                key=lambda h: profile_map[h].get("followersCount", 0) or 0,
                reverse=True,
            )[:plan.analytics_top_n]

            if top_handles_for_analytics:
                await _run_update_metadata(run_id, {"current_step": "step4_engagement_analytics"})
                analytics_results = await apify_client.analyze_profile_engagement(
                    top_handles_for_analytics,
                    posts_to_analyze=30,
                )
                for a in analytics_results:
                    handle = a.get("profile_username", a.get("username", ""))
                    if handle:
                        analytics_by_handle[handle] = a
                logger.info(
                    "step4_analytics_done",
                    profiles_analyzed=len(analytics_by_handle),
                )

        except Exception as e:
            logger.error("discovery_pipeline_steps_1_4_failed", run_id=run_id, error=str(e), exc_info=True)
            await _run_set_status(run_id, "failed", error=f"Pipeline steps 1-4 failed: {str(e)}")
            raise

        total_cost = apify_client.get_and_clear_cost(run_id)
        await _run_update_metadata(run_id, {
            "completed_steps": [
                "step1_keyword_discovery",
                "step2_hashtag_deep_dive",
                "step3_profile_enrichment",
                "step4_engagement_analytics",
            ],
            "current_step": "step5_lwfa_scoring",
            "candidates_found": len(all_profiles),
            "actual_cost_usd": round(total_cost, 4),
        })

        for raw in all_profiles:
            handle = raw.get("username", raw.get("ownerUsername", ""))
            if not handle:
                continue

            profile_data = profile_map.get(handle, raw)
            metrics = _raw_to_candidate_dict(profile_data, Platform.INSTAGRAM)
            score = result_ranker.rank(CandidateMetrics(**metrics), brief)

            analytics = analytics_by_handle.get(handle, {})

            geo_foco = calculate_geo_foco_real(
                geotags=analytics.get("top_geotags", []),
                captions=analytics.get("captions_sample", []),
                profile_bio=profile_data.get("biography", ""),
            )
            velocity = analytics.get("avg_engagement_velocity_per_day", 0.0)
            business_intent = calculate_business_intent(profile_data)
            consistency = analytics.get("engagement_consistency_score", 0.5)
            clips_pct = analytics.get("content_mix_clips_pct", 0.0)

            comment_rate = analytics.get("comment_rate_pct", 0.0)
            total_views = analytics.get("total_views", 0) or 0
            sample_comments = analytics.get("latest_comments", [])
            ica_score = calculate_ica(sample_comments, total_views) if sample_comments else comment_rate

            er = metrics.get("engagement_rate") or 0.0
            lwfa_composite = calculate_lwfa_composite(
                engagement_rate=er,
                business_intent=business_intent,
                velocity_score=velocity,
                geo_foco=geo_foco,
                consistency_score=consistency,
                clips_pct=clips_pct,
                ica_score=ica_score,
            )

            all_candidates.append({
                "run_id": run_id,
                "platform": "instagram",
                "handle": handle,
                "full_name": metrics.get("full_name"),
                "bio": metrics.get("bio"),
                "avatar_url": metrics.get("avatar_url"),
                "country": metrics.get("country"),
                "city": metrics.get("city"),
                "followers": metrics.get("followers"),
                "following": metrics.get("following"),
                "posts_count": metrics.get("posts_count"),
                "avg_likes": metrics.get("avg_likes"),
                "avg_comments": metrics.get("avg_comments"),
                "avg_views": metrics.get("avg_views"),
                "engagement_rate": er,
                "audience_credibility": metrics.get("audience_credibility"),
                "audience_quality": metrics.get("audience_quality"),
                "audience_gender_split": metrics.get("audience_gender_split"),
                "audience_age_buckets": metrics.get("audience_age_buckets"),
                "match_score": lwfa_composite,
                "niche_relevance": score.niche_relevance,
                "geo_relevance": score.geo_relevance,
                "audience_relevance": score.audience_relevance,
                "content_quality": score.content_quality,
                "estimated_cost": score.estimated_cost,
                "expected_reach": score.expected_reach,
                "expected_engagement": score.expected_engagement,
                "roi_estimate": score.roi_estimate,
                "rationale": score.rationale,
                "status": "new",
                "raw_payload": {
                    **raw,
                    "ica_score": ica_score,
                    "geo_foco_score": geo_foco,
                    "velocity_score": velocity,
                    "business_intent_score": business_intent,
                    "consistency_score": consistency,
                    "clips_pct": clips_pct,
                    "lwfa_composite": lwfa_composite,
                    "analytics": analytics,
                },
                "fetched_at": datetime.utcnow().isoformat(),
            })

        await _run_update_metadata(run_id, {
            "current_step": "inserting_candidates",
            "candidates_found": len(all_candidates),
        })

        MIN_SCORE = 15
        MIN_FOLLOWERS = 100

        qualified = [
            c for c in all_candidates
            if (c.get("match_score") or 0) >= MIN_SCORE
            and (c.get("followers") or 0) >= MIN_FOLLOWERS
        ]

        if len(qualified) < 5:
            qualified = [
                c for c in all_candidates
                if (c.get("match_score") or 0) >= 5
                and (c.get("followers") or 0) >= 50
            ]

        logger.info(
            "candidates_filtered",
            total=len(all_candidates),
            qualified=len(qualified),
            min_score=MIN_SCORE,
            min_followers=MIN_FOLLOWERS,
        )

        await _deduplicate_and_insert_candidates(qualified, run_id)

        total = len(all_candidates)
        print(f"[discovery_run_task] DONE run_id={run_id} total_candidates={total}", flush=True)
        await _run_update(run_id, {
            "status": "completed",
            "total_candidates": total,
            "completed_at": datetime.utcnow().isoformat(),
        })
        await _run_update_metadata(run_id, {
            "current_step": "completed",
            "candidates_found": total,
            "completed_at": datetime.utcnow().isoformat(),
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

        logger.info("discovery_run_completed", run_id=run_id, candidates=total)
        return {"run_id": run_id, "candidates": total}

    except Exception as e:
        logger.error("discovery_run_failed", run_id=run_id, error=str(e), exc_info=True)
        await _run_set_status(run_id, "failed", error=str(e))
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
                "avatar_url": raw.get("profilePicUrl", raw.get("displayUrl", "")),
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
                "avatar_url": raw.get("displayUrl", ""),
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


async def _deduplicate_and_insert_candidates(candidates: list[dict], run_id: str) -> None:
    """Inserta candidatos. Datos ya vienen deduplicados por (platform, handle) upstream."""
    for c in candidates:
        try:
            await supabase_rest.insert(
                table="discovery_candidates",
                values=c,
                returning="minimal",
            )
        except Exception as exc:
            logger.warning(
                "candidate_insert_failed",
                run_id=run_id,
                handle=c.get("handle"),
                platform=c.get("platform"),
                error=str(exc),
            )


async def _run_set_status(run_id: str, status: str, error: str | None = None) -> None:
    values = {"status": status, "started_at": datetime.utcnow().isoformat()}
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
    except Exception:
        merged = {**metadata, "updated_at": datetime.utcnow().isoformat()}
        await supabase_rest.update(
            table="discovery_runs",
            filters=[f"id=eq.{run_id}"],
            values={"metadata": merged},
        )


# ---- Existing tasks ----

async def embed_document_task(ctx, document_id: str) -> dict:
    """Chunk a document, embed it, store in pgvector."""
    logger.info("embed_document_task", document_id=document_id)

    doc = await supabase_rest.select_one(
        table="documents",
        select="id,content,doc_type",
        filters=[f"id=eq.{document_id}"],
    )

    if not doc:
        return {"error": "Document not found"}

    from shared_ai import embed_texts
    from app.ai.indexer import index_document_chunks

    text = doc.get("content", "")
    chunks = _chunk_text(text, chunk_size=600, overlap=100)
    embeddings = await embed_texts(chunks)

    await index_document_chunks(
        document_id=document_id,
        chunks=chunks,
        embeddings=embeddings,
        content_type=doc.get("doc_type", "document"),
    )

    await supabase_rest.update(
        table="documents",
        filters=[f"id=eq.{document_id}"],
        values={
            "status": "indexed",
            "chunk_count": len(chunks),
            "indexed_at": datetime.utcnow().isoformat(),
        },
    )

    return {"document_id": document_id, "chunks": len(chunks)}


def _chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


async def generate_insight_task(ctx, campaign_id: str, prompt_code: str) -> dict:
    """Generate an AI insight for a campaign."""
    logger.info("generate_insight_task", campaign_id=campaign_id, prompt_code=prompt_code)

    campaign = await supabase_rest.select_one(
        table="campaigns",
        select="*",
        filters=[f"id=eq.{campaign_id}"],
    )

    if not campaign:
        return {"error": "Campaign not found"}

    from app.services.ai_service import get_ai_service
    ai = get_ai_service()

    prompt = _build_insight_prompt(prompt_code, campaign)
    response = await ai.generate(prompt=prompt, user_id=None)

    insight = await supabase_rest.insert(
        table="insights",
        values={
            "campaign_id": campaign_id,
            "prompt_code": prompt_code,
            "content": response.get("content", ""),
            "model_provider": "deepseek",
            "created_by": "system",
        },
        select="id",
        return_http_status=201,
    )

    return {"insight_id": insight["id"], "campaign_id": campaign_id}


def _build_insight_prompt(code: str, campaign: dict) -> str:
    base = f"Análisis de campaña: {campaign.get('name', 'Sin nombre')}"
    if code == "performance":
        return f"{base}\n\nGenera un insight de performance con recomendaciones."
    elif code == "audience":
        return f"{base}\n\nAnaliza la audiencia y sugiere mejoras."
    return f"{base}\n\nGenera un insight general."


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
        embed_document_task,
        generate_insight_task,
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
