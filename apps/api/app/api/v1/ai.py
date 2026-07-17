"""AI endpoints: chat (RAG), generation, embeddings, indexing."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import time
import structlog

from shared_core import get_db
from app.core.security import CurrentUserDep
from app.schemas import AIChatRequest, AIChatResponse, AIGenerateRequest
from app.services.ai_service import AIService

router = APIRouter()
logger = structlog.get_logger(__name__)
ai_service = AIService()


@router.post("/chat", response_model=AIChatResponse, summary="Chat with La Web Core AI (RAG)")
async def chat(payload: AIChatRequest, user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    start = time.time()
    try:
        result = await ai_service.chat(
            user_id=user.id,
            conversation_id=payload.conversation_id,
            message=payload.message,
            context_type=payload.context_type,
            context_id=payload.context_id,
            db=db,
        )
        latency_ms = int((time.time() - start) * 1000)
        return AIChatResponse(
            conversation_id=result["conversation_id"],
            message=result["message"],
            sources=result.get("sources", []),
            tokens_used=result.get("tokens_used", 0),
            latency_ms=latency_ms,
            used_rag=result.get("used_rag", False),
        )
    except Exception as e:
        logger.error("ai_chat_failed", error=str(e), user_id=str(user.id))
        raise HTTPException(status_code=500, detail=f"AI chat failed: {e}")


@router.post("/generate", summary="Generate content via AI (brief, post-mortem, etc.)")
async def generate(payload: AIGenerateRequest, user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    try:
        result = await ai_service.generate(
            prompt_code=payload.prompt_code,
            campaign_id=payload.campaign_id,
            extra_context=payload.extra_context,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("ai_generate_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"AI generate failed: {e}")


@router.get("/conversations")
async def list_conversations(user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    sql = text("""
        SELECT id, title, context_type, context_id, created_at, updated_at
        FROM ai_conversations
        WHERE user_id = :uid AND is_archived = FALSE
        ORDER BY updated_at DESC LIMIT 50
    """)
    result = await db.execute(sql, {"uid": str(user.id)})
    return [dict(r) for r in result.mappings().all()]


@router.post("/index/reindex", summary="Re-index P.I.A.R. data into vector store")
async def reindex_piar(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None,
    campaign_id: str | None = None,
    full: bool = False,
) -> dict:
    """
    Re-index P.I.A.R. data into the vector store.

    - full=true: re-index ALL publications (up to 1000) + benchmarks
    - campaign_id: re-index only publications for that campaign
    - neither: only index recent publications (last 100)
    """
    try:
        from app.ai.indexer import reindex_all_piar, index_publicaciones_by_campaign
    except ImportError as e:
        logger.error("indexer_import_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Indexer not available")

    if campaign_id:
        try:
            count = await index_publicaciones_by_campaign(db, campaign_id)
            await db.commit()
            return {"status": "ok", "indexed": count, "scope": f"campaign:{campaign_id}"}
        except Exception as e:
            logger.error("reindex_campaign_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    if full:
        try:
            counts = await reindex_all_piar(db)
            await db.commit()
            return {"status": "ok", "indexed": counts, "scope": "full"}
        except Exception as e:
            logger.error("reindex_full_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "message": "Specify campaign_id or full=true"}


@router.get("/sources/{message_id}", summary="Get sources for a chat message")
async def get_message_sources(
    message_id: str,
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Get the sources (chunks) used for a specific assistant message."""
    sql = text("""
        SELECT m.content, m.metadata
        FROM ai_messages m
        JOIN ai_conversations c ON c.id = m.conversation_id
        WHERE m.id = :mid AND c.user_id = :uid
        LIMIT 1
    """)
    result = await db.execute(sql, {"mid": message_id, "uid": str(user.id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"content": row["content"], "metadata": dict(row["metadata"] or {})}