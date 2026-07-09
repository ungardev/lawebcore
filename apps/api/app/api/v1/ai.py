"""AI endpoints: chat (RAG), generation, embeddings."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import time
import structlog

from app.core.db import get_db
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