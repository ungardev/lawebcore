"""AI Service - chat (RAG), generation, embeddings orchestration.

This service is the entry point for all AI features:
- Chat with RAG: retrieve relevant chunks from pgvector, build prompt, call LLM
- Generation: load prompt template, fill with campaign context, call LLM
- Embeddings: chunk a document, embed with OpenAI, store in pgvector
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ai.llm import get_llm
from app.ai.embeddings import embed_text

logger = structlog.get_logger(__name__)


class AIService:
    """Orchestrates all AI operations."""

    async def chat(
        self,
        user_id: UUID,
        conversation_id: UUID | None,
        message: str,
        context_type: str | None,
        context_id: UUID | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Process a chat message with RAG over the knowledge base."""
        # 1. Get or create conversation
        if conversation_id:
            conv_id = conversation_id
        else:
            conv_id = uuid4()
            await db.execute(
                text("""
                INSERT INTO ai_conversations (id, user_id, title, context_type, context_id, system_prompt_code)
                VALUES (:id, :uid, :title, :ctx_type, :ctx_id, 'rag_system_v1')
                """),
                {
                    "id": str(conv_id),
                    "uid": str(user_id),
                    "title": message[:80],
                    "ctx_type": context_type,
                    "ctx_id": str(context_id) if context_id else None,
                },
            )
            await db.commit()

        # 2. Persist user message
        await db.execute(
            text("INSERT INTO ai_messages (conversation_id, role, content) VALUES (:cid, 'user', :content)"),
            {"cid": str(conv_id), "content": message},
        )
        await db.commit()

        # 3. Embed the message and search relevant chunks
        try:
            query_embedding = await embed_text(message)
        except Exception as e:
            logger.warning("embedding_failed_fallback_to_keywords", error=str(e))
            query_embedding = None

        sources: list[dict] = []
        context_text = ""
        if query_embedding:
            try:
                rows = await db.execute(
                    text("""
                    SELECT id, document_id, content,
                           1 - (embedding <=> CAST(:emb AS vector)) AS similarity,
                           metadata
                    FROM document_chunks
                    WHERE embedding IS NOT NULL
                      AND 1 - (embedding <=> CAST(:emb AS vector)) > 0.7
                    ORDER BY embedding <=> CAST(:emb AS vector)
                    LIMIT 8
                    """),
                    {"emb": str(query_embedding)},
                )
                chunks = rows.mappings().all()
                context_text = "\n\n---\n\n".join(c["content"] for c in chunks)
                for c in chunks:
                    sources.append({
                        "chunk_id": str(c["id"]),
                        "document_id": str(c["document_id"]),
                        "similarity": float(c["similarity"]),
                        "excerpt": c["content"][:200],
                    })
            except Exception as e:
                logger.warning("vector_search_failed", error=str(e))

        # 4. Build prompt and call LLM
        system_prompt = (
            "Eres el asistente IA de La Web Core, la plataforma de gestión de campañas de "
            "marketing de influencers de La Web Figital Agency (Venezuela).\n\n"
            "REGLAS ESTRICTAS:\n"
            "1. Solo respondes con información de las fuentes proporcionadas en el contexto.\n"
            "2. Si ninguna fuente es relevante, responde: "
            '"No tengo información suficiente en la base de datos para responder esa pregunta."\n'
            "3. Cuando cites información de una fuente, usa el formato [ref:{tipo}:{id}] al final de la oración.\n"
            "4. Nunca inventas datos, métricas o nombres de influencers.\n"
            "5. Todos los números los presentas con formato legible (ej: 1.2M en vez de 1200000).\n"
            "6. Hablas en español profesional latinoamericano.\n"
            "7. Para consultas sobre 'mejor influencer', 'top creador', 'mayor ER', siempre operas "
            "sobre los datos disponibles en la base, no sobre conocimiento general."
        )
        user_prompt = (
            f"Contexto recuperado de la base de conocimiento:\n\n{context_text}\n\n"
            f"---\n\nPregunta del usuario: {message}\n\n"
            "Responde basándote EXCLUSIVAMENTE en el contexto de arriba. "
            "Cita cada afirmación con [ref:{tipo}:{id}]. "
            "Si no hay información relevante en el contexto, dilo claramente."
        )

        try:
            llm = get_llm(temperature=0.4)
            response = await llm.ainvoke([{"role": "system", "content": system_prompt},
                                           {"role": "user", "content": user_prompt}])
            answer_text = response.content if hasattr(response, "content") else str(response)
            tokens_used = 0
            if hasattr(response, "response_metadata"):
                usage = response.response_metadata.get("token_usage", {})
                tokens_used = usage.get("total_tokens", 0)
        except Exception as e:
            logger.error("llm_call_failed", error=str(e))
            answer_text = (
                "Disculpa, tuve un problema al procesar tu consulta con el modelo de IA. "
                "El equipo tecnico ha sido notificado. "
                "Por favor intenta de nuevo en unos momentos."
            )
            tokens_used = 0

        # 5. Persist assistant message
        await db.execute(
            text("""
            INSERT INTO ai_messages (conversation_id, role, content, model_provider, model_name)
            VALUES (:cid, 'assistant', :content, :prov, :model)
            """),
            {"cid": str(conv_id), "content": answer_text, "prov": settings.DEFAULT_LLM_PROVIDER, "model": settings.DEFAULT_LLM_MODEL},
        )
        await db.commit()

        return {
            "conversation_id": conv_id,
            "message": answer_text,
            "sources": sources,
            "tokens_used": tokens_used,
            "used_rag": bool(context_text),
        }

    async def generate(
        self,
        prompt_code: str,
        campaign_id: UUID,
        extra_context: dict,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Generate content using a named prompt template."""
        # Load prompt template
        prompt_row = (await db.execute(
            text("SELECT * FROM ai_prompts WHERE code = :code AND is_active = TRUE ORDER BY version DESC LIMIT 1"),
            {"code": prompt_code},
        )).mappings().first()
        if not prompt_row:
            raise ValueError(f"Prompt not found or inactive: {prompt_code}")

        # Load campaign context
        camp = (await db.execute(
            text("""
            SELECT c.*, cl.name AS client_name, b.name AS brand_name
            FROM campaigns c
            JOIN clients cl ON cl.id = c.client_id
            JOIN brands b ON b.id = c.brand_id
            WHERE c.id = :id
            """),
            {"id": str(campaign_id)},
        )).mappings().first()
        if not camp:
            raise ValueError(f"Campaign not found: {campaign_id}")

        # KPIs context
        kpis = (await db.execute(
            text("""
            SELECT kd.code, kd.name, ckv.value
            FROM campaign_kpi_values ckv
            JOIN kpi_definitions kd ON kd.id = ckv.kpi_definition_id
            WHERE ckv.campaign_id = :id
            """),
            {"id": str(campaign_id)},
        )).mappings().all()
        kpi_text = "\n".join(f"- {k['name']}: {k['value']}" for k in kpis) or "Sin KPIs cargados"

        # Fill template
        user_tpl = prompt_row["user_template"]
        context = {
            "client": camp["client_name"],
            "brand": camp["brand_name"],
            "campaign_name": camp["name"],
            "objective": camp["objective"],
            "status": camp["status"],
            "kpis": kpi_text,
            "insights": "",
            "winning_format": "",
            "tiers": ", ".join(camp["influencer_tiers"] or []),
            "budget": str(camp["budget_total"] or "N/D"),
            "audience": camp["target_audience"] or "N/D",
            **extra_context,
        }
        try:
            user_prompt = user_tpl.format(**context)
        except KeyError:
            user_prompt = user_tpl

        # Call LLM
        try:
            llm = get_llm(temperature=float(prompt_row["temperature"]))
            response = await llm.ainvoke([
                {"role": "system", "content": prompt_row["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ])
            generated_text = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error("generate_llm_failed", error=str(e), prompt_code=prompt_code)
            raise

        # Persist as AI-generated insight if post_mortem
        if prompt_code.startswith("post_mortem"):
            await db.execute(
                text("""
                INSERT INTO insights (campaign_id, insight_type, title, description, generated_by_ai)
                VALUES (:cid, 'post_mortem', 'Post-Mortem generado por IA', :desc, TRUE)
                """),
                {"cid": str(campaign_id), "desc": generated_text},
            )
            await db.commit()

        return {
            "campaign_id": str(campaign_id),
            "prompt_code": prompt_code,
            "generated_content": generated_text,
            "model": prompt_row["model_name"],
        }