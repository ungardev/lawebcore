"""API v1 router para el módulo de Discovery."""

import uuid as uuidlib
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import CurrentUserDep
from app.core.supabase_rest import supabase_rest
from app.discovery.orchestrator import orchestrator
from app.discovery.schemas import (
    BriefStructured,
    ConversationResponse,
    ConversationStep,
    DiscoveryConversationCreate,
    DiscoveryRunResponse,
    DiscoveryRunStatus,
    DiscoverySearchRequest,
    MessageCreate,
    MessageResponse,
)

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
    from app.discovery.memory import conversation_memory

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
    from app.discovery.memory import conversation_memory

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
    from app.discovery.memory import conversation_memory

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
    }


# ---- Direct Search (no chat) ----

@router.post("/search", response_model=DiscoveryRunResponse)
async def create_discovery_run(body: DiscoverySearchRequest, user: CurrentUserDep):
    """Crea y ejecuta un discovery_run sin chat conversacional."""
    from app.discovery.memory import conversation_memory
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


@router.get("/runs/{run_id}", response_model=DiscoveryRunResponse)
async def get_discovery_run(run_id: UUID):
    """Obtiene el estado de un run de búsqueda."""
    result = await supabase_rest.select_one(
        table="discovery_runs",
        select="id,status,total_candidates,accepted,actual_cost_usd,error,started_at,completed_at,created_at",
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
