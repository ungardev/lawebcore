"""AI Service - chat (RAG), generation, embeddings orchestration.

This service is the entry point for all AI features:
- Chat with RAG: retrieve relevant chunks from pgvector, build prompt, call LLM
- Generation: load prompt template, fill with campaign context, call LLM
- Embeddings: chunk a document, embed with OpenAI, store in pgvector
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import structlog
from langchain_openai import ChatOpenAI
from shared_ai import deepseek_client, embed_text
from shared_core import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

logger = structlog.get_logger(__name__)


class AIService:
    """Orchestrates all AI operations."""

    async def _load_system_prompt(self, code: str, fallback: str, db: AsyncSession) -> str:
        """Load system prompt from ai_prompts table. Falls back to hardcoded string."""
        try:
            row = (
                await db.execute(
                    text("""
                        SELECT system_prompt FROM ai_prompts
                        WHERE code = :code AND is_active = TRUE
                        ORDER BY version DESC LIMIT 1
                    """),
                    {"code": code},
                )
            ).mappings().first()
            if row:
                return row["system_prompt"]
        except Exception as e:
            logger.warning("load_system_prompt_failed", code=code, error=str(e))
        return fallback

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
        await db.rollback()

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
        await db.rollback()

        # 4. Load conversation history (last 6 messages)
        conversation_history: list[dict[str, str]] = []
        try:
            history_rows = await db.execute(
                text("""
                    SELECT role, content FROM ai_messages
                    WHERE conversation_id = :cid
                    ORDER BY created_at DESC
                    LIMIT 6
                """),
                {"cid": str(conv_id)},
            )
            rows = history_rows.mappings().all()
            conversation_history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        except Exception as e:
            logger.warning("load_conversation_history_failed", error=str(e))
        await db.rollback()

        # 5. Build prompt and call LLM
        _SYSTEM_PROMPT_FALLBACK = (  # noqa: N806
            "Eres el asistente estratégico de La Web Figital Agency — la agencia de influencer marketing "
            "#1 en Venezuela, con 12 años ejecutando campañas en Latam.\n\n"
            "CONOCIMIENTO CLAVE:\n"
            "- Mercado VE: 4.5M usuarios IG activos, 65% femenino, 25-44 años\n"
            "- ER promedio VE: 4-7% es bueno, >8% es excelente\n"
            "- Tiers: MACRO (>500K), MID (100K-500K), MICRO (10K-100K), NANO (<10K)\n\n"
            "REGLAS ESTRICTAS:\n"
            "1. Solo respondes con información de las fuentes proporcionadas. Si no hay contexto, dilo claramente.\n"
            "2. Cuando cites datos, usa [ref:{tipo}:{id}] al final de la oración.\n"
            "3. Nunca inventas métricas ni nombres de creators. Si no tienes el dato, dilo.\n"
            "4. Presenta números de forma legible: 1.2M en vez de 1200000, 5.8% en vez de 0.058.\n"
            "5. Tono: profesional-seguro, estratégico. Ejemplo: 'El brief es claro. La jugada es...' No seas genérico.\n"
            "6. Si el usuario pregunta por 'mejor influencer' o 'top creators', responde solo con datos de la base.\n"
            "7. Para decisiones de campaña, siempre da contexto de mercado (no solo números)."
        )
        system_prompt = await self._load_system_prompt("rag_system_v1", _SYSTEM_PROMPT_FALLBACK, db)

        history_text = ""
        if conversation_history:
            history_lines = [
                f"{'Usuario' if msg['role'] == 'user' else 'Asistente'}: {msg['content']}"
                for msg in conversation_history
            ]
            history_text = "\n".join(history_lines) + "\n\n"

        user_prompt = (
            f"{history_text}"
            f"Contexto recuperado de la base de conocimiento:\n\n{context_text}\n\n"
            f"---\n\nPregunta del usuario: {message}\n\n"
            "Responde basándote EXCLUSIVAMENTE en el contexto de arriba. "
            "Cita cada afirmación con [ref:{tipo}:{id}]. "
            "Si no hay información relevante en el contexto, dilo claramente."
        )

        try:
            result = await deepseek_client.complete(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.4,
                max_tokens=2000,
            )
            answer_text = result.content
            tokens_input = result.tokens_input or 0
            tokens_output = result.tokens_output or 0
            cost_usd = result.cost_usd or 0.0
            latency_ms = result.latency_ms or 0
        except Exception as e:
            logger.error("llm_call_failed", error=str(e), exc_info=True)
            answer_text = (
                "Disculpa, tuve un problema al procesar tu consulta con el modelo de IA. "
                "El equipo tecnico ha sido notificado. "
                "Por favor intenta de nuevo en unos momentos."
            )
            tokens_input = 0
            tokens_output = 0
            cost_usd = 0.0
            latency_ms = 0

        # 5. Persist assistant message
        await db.rollback()
        try:
            await db.execute(
                text("""
                INSERT INTO ai_messages (conversation_id, role, content, model_provider, model_name,
                                          tokens_input, tokens_output, cost_usd, latency_ms)
                VALUES (:cid, 'assistant', :content, :prov, :model, :tin, :tout, :cost, :lat)
                """),
                {
                    "cid": str(conv_id),
                    "content": answer_text,
                    "prov": "deepseek",
                    "model": settings.DEEPSEEK_MODEL,
                    "tin": tokens_input,
                    "tout": tokens_output,
                    "cost": cost_usd,
                    "lat": latency_ms,
                },
            )
        except Exception as e:
            logger.error("persist_assistant_message_failed", error=str(e), exc_info=True)
            await db.rollback()
        else:
            await db.commit()

        return {
            "conversation_id": conv_id,
            "message": answer_text,
            "sources": sources,
            "tokens_used": tokens_input + tokens_output,
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
            model_name = prompt_row.get("model_name") or settings.DEEPSEEK_MODEL
            provider = prompt_row.get("model_provider", "deepseek")
            if provider == "deepseek":
                base_url = "https://api.deepseek.com"
                api_key = settings.DEEPSEEK_API_KEY
            else:
                base_url = None
                api_key = None
            llm = ChatOpenAI(
                model=model_name,
                temperature=float(prompt_row["temperature"]),
                api_key=api_key,
                base_url=base_url,
            )
            response = await llm.ainvoke([
                {"role": "system", "content": prompt_row["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ])
            generated_text = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error("generate_llm_failed", error=str(e), prompt_code=prompt_code, exc_info=True)
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
