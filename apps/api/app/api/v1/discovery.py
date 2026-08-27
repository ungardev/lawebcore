"""API v1 router para el módulo de Discovery."""

import contextlib
import uuid as uuidlib
from datetime import UTC, datetime
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
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from shared_core import railway_pg

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


# ---- Candidate serialization helpers ----

def _tier_from_followers(followers: int | float | None) -> str | None:
    if not followers:
        return None
    f = int(followers)
    if f < 10_000:
        return "NANO"
    if f < 100_000:
        return "MICRO"
    if f < 500_000:
        return "MID"
    return "MACRO"


_TIENDA_PATTERNS = [
    "tienda", "shop", "ventas", "pedidos", "catálogo",
    "mayor y detal", "envíos", "mercado libre", "delivery",
    "comprar aquí", "adquirir", "whatsapp", "telf", "teléfono",
]


def _is_tienda(bio: str | None) -> bool:
    if not bio:
        return False
    lower = bio.lower()
    return any(p in lower for p in _TIENDA_PATTERNS)


def _build_fallback_url(c: dict) -> str | None:
    url = c.get("url")
    if url:
        return url
    handle = c.get("handle") or ""
    platform = c.get("platform") or ""
    if not handle:
        return None
    if platform == "tiktok":
        return f"https://tiktok.com/@{handle}"
    if platform == "youtube":
        return f"https://youtube.com/@{handle}"
    if platform == "instagram":
        return f"https://instagram.com/{handle}"
    return None


def _serialize_candidate(c: dict) -> dict:
    followers = c.get("followers") or 0
    bio = c.get("bio") or c.get("biography") or ""
    tier = c.get("tier") or _tier_from_followers(followers)
    engagement_rate = c.get("engagement_rate")
    if engagement_rate is not None:
        engagement_rate = round(float(engagement_rate), 4)
    is_tienda = c.get("is_tienda")
    if is_tienda is None:
        is_tienda = _is_tienda(bio)
    raw = c.get("raw_payload") or {}
    if isinstance(raw, str):
        try:
            import json
            raw = json.loads(raw)
        except Exception:
            raw = {}
    return {
        "id": str(c.get("id", "")),
        "platform": c.get("platform", "instagram"),
        "handle": str(c.get("handle", "")),
        "url": c.get("url") or _build_fallback_url(c),
        "full_name": c.get("full_name") or c.get("fullName"),
        "avatar_url": c.get("avatar_url") or c.get("profilePicUrl"),
        "followers": int(followers) if followers else 0,
        "following": int(c.get("following") or 0),
        "posts_count": int(c.get("posts_count") or 0),
        "avg_likes": int(c.get("avg_likes")) if c.get("avg_likes") is not None else None,
        "avg_comments": int(c.get("avg_comments")) if c.get("avg_comments") is not None else None,
        "avg_views": int(c.get("avg_views")) if c.get("avg_views") is not None else None,
        "engagement_rate": engagement_rate,
        "audience_credibility": round(float(c.get("audience_credibility") or 0), 2),
        "audience_quality": round(float(c.get("audience_quality") or 0), 2),
        "is_verified": raw.get("is_verified") if isinstance(raw, dict) else False,
        "is_creator": raw.get("is_creator") if isinstance(raw, dict) else False,
        "creator_signals": raw.get("creator_signals") if isinstance(raw, dict) else 0,
        "match_score": round(float(c.get("match_score") or 0), 1),
        "tier": tier,
        "niche_relevance": round(float(c.get("niche_relevance") or 0), 2),
        "geo_relevance": round(float(c.get("geo_relevance") or 0), 2),
        "audience_relevance": round(float(c.get("audience_relevance") or 0), 2),
        "content_quality": round(float(c.get("content_quality") or 0), 2),
        "status": c.get("status", "new"),
        "expected_reach": int(c.get("expected_reach") or 0),
        "expected_engagement": int(c.get("expected_engagement") or 0),
        "rationale": c.get("rationale"),
        "country": c.get("country"),
        "city": c.get("city"),
        "bio": bio[:300] if bio else None,
        "is_tienda": is_tienda,
        "raw_payload": raw,
    }


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
    from discovery.memory import _generate_conversation_title, conversation_memory

    conversation_id = uuidlib.uuid4()
    result = await orchestrator.create_conversation(
        conversation_id=conversation_id,
        initial_brief=body.initial_brief,
    )

    orchestrator_step = result.get("step", ConversationStep.START.value)
    assistant_content = result.get("message", "")

    brief_data = result.get("brief")
    conv_title = _generate_conversation_title(brief_data) if brief_data else None
    await conversation_memory.save_conversation(
        conversation_id=conversation_id,
        user_id=user.id,
        bu_id=body.bu_id,
        step=orchestrator_step,
        title=conv_title,
    )

    if body.initial_brief:
        await railway_pg.insert(
            table="discovery_messages",
            values={
                "conversation_id": str(conversation_id),
                "role": "user",
                "content": body.initial_brief,
            },
            returning="representation",
        )

    if assistant_content:
        await railway_pg.insert(
            table="discovery_messages",
            values={
                "conversation_id": str(conversation_id),
                "role": "assistant",
                "content": assistant_content,
                "reasoning": result.get("reasoning"),
                "tool_calls": result.get("tool_calls"),
                "tool_results": result.get("tool_results"),
                "cost_usd": result.get("cost_usd", 0.0),
                "latency_ms": result.get("latency_ms", 0),
            },
            returning="representation",
        )

    msg_count = (1 if body.initial_brief else 0) + (1 if assistant_content else 0)
    await conversation_memory.update_conversation(
        conversation_id=conversation_id,
        updates={
            "accumulated_brief": result.get("accumulated_brief", ""),
            "parsed_brief_json": result.get("brief"),
            "message_count": msg_count,
        },
    )

    return ConversationResponse(
        id=conversation_id,
        current_step=ConversationStep(orchestrator_step),
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

    result = await railway_pg.select(
        table="discovery_conversations",
        select="id,user_id,current_step,status,message_count,started_at,last_message_at,title",
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

    messages = await railway_pg.select(
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

    user_message_record = await railway_pg.insert(
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
    reasoning = ai_response.get("reasoning")
    tool_calls = ai_response.get("tool_calls")
    tool_results = ai_response.get("tool_results")
    cost_usd = ai_response.get("cost_usd", 0.0)
    latency_ms = ai_response.get("latency_ms", 0)
    discovery_run_id: str | None = None

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
                        hashtags=brief.hashtags,
                        audience_gender=brief.audience_gender,
                        audience_age_min=brief.audience_age_min,
                        audience_age_max=brief.audience_age_max,
                        audience_countries=brief.audience_countries,
                        audience_cities=brief.audience_cities,
                        audience_states=brief.audience_states,
                        tone=brief.tone,
                        platforms=brief.platforms,
                        exclude_handles=brief.exclude_handles if hasattr(brief, "exclude_handles") else [],
                        discovery_mode=getattr(brief, "discovery_mode", "auto"),
                        handles_to_analyze=getattr(brief, "handles_to_analyze", []),
                    ),
                    created_by=user.id,
                )
                await enqueue_discovery_run(str(run["id"]))
                discovery_run_id = str(run["id"])
                platform_text = "Instagram"
                if len(brief.platforms) == 2:
                    platform_text = f"Instagram y {brief.platforms[1].replace('instagram', '').replace('tiktok', 'TikTok').replace('youtube', 'YouTube')}"
                elif len(brief.platforms) > 2:
                    platform_text = "Instagram, TikTok y YouTube"
                elif brief.platforms and brief.platforms[0] != "instagram":
                    platform_text = brief.platforms[0].replace("tiktok", "TikTok").replace("youtube", "YouTube").replace("instagram", "Instagram")

                product_text = f"'{brief.product_name}'" if brief.product_name else "tu producto"
                location_text = ""
                if brief.audience_cities and len(brief.audience_cities) > 0:
                    location_text = f" en {', '.join(brief.audience_cities[:2])}"
                elif brief.audience_countries and len(brief.audience_countries) > 0:
                    location_text = f" en {', '.join(brief.audience_countries[:2])}"

                assistant_content = (
                    f"Perfecto. Voy a buscar candidatos en {platform_text} para {product_text}{location_text}. "
                    "Te aviso cuando tenga resultados."
                )
            except Exception as e:
                assistant_content = (
                    f"Error al iniciar la búsqueda: {e}. "
                    "Intenta de nuevo o contacta al administrador."
                )

    assistant_record = await railway_pg.insert(
        table="discovery_messages",
        values={
            "conversation_id": str(conversation_id),
            "role": "assistant",
            "content": assistant_content,
            "reasoning": reasoning,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
        },
        returning="representation",
    )

    await railway_pg.update(
        table="discovery_conversations",
        filters=[f"id=eq.{conversation_id}"],
        values={
            "last_message_at": datetime.now(UTC),
            "current_step": ai_response.get("step", "brief"),
            "discovery_run_id": discovery_run_id,
        },
    )

    return {
        "user_message": user_message_record,
        "assistant_message": assistant_record,
        "candidates": ai_response.get("candidates", []),
        "run_summary": ai_response.get("run_summary"),
        "discovery_run_id": discovery_run_id,
    }


# ---- Brief Upload (PDF/TXT/CSV → Super Brief) ----

@router.post("/lens/discovery/upload-brief")
async def upload_brief_from_file(user: CurrentUserDep, file: UploadFile = File(...)):
    """Parse a PDF, TXT or CSV file and extract a super-enriched BriefStructured JSON."""
    import csv
    import io
    import json as jsonlib

    from pypdf import PdfReader

    ALLOWED_TYPES = {  # noqa: N806
        "application/pdf": "pdf",
        "text/plain": "txt",
        "text/csv": "csv",
        "text/markdown": "md",
        "application/json": "json",
    }
    MAX_SIZE = 5 * 1024 * 1024  # noqa: N806

    content_type = file.content_type or ""
    file_ext = ALLOWED_TYPES.get(content_type)
    if not file_ext and file.filename:
        ext = file.filename.lower().split(".")[-1]
        file_ext = {"pdf": "pdf", "txt": "txt", "csv": "csv", "md": "md", "json": "json"}.get(ext)

    if not file_ext:
        raise HTTPException(
            status_code=415,
detail=f"Tipo de archivo no soportado: {content_type}. Usa PDF, TXT, CSV, MD o JSON.",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Archivo demasiado grande. Máximo 5MB. Recibido: {len(contents) / 1024 / 1024:.1f}MB",
        )

    text = ""
    file_meta = {
        "file_name": file.filename or "unknown",
        "file_size_bytes": len(contents),
        "mime_type": content_type or "application/octet-stream",
    }

    if file_ext == "pdf":
        try:
            reader = PdfReader(io.BytesIO(contents))
            file_meta["pages"] = len(reader.pages)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Error leyendo PDF: {e}")  # noqa: B904
        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail="No se pudo extraer texto del PDF. Si tiene imágenes escaneadas, conviértelas a texto primero.",
            )

    elif file_ext == "csv":
        try:
            decoded = contents.decode("utf-8")
            reader = csv.reader(io.StringIO(decoded))
            for row in reader:
                text += " ".join(row) + "\n"
            file_meta["rows"] = len(text.splitlines())
        except UnicodeDecodeError:
            contents = await file.read()
            decoded = contents.decode("latin-1")
            reader = csv.reader(io.StringIO(decoded))
            for row in reader:
                text += " ".join(row) + "\n"
        if not text.strip():
            raise HTTPException(status_code=422, detail="CSV vacío o no pudo leerse.")

    elif file_ext in ("txt", "md", "json"):
        try:
            text = contents.decode("utf-8")
        except UnicodeDecodeError:
            text = contents.decode("latin-1")
        if file_ext == "json":
            try:
                data = jsonlib.loads(text)
                text = jsonlib.dumps(data, indent=2, ensure_ascii=False)
            except jsonlib.JSONDecodeError:
                pass

    if not text.strip():
        raise HTTPException(status_code=422, detail="No se pudo extraer texto del archivo.")

    text = text[:50000]

    from discovery.brief_parser import brief_parser_agent

    brief = await brief_parser_agent.parse_from_document(text=text, file_meta=file_meta)

    return {
        "brief": brief.model_dump(mode="json"),
        "file_name": file_meta["file_name"],
        "text_length": len(text),
    }


# ---- Direct Search (no chat) ----

@router.post("/search", response_model=DiscoveryRunResponse)
async def create_discovery_run(body: DiscoverySearchRequest, user: CurrentUserDep):
    """Crea y ejecuta un discovery_run sin chat conversacional."""
    if not body.product_name:
        raise HTTPException(status_code=400, detail="product_name es obligatorio")
    if not body.niches:
        raise HTTPException(status_code=400, detail="niches es obligatorio")

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


class AnalyzeSelectedRequest(BaseModel):
    run_id: UUID
    handles_to_analyze: list[str]


@router.post("/analyze-selected", response_model=DiscoveryRunResponse)
async def analyze_selected(body: AnalyzeSelectedRequest, user: CurrentUserDep):
    """Crea un run en modo 'analyze' para enriquecer handles seleccionados en modo 'explore'.

    El run padre (explore) ya descubrió los handles. Esta operación los enriquece
    y scorea con los datos reales de HikerAPI.
    """
    from discovery.memory import conversation_memory

    from app.core.worker_enqueuer import enqueue_discovery_run

    parent_run = await railway_pg.select_one(
        table="discovery_runs",
        select="*",
        filters=[f"id=eq.{body.run_id}"],
    )
    if not parent_run:
        raise HTTPException(status_code=404, detail="Run padre no encontrado")

    brief_parsed = parent_run.get("brief_parsed", {})
    if isinstance(brief_parsed, str):
        import json
        brief_parsed = json.loads(brief_parsed)

    brief_parsed["discovery_mode"] = "analyze"
    brief_parsed["handles_to_analyze"] = body.handles_to_analyze
    brief_parsed["parent_run_id"] = str(body.run_id)

    from discovery.schemas import DiscoverySearchRequest
    brief = DiscoverySearchRequest(**brief_parsed)

    run = await conversation_memory.launch_discovery_run(
        brief=brief,
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

    influencers = await railway_pg.select(
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

    batch_size = 10
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
            updates["enriched_at"] = datetime.now(UTC)
            try:
                await railway_pg.update(
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
        await railway_pg.insert("api_costs", {
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
    results = await railway_pg.select(
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
    result = await railway_pg.select_one(
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

    rows = await railway_pg.select(
        table="discovery_candidates",
        select="*",
        filters=filters,
        order="match_score.desc",
        limit=limit,
        offset=offset,
    )
    return [_serialize_candidate(r) for r in rows]


@router.get("/runs/{run_id}/proposal.csv")
async def download_proposal_csv(run_id: UUID):
    """Descarga propuesta CSV con los candidatos guardados (top 10)."""
    from fastapi.responses import StreamingResponse

    from app.services.proposal_generator import generate_proposal_csv

    candidates = await railway_pg.select(
        table="discovery_candidates",
        select="*",
        filters=[f"run_id=eq.{run_id}", "status=eq.saved"],
        order="match_score.desc",
        limit=10,
    )

    if not candidates:
        raise HTTPException(
            status_code=400,
            detail="No hay candidatos guardados. Guarda al menos 1 candidato primero.",
        )

    run = await railway_pg.select_one(
        table="discovery_runs",
        select="product_name",
        filters=[f"id=eq.{run_id}"],
    )
    product_name = (run.get("product_name") or "Influencer Proposal") if run else "Influencer Proposal"

    csv_bytes = generate_proposal_csv(
        [_serialize_candidate(c) for c in candidates],
        product_name=product_name,
    )

    filename = f"propuesta_{str(run_id)[:8]}_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---- Candidate management ----


def _derive_tier(followers: int | None) -> str | None:
    """Deriva el tier desde follower_count.

    Alineado con TIER_BENCHMARKS en result_ranker.py:6-16.
    9 sub-tiers: NANO_BAJO, NANO_ALTO, MICRO_BAJO, MICRO_MEDIO,
    MICRO_ALTO, MID_BAJO, MID_ALTO, MACRO_BAJO, MACRO_ALTO.
    """
    if followers is None:
        return None
    if followers < 2_000:
        return "NANO_BAJO"
    if followers < 10_000:
        return "NANO_ALTO"
    if followers < 30_000:
        return "MICRO_BAJO"
    if followers < 100_000:
        return "MICRO_MEDIO"
    if followers < 500_000:
        return "MICRO_ALTO"
    if followers < 1_000_000:
        return "MID_BAJO"
    if followers < 5_000_000:
        return "MID_ALTO"
    if followers < 10_000_000:
        return "MACRO_BAJO"
    return "MACRO_ALTO"


@router.post("/candidates/{candidate_id}/save")
async def save_candidate(candidate_id: UUID, user: CurrentUserDep):
    """Convierte un discovery_candidate a influencer real."""
    candidate = await railway_pg.select_one(
        table="discovery_candidates",
        select="*",
        filters=[f"id=eq.{candidate_id}"],
    )

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    follower_count = candidate.get("followers") or 0
    handle = candidate.get("handle", "")

    existing = await railway_pg.select_one(
        table="influencers",
        select="id",
        filters=[f"primary_handle=eq.{handle}"],
    )

    if existing:
        influencer_id = existing["id"]
        await railway_pg.update(
            table="influencers",
            filters=[f"id=eq.{influencer_id}"],
            values={
                "full_name": candidate.get("full_name", ""),
                "country": candidate.get("country", "VE"),
                "city": candidate.get("city", ""),
                "primary_tier": _derive_tier(follower_count),
                "avatar_url": candidate.get("avatar_url", ""),
                "bio": candidate.get("bio", ""),
                "discovery_query": candidate.get("discovery_query", ""),
                "discovery_confidence": candidate.get("match_score", 0),
                "followers": follower_count,
            },
        )
        influencer = {"id": influencer_id}
    else:
        influencer = await railway_pg.insert(
            table="influencers",
            values={
                "full_name": candidate.get("full_name", ""),
                "email": candidate.get("contact_email", ""),
                "phone": candidate.get("contact_phone", ""),
                "country": candidate.get("country", "VE"),
                "city": candidate.get("city", ""),
                "primary_tier": _derive_tier(follower_count),
                "primary_handle": handle,
                "avatar_url": candidate.get("avatar_url", ""),
                "bio": candidate.get("bio", ""),
                "is_discoverable": True,
                "discovered_at": datetime.now(UTC),
                "discovery_query": candidate.get("discovery_query", ""),
                "discovery_confidence": candidate.get("match_score", 0),
                "followers": follower_count,
                "metadata": {"discovery_candidate_id": str(candidate_id)},
            },
            returning="representation",
        )

    await railway_pg.update(
        table="discovery_candidates",
        filters=[f"id=eq.{candidate_id}"],
        values={
            "status": "saved",
            "saved_as_influencer_id": influencer["id"],
        },
    )

    run_id = candidate.get("run_id")
    if run_id:
        await railway_pg.execute(
            "UPDATE discovery_runs SET accepted = accepted + 1 WHERE id = $1",
            [str(run_id)],
        )

    influencer_id = influencer["id"]

    social_account_rows = await railway_pg.upsert(
        table="influencer_social_accounts",
        values={
            "influencer_id": influencer_id,
            "platform": "instagram",
            "handle": handle,
            "url": f"https://instagram.com/{handle}" if handle else None,
            "is_primary": True,
        },
        on_conflict=["platform", "handle"],
        returning="representation",
    )
    social_account_id = social_account_rows[0]["id"] if social_account_rows else None

    await railway_pg.upsert(
        table="influencer_metrics_snapshot",
        values={
            "influencer_id": influencer_id,
            "social_account_id": social_account_id,
            "snapshot_date": datetime.now(UTC).date(),
            "follower_count": follower_count,
            "engagement_rate": candidate.get("engagement_rate"),
            "avg_likes": candidate.get("avg_likes"),
            "raw_data": candidate.get("raw_payload", {}),
        },
        on_conflict=["influencer_id", "social_account_id", "snapshot_date", "source"],
        returning="representation",
    )

    return {"influencer_id": influencer_id, "candidate_id": str(candidate_id)}


@router.post("/candidates/{candidate_id}/dismiss")
async def dismiss_candidate(candidate_id: UUID, reason: str | None = None, user: CurrentUserDep = None):
    """Descarta un candidato."""
    await railway_pg.update(
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
    """Retorna costos agregados de APIs externas.

    Args:
        provider: Filtrar por proveedor (apify, deepseek).
        from_date: Fecha inicio ISO (YYYY-MM-DD).
        to_date: Fecha fin ISO (YYYY-MM-DD).
        group_by: 'provider' para resumen por proveedor,
                  'operation' para desglose completo por actor/operacion.
    """
    filters: list[str] = []
    if provider:
        filters.append(f"provider=eq.{provider}")
    if from_date:
        filters.append(f"occurred_at.gte.{from_date}T00:00:00Z")
    if to_date:
        filters.append(f"occurred_at.lte.{to_date}T23:59:59Z")

    rows = await railway_pg.select(
        table="api_costs",
        select="provider,operation,cost_usd,request_count,tokens_input,tokens_output",
        filters=filters,
        order="cost_usd.desc",
        limit=1000,
    )

    if not rows:
        return {"total_cost_usd": 0, "by_group": [], "details": []}

    if group_by == "provider":
        by_group: dict[str, dict] = {}
        for r in rows:
            key = r["provider"]
            if key not in by_group:
                by_group[key] = {
                    "provider": key,
                    "total_cost_usd": 0.0,
                    "total_requests": 0,
                    "tokens_input": 0,
                    "tokens_output": 0,
                }
            by_group[key]["total_cost_usd"] += float(r["cost_usd"] or 0)
            by_group[key]["total_requests"] += int(r["request_count"] or 0)
            by_group[key]["tokens_input"] += int(r["tokens_input"] or 0)
            by_group[key]["tokens_output"] += int(r["tokens_output"] or 0)
        groups = list(by_group.values())
    else:
        op_group: dict[tuple, dict] = {}
        for r in rows:
            key = (r["provider"], r["operation"])
            if key not in op_group:
                op_group[key] = {
                    "provider": r["provider"],
                    "operation": r["operation"],
                    "total_cost_usd": 0.0,
                    "total_requests": 0,
                    "tokens_input": 0,
                    "tokens_output": 0,
                }
            op_group[key]["total_cost_usd"] += float(r["cost_usd"] or 0)
            op_group[key]["total_requests"] += int(r["request_count"] or 0)
            op_group[key]["tokens_input"] += int(r["tokens_input"] or 0)
            op_group[key]["tokens_output"] += int(r["tokens_output"] or 0)
        groups = list(op_group.values())

    total = round(sum(float(r["cost_usd"] or 0) for r in rows), 6)
    return {
        "total_cost_usd": total,
        "by_group": groups,
        "count": len(rows),
    }


@router.get("/metrics")
async def get_discovery_metrics():
    """Dashboard de métricas del módulo de discovery."""
    runs = await railway_pg.select(
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
