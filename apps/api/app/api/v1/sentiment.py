"""P.I.A.R. Sentiment Analysis endpoints — DeepSeek-powered comment classification."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from shared_core import railway_pg

from app.ai.sentiment_analyzer import analyze_comments_full
from app.core.security import CurrentUserDep

router = APIRouter(prefix="/sentiment", tags=["sentiment"])


def _pub_exists(pub_id: str) -> dict[str, Any]:
    rows = railway_pg.table(
        "publicaciones",
        select="id,sentimiento_positivo,sentimiento_neutro,sentimiento_negativo,comentarios_analizados,sentimiento_analizado_at",
        eq_filters={"id": pub_id},
        limit=1,
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Publicación {pub_id} no encontrada")
    return rows[0]


@router.post("/analyze")
async def analyze_comments(
    payload: dict[str, Any],
    user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Analiza comentarios de UNA publicación.

    Body:
      publicacion_id: UUID de la publicación
      comentarios: list[str] — textos de los comentarios a analizar
                  (si se omite, busca en la tabla comentarios)

    Si se proporcionan directamente los textos, se usan esos.
    Si no, se buscan en la tabla comentarios de Supabase.
    """
    pub_id: str | None = payload.get("publicacion_id")
    if not pub_id:
        raise HTTPException(status_code=422, detail="publicacion_id es requerido")

    pub = _pub_exists(pub_id)  # noqa: F841
    comment_texts: list[str] | None = payload.get("comentarios")

    if comment_texts is None:
        rows = railway_pg.table(
            "comentarios",
            select="id,texto",
            eq_filters={"publicacion_id": pub_id, "analyzed_sentiment": None},
            limit=500,
        )
        comment_texts = [r["texto"] for r in rows if r.get("texto")]

    if not comment_texts:
        raise HTTPException(
            status_code=422,
            detail="No hay comentarios para analizar (ni en body ni en tabla comentarios)",
        )

    dist = await analyze_comments_full(comment_texts)

    now = datetime.now(UTC).isoformat()
    updates = {
        "comentarios_analizados": dist.to_dict(),
        "sentimiento_positivo": dist.positivo,
        "sentimiento_neutro": dist.neutro,
        "sentimiento_negativo": dist.negativo,
        "sentimiento_analizado_at": now,
    }
    await railway_pg.update("publicaciones", updates, eq_filters={"id": pub_id})

    return {
        "publicacion_id": pub_id,
        "distribution": dist.to_dict(),
        "analyzed_at": now,
    }


@router.get("/publicacion/{publicacion_id}")
async def get_sentiment(
    publicacion_id: str,
    user: CurrentUserDep,
) -> dict[str, Any]:
    """Devuelve el resultado de análisis de sentimiento de una publicación."""
    pub = _pub_exists(publicacion_id)

    if not pub.get("comentarios_analizados"):
        raise HTTPException(
            status_code=404,
            detail="Esta publicación aún no tiene análisis de sentimiento",
        )

    return {
        "publicacion_id": publicacion_id,
        "analizado_en": pub.get("sentimiento_analizado_at"),
        "distribution": pub["comentarios_analizados"],
    }


@router.get("/campaign/{campaign_id}/aggregate")
async def campaign_sentiment_aggregate(
    campaign_id: str,
    user: CurrentUserDep,
) -> dict[str, Any]:
    """Agrega sentimiento de todas las publicaciones de una campaña."""
    rows = railway_pg.table(
        "publicaciones",
        select="id,sentimiento_positivo,sentimiento_neutro,sentimiento_negativo,comentarios_analizados",
        eq_filters={"campaign_id": campaign_id},
        limit=1000,
    )

    total_pos = sum(int(r.get("sentimiento_positivo") or 0) for r in rows)
    total_neu = sum(int(r.get("sentimiento_neutro") or 0) for r in rows)
    total_neg = sum(int(r.get("sentimiento_negativo") or 0) for r in rows)
    analyzed = sum(1 for r in rows if r.get("comentarios_analizados"))
    pending = len(rows) - analyzed
    total_comments = total_pos + total_neu + total_neg

    pub_breaks = []
    for r in rows:
        if r.get("comentarios_analizados"):
            pub_breaks.append({
                "publicacion_id": str(r["id"]),
                "analizado": True,
                "positivo": int(r.get("sentimiento_positivo") or 0),
                "neutro": int(r.get("sentimiento_neutro") or 0),
                "negativo": int(r.get("sentimiento_negativo") or 0),
            })
        else:
            pub_breaks.append({
                "publicacion_id": str(r["id"]),
                "analizado": False,
            })

    return {
        "campaign_id": campaign_id,
        "total_publicaciones": len(rows),
        "analizadas": analyzed,
        "pendientes": pending,
        "totales": {
            "positivo": total_pos,
            "neutro": total_neu,
            "negativo": total_neg,
            "total": total_comments,
        },
        "por_publicacion": pub_breaks,
    }


@router.post("/campaign/{campaign_id}/reanalyze")
async def reanalyze_campaign(
    campaign_id: str,
    user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Fuerza el re-análisis de TODAS las publicaciones con comentarios
    pendientes de una campaña. Se ejecuta en background.
    """
    rows = railway_pg.table(
        "publicaciones",
        select="id",
        eq_filters={"campaign_id": campaign_id},
        limit=500,
    )

    job_id = f"sentiment_reanalyze_{campaign_id}"
    background_tasks.add_task(_background_reanalyze, [r["id"] for r in rows], job_id)

    return {
        "campaign_id": campaign_id,
        "queued": len(rows),
        "job_id": job_id,
        "message": f"Re-análisis de {len(rows)} publicaciones encolado",
    }


async def _background_reanalyze(pub_ids: list[str], job_id: str) -> None:
    """Background task: re-analiza publicaciones."""
    import structlog
    logger = structlog.get_logger()
    logger.info("sentiment_reanalyze_job_start", job_id=job_id, count=len(pub_ids))

    for pub_id in pub_ids:
        try:
            comment_rows = railway_pg.table(
                "comentarios",
                select="id,texto",
                eq_filters={"publicacion_id": pub_id},
                limit=500,
            )
            texts = [r["texto"] for r in comment_rows if r.get("texto")]
            if not texts:
                continue

            dist = await analyze_comments_full(texts)
            now = datetime.now(UTC).isoformat()

            updates = {
                "comentarios_analizados": dist.to_dict(),
                "sentimiento_positivo": dist.positivo,
                "sentimiento_neutro": dist.neutro,
                "sentimiento_negativo": dist.negativo,
                "sentimiento_analizado_at": now,
            }
            await railway_pg.update("publicaciones", updates, eq_filters={"id": pub_id})

            for r, c in zip(comment_rows, dist.comentarios):  # noqa: B905
                await railway_pg.update("comentarios", {
                    "analyzed_sentiment": c.sentiment.value,
                    "analyzed_confidence": c.confidence,
                }, eq_filters={"id": r["id"]})

            logger.info("sentiment_pub_analyzed", pub_id=pub_id, dist=dist.to_dict())
        except Exception as e:
            logger.error("sentiment_pub_error", pub_id=pub_id, error=str(e))

    logger.info("sentiment_reanalyze_job_done", job_id=job_id)
