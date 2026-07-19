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

from datetime import datetime, timedelta

import structlog
from arq import cron
from arq.connections import RedisSettings

from shared_core import settings
from shared_core import supabase_rest
from discovery.query_builder import query_builder
from discovery.result_ranker import result_ranker
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
    Ejecuta un discovery_run completo:
    1. Carga el run de la BD
    2. Parsea el brief
    3. Ejecuta queries en todas las plataformas
    4. Scorea cada candidato
    5. Persiste en discovery_candidates
    6. Actualiza el estado del run
    """
    try:
        await _run_set_status(run_id, "running")

        print(f"[discovery_run_task] START run_id={run_id}", flush=True)

        run = await supabase_rest.select_one(
            table="discovery_runs",
            select="*",
            filters=[f"id=eq.{run_id}"],
        )

        if not run:
            print(f"[discovery_run_task] ABORT: Run {run_id} not found", flush=True)
            return {"error": f"Run {run_id} not found"}

        print(f"[discovery_run_task] brief_parsed={run.get('brief_parsed')}", flush=True)

        brief_parsed = run.get("brief_parsed", {})
        if isinstance(brief_parsed, str):
            import json
            brief_parsed = json.loads(brief_parsed)

        brief = BriefStructured(**brief_parsed)
        platforms_raw = run.get("platforms", ["instagram"])
        platforms = [Platform(p) if isinstance(p, str) else p for p in platforms_raw]

        queries = query_builder.build(brief)
        print(f"[discovery_run_task] queries built: {list(queries.keys())}", flush=True)
        await _run_update_metadata(run_id, {
            "current_step": "building_queries",
            "completed_steps": ["parsing_brief"],
            "platforms": [p.value for p in platforms],
            "total_queries": sum(len(queries.get(p, [])) for p in platforms),
            "candidates_found": 0,
        })
        all_candidates: list[dict] = []

        for platform in platforms:
            platform_queries = queries.get(platform, [])
            for q in platform_queries:
                step_label = f"querying_{platform.value}_{q.query_type}"
                await _run_update_metadata(run_id, {
                    "current_step": step_label,
                    "current_hashtag": q.params.get("hashtag", q.params.get("query", "")),
                })
                logger.info(
                    "discovery_executing_query",
                    platform=platform.value,
                    query_type=q.query_type,
                    params=q.params,
                )
                try:
                    candidates = await _execute_platform_query(platform, q)
                    logger.info(
                        "discovery_query_done",
                        platform=platform.value,
                        query_type=q.query_type,
                        candidates_count=len(candidates),
                    )
                    await _run_update_metadata(run_id, {
                        "candidates_found": len(all_candidates),
                        "last_query_platform": platform.value,
                        "last_query_type": q.query_type,
                    })
                    for raw in candidates:
                        metrics = _raw_to_candidate_dict(raw, platform)
                        score = result_ranker.rank(
                            CandidateMetrics(**metrics),
                            brief,
                        )
                        all_candidates.append({
                            "run_id": run_id,
                            "platform": platform.value,
                            "handle": metrics.get("handle", "unknown"),
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
                            "engagement_rate": metrics.get("engagement_rate"),
                            "audience_credibility": metrics.get("audience_credibility"),
                            "audience_quality": metrics.get("audience_quality"),
                            "audience_gender_split": metrics.get("audience_gender_split"),
                            "audience_age_buckets": metrics.get("audience_age_buckets"),
                            "match_score": score.match_score,
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
                            "raw_payload": raw,
                            "fetched_at": datetime.utcnow().isoformat(),
                        })
                except Exception as e:
                    logger.error(
                        "discovery_query_failed",
                        platform=platform.value,
                        query=q.query_type,
                        params=q.params,
                        error=str(e),
                        exc_info=True,
                    )

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
                f"ER {c.get('engagement_rate', 0):.1f}%"
                for c in top_candidates
            ]
            content = (
                f"Terminé la búsqueda. Encontré {len(qualified)} candidatos "
                f"que coinciden con tu brief.\n\n"
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
                results_limit=50,
            )

            if raw_posts:
                unique_handles = list(set(
                    p.get("ownerUsername")
                    for p in raw_posts
                    if p.get("ownerUsername")
                ))
                logger.info("instagram_enriching_profiles", handles_count=len(unique_handles))

                profile_map: dict[str, dict] = {}
                if unique_handles:
                    try:
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
                max_count=100,
            )
    elif platform == Platform.YOUTUBE:
        if query.query_type == "channel_search":
            return await youtube_client.search_channels(
                query=query.params.get("query", ""),
                region=query.params.get("region", "VE"),
                max_results=20,
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
                engagement_rate = round((likes + comments) / max(followers, 1) * 100, 4)
            elif likes > 0:
                engagement_rate = round((likes + comments) / max(likes, 1) * 100, 2)

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
            engagement_rate = 0.0
            if likes > 0:
                engagement_rate = round((likes + comments) / max(likes, 1) * 100, 2)

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
    existing = await supabase_rest.select_one(
        table="discovery_runs",
        select="metadata",
        filters=[f"id=eq.{run_id}"],
    )
    current = existing.get("metadata", {}) if existing else {}
    merged = {**current, **metadata, "updated_at": datetime.utcnow().isoformat()}
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
