"""
P.I.A.R. RAG Indexer — indexa publicaciones, scores y benchmarks en document_chunks.

Triggered:
  - On-demand via endpoint POST /ai/index/reindex
  - After a publication is inserted/updated
  - After a scoring is calculated

Uses the existing document_chunks table (no document_id required for P.I.A.R. data —
we use metadata to link back to the source).
"""

import structlog
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared_ai import embed_texts, chunk_text

logger = structlog.get_logger(__name__)

CHUNK_SIZE = 600
EMBED_BATCH = 20


def _build_pub_text(pub: dict[str, Any]) -> str:
    parts = [
        f"Publicación: {pub.get('platform', 'N/A')}",
        f"Fecha: {pub.get('fecha_publicacion', 'N/A')}",
    ]
    if pub.get("influencer_name"):
        parts.append(f"Creador: {pub['influencer_name']}")
    if pub.get("formato"):
        parts.append(f"Formato: {pub['formato']}")
    if pub.get("vistas") is not None:
        parts.append(f"Vistas: {pub['vistas']:,}")
    if pub.get("alcance") is not None:
        parts.append(f"Alcance: {pub['alcance']:,}")
    if pub.get("likes") is not None:
        parts.append(f"Likes: {pub['likes']:,}")
    if pub.get("comentarios") is not None:
        parts.append(f"Comentarios: {pub['comentarios']:,}")
    if pub.get("er_alcance") is not None:
        parts.append(f"ER (alcance): {float(pub['er_alcance']) * 100:.2f}%")
    if pub.get("er_vistas") is not None:
        parts.append(f"ER (vistas): {float(pub['er_vistas']) * 100:.2f}%")
    if pub.get("retencion") is not None:
        parts.append(f"Retención: {float(pub['retencion']) * 100:.1f}%")
    if pub.get("sentimiento_positivo") is not None:
        parts.append(f"Sentimiento positivo: {pub['sentimiento_positivo']}")
    if pub.get("sentimiento_neutro") is not None:
        parts.append(f"Sentimiento neutro: {pub['sentimiento_neutro']}")
    if pub.get("sentimiento_negativo") is not None:
        parts.append(f"Sentimiento negativo: {pub['sentimiento_negativo']}")
    if pub.get("url_publicacion"):
        parts.append(f"URL: {pub['url_publicacion']}")
    return " | ".join(parts)


def _build_score_text(inf_id: str, score: dict[str, Any]) -> str:
    parts = [
        f"Scoring de influencer: {inf_id}",
        f"Decisión: {score.get('decision', 'N/A')}",
        f"Score final: {score.get('score_final', 'N/A')}/3.0",
    ]
    if score.get("score_retention") is not None:
        parts.append(f"Retención: {score['score_retention']}/3 pts")
    if score.get("score_engagement") is not None:
        parts.append(f"Engagement: {score['score_engagement']}/3 pts")
    if score.get("score_viralidad") is not None:
        parts.append(f"Viralidad: {score['score_viralidad']}/3 pts")
    if score.get("retention_avg") is not None:
        parts.append(f"Retención promedio: {score['retention_avg']:.3f}s/vista")
    if score.get("er_vistas") is not None:
        parts.append(f"ER vistas: {float(score['er_vistas']) * 100:.2f}%")
    if score.get("vf_ratio") is not None:
        parts.append(f"V/F: {score['vf_ratio']:.3f}")
    if score.get("followers") is not None:
        parts.append(f"Seguidores: {score['followers']:,}")
    if score.get("subtier"):
        parts.append(f"Sub-tier: {score['subtier']}")
    if score.get("mode"):
        parts.append(f"Modo scoring: {score['mode']}")
    parts.append(f"Publicaciones analizadas: {score.get('publicaciones_count', 0)}")
    return " | ".join(parts)


def _build_benchmark_text(subtier: str, bench: dict[str, Any]) -> str:
    parts = [
        f"Benchmark LWFA: {subtier}",
        f"V/F: {bench.get('vf_min', 0):.2f}x – {bench.get('vf_max', 0):.2f}x",
        f"ER: {bench.get('er_min', 0):.2f}% – {bench.get('er_max', 0):.2f}%",
    ]
    if bench.get("cpv_ideal") is not None:
        parts.append(f"CPV ideal: ${bench['cpv_ideal']:.4f}")
    if bench.get("role_description"):
        parts.append(f"Rol: {bench['role_description']}")
    return " | ".join(parts)


async def _insert_chunks(
    db: AsyncSession,
    content_type: str,
    source_id: str,
    chunks: list[str],
    metadata: dict[str, Any],
) -> int:
    if not chunks:
        return 0
    inserted = 0
    for i in range(0, len(chunks), EMBED_BATCH):
        batch = chunks[i:i + EMBED_BATCH]
        vectors = await embed_texts(batch)
        for j, (chunk_text_val, vec) in enumerate(zip(batch, vectors)):
            chunk_idx = i + j
            await db.execute(
                text("""
                    INSERT INTO document_chunks
                        (id, document_id, chunk_index, content, embedding, metadata)
                    VALUES
                        (:id, :doc_id, :idx, :content, :emb, :meta)
                    ON CONFLICT (document_id, chunk_index)
                    DO UPDATE SET content = EXCLUDED.content,
                                  embedding = EXCLUDED.embedding,
                                  metadata = EXCLUDED.metadata
                """),
                {
                    "id": str(uuid4()),
                    "doc_id": str(source_id),
                    "idx": chunk_idx,
                    "content": chunk_text_val,
                    "emb": str(vec),
                    "meta": {"content_type": content_type, **metadata},
                },
            )
        inserted += len(batch)
    return inserted


async def index_publicacion(
    db: AsyncSession,
    pub_id: str,
    pub_data: dict[str, Any] | None = None,
) -> int:
    """Index or re-index a single publicacion in the vector store."""
    if pub_data is None:
        from shared_core import supabase_rest
        rows = await supabase_rest.table(
            "publicaciones", select="*", eq_filters={"id": pub_id}, limit=1
        )
        if not rows:
            return 0
        pub_data = rows[0]

    raw_text = _build_pub_text(pub_data)
    chunks = chunk_text(raw_text, chunk_size=CHUNK_SIZE)

    meta = {
        "content_type": "publicacion",
        "publicacion_id": pub_id,
        "campaign_id": str(pub_data.get("campaign_id", "")),
        "influencer_id": str(pub_data.get("influencer_id", "") or ""),
        "platform": pub_data.get("platform", ""),
        "fecha": pub_data.get("fecha_publicacion", ""),
    }

    total = await _insert_chunks(db, "publicacion", pub_id, chunks, meta)
    logger.info("indexed_publicacion", pub_id=pub_id, chunks=total)
    return total


async def index_publicaciones_by_campaign(
    db: AsyncSession,
    campaign_id: str,
) -> int:
    """Re-index all publicaciones for a campaign."""
    from shared_core import supabase_rest
    rows = await supabase_rest.table(
        "publicaciones",
        select="*",
        eq_filters={"campaign_id": campaign_id},
        limit=500,
    )
    total = 0
    for row in rows:
        try:
            total += await index_publicacion(db, str(row["id"]), row)
        except Exception as e:
            logger.error("index_pub_error", pub_id=row["id"], error=str(e))
    return total


async def index_influencer_score(
    db: AsyncSession,
    inf_id: str,
    score_data: dict[str, Any],
) -> int:
    """Index an influencer scoring result."""
    text_content = _build_score_text(inf_id, score_data)
    chunks = chunk_text(text_content, chunk_size=CHUNK_SIZE)

    meta = {
        "content_type": "influencer_score",
        "influencer_id": inf_id,
        "decision": score_data.get("decision", ""),
        "score_final": score_data.get("score_final"),
    }

    total = await _insert_chunks(db, "influencer_score", inf_id, chunks, meta)
    logger.info("indexed_influencer_score", inf_id=inf_id, chunks=total)
    return total


async def index_benchmarks(db: AsyncSession) -> int:
    """Index all LWFA benchmarks."""
    from shared_core import supabase_rest
    rows = await supabase_rest.table("tier_benchmarks", select="*", limit=20)
    total = 0
    for row in rows:
        subtier = str(row["subtier"])
        text_content = _build_benchmark_text(subtier, row)
        chunks = chunk_text(text_content, chunk_size=CHUNK_SIZE)

        meta = {
            "content_type": "benchmark",
            "subtier": subtier,
            "vf_min": float(row.get("vf_min", 0)),
            "vf_max": float(row.get("vf_max", 0)),
            "er_min": float(row.get("er_min", 0)),
            "er_max": float(row.get("er_max", 0)),
        }

        n = await _insert_chunks(db, "benchmark", f"benchmark_{subtier}", chunks, meta)
        total += n
    logger.info("indexed_benchmarks", total=total)
    return total


async def reindex_all_piar(db: AsyncSession, limit: int = 1000) -> dict[str, int]:
    """
    Full reindex of all P.I.A.R. data.
    Returns counts of indexed items per type.
    """
    logger.info("piar_reindex_start", limit=limit)
    counts: dict[str, int] = {}

    from shared_core import supabase_rest

    pubs = await supabase_rest.table("publicaciones", select="id", limit=limit)
    pub_total = 0
    for row in pubs[:100]:
        try:
            pub_total += await index_publicacion(db, str(row["id"]))
        except Exception as e:
            logger.error("reindex_pub_error", id=row["id"], error=str(e))
    counts["publicaciones"] = pub_total

    bench_total = await index_benchmarks(db)
    counts["benchmarks"] = bench_total

    await db.commit()
    logger.info("piar_reindex_done", counts=counts)
    return counts
