"""
P.I.A.R. RAG Engine — retrieve + generate with citations.

Builds on top of AIService. Adds:
- P.I.A.R.-specific system prompt
- Strict citation of sources in responses
- Detection of queries that need RAG vs. general knowledge
"""

import json
from dataclasses import dataclass
from typing import Any

import structlog

from app.ai.deepseek_client import deepseek_client
from app.ai.embeddings import embed_text

logger = structlog.get_logger(__name__)

PIAR_SYSTEM_PROMPT = """Eres el asistente IA de La Web Core, la plataforma de gestión de campañas de marketing de influencers de La Web Figital Agency (Venezuela).

REGLAS ESTRICTAS:
1. Solo respondes con información de las fuentes proporcionadas en el contexto.
2. Si ninguna fuente es relevante, responde: "No tengo información suficiente en la base de datos para responder esa pregunta."
3. Cuando cites información de una fuente, usa el formato [ref:{tipo}:{id}] al final de la oración.
4. Nunca inventas datos, métricas o nombres de influencers.
5. Todos los números los presentas con formato legible (ej: 1.2M en vez de 1200000).
6. Hablas en español profesional latinoamericano.
7. Para consultas sobre "mejor influencer", "top creador", "mayor ER", siempre operas sobre los datos disponibles en la base, no sobre conocimiento general.
8. El contexto recuperado puede contener información de: publicaciones de campañas, scores de influencers, o benchmarks LWFA."""

USER_PROMPT_TEMPLATE = """Contexto recuperado de la base de conocimiento:

{context}

---
Pregunta: {query}

---
Instrucciones: Responde basándote EXCLUSIVAMENTE en el contexto de arriba. Cita cada afirmación con [ref:{tipo}:{id}]. Si no hay información relevante en el contexto, dilo claramente."""


@dataclass
class Source:
    chunk_id: str
    content_type: str
    source_id: str
    similarity: float
    excerpt: str


def _needs_rag(query: str) -> bool:
    """Detect if a query would benefit from RAG retrieval."""
    query_lower = query.lower()
    rag_keywords = [
        "influencer", "creador", "campaña", "publicación", "métricas", "kpis",
        "er", "engagement", "vistas", "alcance", "sentimiento", "score",
        "benchmark", "sub-tier", "tier", "proyección", "proyeccion",
        "mejor", "peor", "top", "ranking", "comparar", "comparación",
        "rendimiento", "performance", "audiencia", "seguidores",
    ]
    general_keywords = [
        "que es", "qué es", "definición", "concepto", "cómo funciona",
        "hola", "buenos días", "saludos", "gracias", "ayuda",
    ]
    query_has_rag = any(kw in query_lower for kw in rag_keywords)
    query_is_general = any(kw in query_lower for kw in general_keywords)
    return query_has_rag or not query_is_general


async def retrieve_context(
    query: str,
    db: Any,
    top_k: int = 6,
    similarity_threshold: float = 0.65,
) -> tuple[str, list[Source]]:
    """
    Embed query and retrieve relevant chunks from document_chunks.
    Returns (context_text, sources_list).
    """
    try:
        query_embedding = await embed_text(query)
    except Exception as e:
        logger.warning("embed_failed_rag", error=str(e))
        return "", []

    try:
        from sqlalchemy import text
        result = await db.execute(
            text("""
                SELECT id, document_id, content, metadata,
                       1 - (embedding <=> CAST(:emb AS vector)) AS similarity
                FROM document_chunks
                WHERE embedding IS NOT NULL
                  AND 1 - (embedding <=> CAST(:emb AS vector)) > :threshold
                ORDER BY embedding <=> CAST(:emb AS vector)
                LIMIT :top_k
            """),
            {"emb": str(query_embedding), "threshold": similarity_threshold, "top_k": top_k},
        )
        rows = result.mappings().all()
    except Exception as e:
        logger.warning("vector_search_failed", error=str(e))
        return "", []

    if not rows:
        return "", []

    chunks_text: list[str] = []
    sources: list[Source] = []

    for row in rows:
        meta = dict(row["metadata"] or {})
        content_type = meta.get("content_type", "unknown")
        source_id = meta.get("publicacion_id") or meta.get("influencer_id") or meta.get("subtier") or str(row["document_id"])

        excerpt = row["content"][:300] if row["content"] else ""
        chunks_text.append(f"[{content_type}:{source_id}]\n{row['content']}")
        sources.append(Source(
            chunk_id=str(row["id"]),
            content_type=content_type,
            source_id=source_id,
            similarity=float(row["similarity"]),
            excerpt=excerpt,
        ))

    context = "\n\n---\n\n".join(chunks_text)
    return context, sources


async def generate_with_context(
    query: str,
    context: str,
    sources: list[Source],
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[str, list[dict[str, Any]], int]:
    """
    Generate response using DeepSeek with RAG context.
    Returns (answer, formatted_sources, tokens_used).
    """
    if not context:
        return (
            "No tengo información suficiente en la base de datos para responder esa pregunta.",
            [],
            0,
        )

    user_prompt = USER_PROMPT_TEMPLATE.format(context=context, query=query)

    messages = [
        {"role": "system", "content": PIAR_SYSTEM_PROMPT},
    ]
    if conversation_history:
        for msg in conversation_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_prompt})

    try:
        response = deepseek_client.complete(
            prompt=user_prompt,
            system=PIAR_SYSTEM_PROMPT,
        )
        answer = response.content
        tokens = response.tokens_used or 0
    except Exception as e:
        logger.error("rag_llm_error", error=str(e))
        answer = "Tuve un problema al generar la respuesta. Por favor intenta de nuevo."
        tokens = 0

    formatted_sources = [
        {
            "type": s.content_type,
            "id": s.source_id,
            "similarity": round(s.similarity, 3),
            "excerpt": s.excerpt[:150],
        }
        for s in sources
    ]

    return answer, formatted_sources, tokens


async def rag_query(
    query: str,
    db: Any,
    conversation_history: list[dict[str, str]] | None = None,
    force_rag: bool = False,
) -> dict[str, Any]:
    """
    Full RAG pipeline: detect → retrieve → generate → format sources.

    Returns:
        answer: str
        sources: list[dict]
        tokens_used: int
        used_rag: bool
    """
    used_rag = force_rag or _needs_rag(query)

    if not used_rag:
        return {
            "answer": "Para consultas generales sobre La Web Core, consulta la documentación o contacta al equipo de soporte.",
            "sources": [],
            "tokens_used": 0,
            "used_rag": False,
        }

    context, sources = await retrieve_context(query, db, top_k=6)

    answer, formatted_sources, tokens = await generate_with_context(
        query, context, sources, conversation_history
    )

    return {
        "answer": answer,
        "sources": formatted_sources,
        "tokens_used": tokens,
        "used_rag": True,
    }
