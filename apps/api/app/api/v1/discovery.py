"""API v1 router para el módulo de Discovery."""

import contextlib
import uuid as uuidlib
from uuid import UUID

from discovery.orchestrator import orchestrator
from discovery.schemas import (
    BriefStructured,
    ConversationResponse,
    ConversationStep,
    DiscoveryConversationCreate,
    DiscoveryRunResponse,
    DiscoveryRunStatus,
    DiscoverySearchRequest,
    MessageCreate,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from shared_core import supabase_rest

from app.core.security import CurrentUserDep


class EnrichRequest(BaseModel):
    influencer_ids: list[str] | None = None
    all_active: bool = False


class EnrichResult(BaseModel):
    influencer_id: str
    handle: str
    success: bool
    followers: int | None = None
    engagement_rate: float | None = None
    error: str | None = None


class EnrichResponse(BaseModel):
    total: int
    enriched: int
    failed: int
    cost_usd: float
    results: list[EnrichResult]

router = APIRouter(prefix="/discovery", tags=["discovery"])


class InlineMessageResponse(BaseModel):
    id: str
    created_at: str


class InlineAssistantMessage(BaseModel):
    id: str
    created_at: str


# ---- Conversations (chat style) ----

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(body: DiscoveryConversationCreate, user: CurrentUserDep):
    """Crea una conversación nueva de discovery."""
    from discovery.memory import conversation_memory

    conversation_id = uuidlib.uuid4()
    result = await orchestrator.create_conversation(
        conversation_id=conversation_id,
        initial_brief=body.initial_brief,
    )

    await conversation_memory.save_conversation(
        conversation_id=conversation_id,
        user_id=user.id,
        bu_id=body.bu_id,
        step=ConversationStep.START.value,
    )

    return ConversationResponse(
        id=conversation_id,
        current_step=ConversationStep.START,
        status="active",
        started_at=result.get("started_at", ""),
        last_message_at=result.get("last_message_at", ""),
    )


@router.get("/conversations")
async def list_conversations(
    user_id: UUID | None = None,
    status_filter: str = "active",
    limit: int = 20,
):
    """Lista conversaciones del usuario."""
    filters = []
    if user_id:
        filters.append(f"user_id=eq.{user_id}")
    if status_filter:
        filters.append(f"status=eq.{status_filter}")

    result = await supabase_rest.select(
        table="discovery_conversations",
        select="id,user_id,current_step,status,message_count,started_at,last_message_at",
        filters=filters,
        order="last_message_at.desc",
        limit=limit,
    )

    return result


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: UUID):
    """Obtiene detalle de una conversación con sus mensajes."""
    from discovery.memory import conversation_memory

    conv = await conversation_memory.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await supabase_rest.select(
        table="discovery_messages",
        select="id,role,content,tool_calls,tool_results,reasoning,cost_usd,latency_ms,created_at",
        filters=[f"conversation_id=eq.{conversation_id}"],
        order="created_at.asc",
        limit=100,
    )

    return {**conv, "messages": messages}


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    message: MessageCreate,
    user: CurrentUserDep,
):
    """Procesa un mensaje del usuario y retorna la respuesta IA."""
    from discovery.memory import conversation_memory

    user_message_record = await supabase_rest.insert(
        table="discovery_messages",
        values={
            "conversation_id": str(conversation_id),
            "role": "user",
            "content": message.content,
        },
        returning="representation",
    )

    ai_response = await orchestrator.process_message(
        conversation_id=conversation_id,
        message=message,
    )

    assistant_content = ai_response["message"]

    if ai_response.get("pending_discovery"):
        from app.core.worker_enqueuer import enqueue_discovery_run
        brief_data = ai_response.get("brief")
        if brief_data:
            try:
                brief = BriefStructured(**brief_data)
                run = await conversation_memory.launch_discovery_run(
                    brief=DiscoverySearchRequest(
                        product_name=brief.product_name,
                        industry=brief.industry,
                        niches=brief.niches,
                        audience_gender=brief.audience_gender,
                        audience_age_min=brief.audience_age_min,
                        audience_age_max=brief.audience_age_max,
                        audience_countries=brief.audience_countries,
                        audience_cities=brief.audience_cities,
                        budget_usd=brief.budget_usd,
                        tone=brief.tone,
                        platforms=brief.platforms,
                    ),
                    created_by=user.id,
                )
                await enqueue_discovery_run(str(run["id"]))
                ai_response = ai_response.copy()
                ai_response["discovery_run_id"] = str(run["id"])
                assistant_content = (
                    "Estoy buscando candidatos en Instagram, TikTok y YouTube "
                    "basado en tu brief. Te aviso cuando termine la búsqueda."
                )
            except Exception as e:
                assistant_content = (
                    f"Error al iniciar la búsqueda: {e}. "
                    "Intenta de nuevo o contacta al administrador."
                )

    assistant_record = await supabase_rest.insert(
        table="discovery_messages",
        values={
            "conversation_id": str(conversation_id),
            "role": "assistant",
            "content": assistant_content,
            "tool_calls": None,
            "tool_results": None,
            "cost_usd": 0.0,
            "latency_ms": 0,
        },
        returning="representation",
    )

    await supabase_rest.update(
        table="discovery_conversations",
        filters=[f"id=eq.{conversation_id}"],
        values={
            "last_message_at": "now()",
            "current_step": ai_response.get("step", "brief"),
            "discovery_run_id": ai_response.get("discovery_run_id"),
        },
    )

    return {
        "user_message": user_message_record,
        "assistant_message": assistant_record,
        "candidates": ai_response.get("candidates", []),
        "run_summary": ai_response.get("run_summary"),
        "discovery_run_id": ai_response.get("discovery_run_id"),
    }


# ---- Direct Search (no chat) ----

@router.post("/search", response_model=DiscoveryRunResponse)
async def create_discovery_run(body: DiscoverySearchRequest, user: CurrentUserDep):
    """Crea y ejecuta un discovery_run sin chat conversacional."""
    from discovery.memory import conversation_memory

    from app.core.worker_enqueuer import enqueue_discovery_run

    run = await conversation_memory.launch_discovery_run(
        brief=body,
        created_by=user.id,
    )

    await enqueue_discovery_run(str(run["id"]))

    return DiscoveryRunResponse(
        id=run["id"],
        status=DiscoveryRunStatus.PENDING,
        total_candidates=0,
        accepted=0,
        actual_cost_usd=None,
        error=None,
        started_at=None,
        completed_at=None,
        created_at=run["created_at"],
    )


@router.post("/enrich-influencers", response_model=EnrichResponse)
async def enrich_influencers(body: EnrichRequest, user: CurrentUserDep):
    """Enriquece perfiles de influencers con datos reales de Instagram via Apify.

    Si `influencer_ids` esta vacio y `all_active=True`, enriquece todos los
    influencers activos. De lo contrario, solo los IDs especificados.
    """
    from discovery.tools import apify_client

    filters: list[str] = ["status=eq.active"]
    if body.influencer_ids:
        id_list = ",".join(f'"{i}"' for i in body.influencer_ids)
        filters.append(f"id=in.({id_list})")

    influencers = await supabase_rest.select(
        table="influencers",
        select="id,full_name,primary_handle",
        filters=filters,
        limit=100,
    )

    if not influencers:
        return EnrichResponse(total=0, enriched=0, failed=0, cost_usd=0.0, results=[])

    handles = [
        {"id": str(inf["id"]), "handle": str(inf.get("primary_handle", "")).lstrip("@")}
        for inf in influencers
        if inf.get("primary_handle")
    ]

    if not handles:
        return EnrichResponse(total=len(influencers), enriched=0, failed=len(influencers), cost_usd=0.0, results=[])

    enriched_map: dict[str, dict] = {}
    results: list[EnrichResult] = []
    enriched_count = 0
    failed_count = 0
    total_cost = 0.0

    batch_size = 5
    for i in range(0, len(handles), batch_size):
        batch = handles[i:i + batch_size]
        usernames = [h["handle"] for h in batch]

        try:
            profiles = await apify_client.search_instagram_profiles_batch(usernames)
            if profiles is None:
                for h in batch:
                    results.append(EnrichResult(
                        influencer_id=h["id"],
                        handle=h["handle"],
                        success=False,
                        error="Apify returned no data (profile not found or API unavailable)",
                    ))
                    failed_count += 1
                continue
            for profile in profiles:
                username = profile.get("username", "")
                matched = next((h for h in batch if h["handle"].lower() == username.lower()), None)
                if not matched:
                    matched = next((h for h in handles if h["handle"].lower() == username.lower()), None)
                if matched:
                    followers = profile.get("followersCount") or profile.get("followers_count")
                    following = profile.get("followsCount") or profile.get("follows_count")
                    posts_count = profile.get("postsCount") or profile.get("posts_count")
                    avg_likes = profile.get("avgLikes") or profile.get("avg_likes")
                    avg_comments = profile.get("avgComments") or profile.get("avg_comments")
                    er = profile.get("avgLikesPercent") or profile.get("avg_likes_percent")

                    if followers and followers > 0 and er is None:
                        if avg_likes and avg_comments:
                            er = (avg_likes + avg_comments) / followers
                        elif avg_likes:
                            er = avg_likes / followers

                    enriched_map[matched["id"]] = {
                        "followers": followers,
                        "following": following,
                        "posts_count": posts_count,
                        "avg_likes": avg_likes,
                        "avg_comments": avg_comments,
                        "engagement_rate": round(er, 6) if er is not None else None,
                        "audience_credibility": (
                            50 + (20 if profile.get("isVerified") else 0) + (15 if profile.get("isBusinessAccount") else 0)
                        ),
                        "profile_pic_url": profile.get("profilePicUrl") or profile.get("profile_pic_url"),
                        "bio": profile.get("biography") or profile.get("bio", ""),
                        "platform": "instagram",
                    }
        except Exception as e:
            for h in batch:
                results.append(EnrichResult(
                    influencer_id=h["id"],
                    handle=h["handle"],
                    success=False,
                    error=str(e),
                ))
                failed_count += 1

    for inf in influencers:
        inf_id = str(inf["id"])
        if inf_id in enriched_map:
            updates = enriched_map[inf_id]
            updates["enriched_at"] = "now()"
            try:
                await supabase_rest.update(
                    table="influencers",
                    filters=[f"id=eq.{inf_id}"],
                    values=updates,
                )
                results.append(EnrichResult(
                    influencer_id=inf_id,
                    handle=str(inf.get("primary_handle", "")),
                    success=True,
                    followers=updates.get("followers"),
                    engagement_rate=updates.get("engagement_rate"),
                ))
                enriched_count += 1
            except Exception as e:
                results.append(EnrichResult(
                    influencer_id=inf_id,
                    handle=str(inf.get("primary_handle", "")),
                    success=False,
                    error=str(e),
                ))
                failed_count += 1
        else:
            if not any(r.influencer_id == inf_id for r in results):
                results.append(EnrichResult(
                    influencer_id=inf_id,
                    handle=str(inf.get("primary_handle", "")),
                    success=False,
                    error="No se encontraron datos en Apify",
                ))
                failed_count += 1

    apify_cost = enriched_count * 0.0002
    total_cost += apify_cost

    with contextlib.suppress(Exception):
        await supabase_rest.insert("api_costs", {
            "provider": "apify",
            "cost_usd": apify_cost,
            "request_count": enriched_count,
            "description": f"enrich_influencers: {enriched_count} profiles",
        })

    return EnrichResponse(
        total=len(influencers),
        enriched=enriched_count,
        failed=failed_count,
        cost_usd=round(total_cost, 6),
        results=results,
    )


@router.get("/runs")
async def list_discovery_runs(limit: int = 20, offset: int = 0):
    """Lista todos los runs de búsqueda paginados."""
    results = await supabase_rest.select(
        table="discovery_runs",
        select="id,status,total_candidates,accepted,actual_cost_usd,error,started_at,completed_at,created_at,metadata",
        order="created_at.desc",
        limit=limit,
        offset=offset,
    )
    return results


@router.get("/runs/{run_id}", response_model=DiscoveryRunResponse)
async def get_discovery_run(run_id: UUID):
    """Obtiene el estado de un run de búsqueda."""
    result = await supabase_rest.select_one(
        table="discovery_runs",
        select="id,status,total_candidates,accepted,actual_cost_usd,error,started_at,completed_at,created_at,metadata",
        filters=[f"id=eq.{run_id}"],
    )

    if not result:
        raise HTTPException(status_code=404, detail="Run not found")

    return DiscoveryRunResponse(**result)


@router.get("/runs/{run_id}/candidates")
async def list_run_candidates(
    run_id: UUID,
    status_filter: str | None = None,
    min_score: float | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """Lista candidatos de un run con filtros."""
    filters = [f"run_id=eq.{run_id}"]
    if status_filter:
        filters.append(f"status=eq.{status_filter}")
    if min_score is not None:
        filters.append(f"match_score=gte.{min_score}")

    return await supabase_rest.select(
        table="discovery_candidates",
        select="id,platform,handle,full_name,followers,engagement_rate,match_score,niche_relevance,geo_relevance,audience_relevance,content_quality,status,estimated_cost,expected_reach,expected_engagement,rationale,country,city,avatar_url",
        filters=filters,
        order="match_score.desc",
        limit=limit,
        offset=offset,
    )


# ---- Candidate management ----

@router.post("/candidates/{candidate_id}/save")
async def save_candidate(candidate_id: UUID, user: CurrentUserDep):
    """Convierte un discovery_candidate a influencer real."""
    candidate = await supabase_rest.select_one(
        table="discovery_candidates",
        select="*",
        filters=[f"id=eq.{candidate_id}"],
    )

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    influencer = await supabase_rest.insert(
        table="influencers",
        values={
            "full_name": candidate.get("full_name", ""),
            "email": candidate.get("contact_email", ""),
            "phone": candidate.get("contact_phone", ""),
            "country": candidate.get("country", "VE"),
            "city": candidate.get("city", ""),
            "primary_tier": "MICRO",
            "primary_handle": candidate.get("handle", ""),
            "avatar_url": candidate.get("avatar_url", ""),
            "bio": candidate.get("bio", ""),
            "is_discoverable": True,
            "discovered_at": "now()",
            "discovery_query": "",
            "discovery_confidence": candidate.get("match_score", 0),
            "metadata": {"discovery_candidate_id": str(candidate_id)},
        },
        returning="representation",
    )

    await supabase_rest.update(
        table="discovery_candidates",
        filters=[f"id=eq.{candidate_id}"],
        values={
            "status": "saved",
            "saved_as_influencer_id": influencer["id"],
        },
    )

    return {"influencer_id": influencer["id"], "candidate_id": str(candidate_id)}


@router.post("/candidates/{candidate_id}/dismiss")
async def dismiss_candidate(candidate_id: UUID, reason: str | None = None, user: CurrentUserDep = None):
    """Descarta un candidato."""
    await supabase_rest.update(
        table="discovery_candidates",
        filters=[f"id=eq.{candidate_id}"],
        values={
            "status": "dismissed",
            "metadata": {"dismiss_reason": reason} if reason else {},
        },
    )
    return {"candidate_id": str(candidate_id), "status": "dismissed"}


# ---- Costs ----

@router.get("/costs")
async def get_api_costs(
    provider: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    group_by: str = "provider",
):
    """Retorna costos agregados de APIs externas."""
    filters = []
    if provider:
        filters.append(f"provider=eq.{provider}")

    result = await supabase_rest.select(
        table="api_costs",
        select="provider,cost_usd,request_count",
        filters=filters,
        order="cost_usd.desc",
        limit=50,
    )

    return result


@router.get("/metrics")
async def get_discovery_metrics():
    """Dashboard de métricas del módulo de discovery."""
    runs = await supabase_rest.select(
        table="discovery_runs",
        select="id,status,total_candidates,accepted,actual_cost_usd,created_at",
        filters=[],
        order="created_at.desc",
        limit=100,
    )

    total_runs = len(runs)
    completed = sum(1 for r in runs if r.get("status") == "completed")
    total_candidates = sum(r.get("total_candidates", 0) for r in runs)
    total_saved = sum(r.get("accepted", 0) for r in runs)
    avg_cost = sum(r.get("actual_cost_usd", 0) or 0 for r in runs) / max(total_runs, 1)

    return {
        "total_runs": total_runs,
        "completed_runs": completed,
        "total_candidates_found": total_candidates,
        "total_saved_as_influencers": total_saved,
        "avg_cost_per_run": round(avg_cost, 4),
    }
