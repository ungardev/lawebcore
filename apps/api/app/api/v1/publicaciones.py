"""Publicaciones endpoints — metrics per influencer post (P.I.A.R)."""

from fastapi import APIRouter, Query
from app.core.supabase_rest import supabase_rest
from app.core.security import CurrentUserDep

router = APIRouter()


@router.get("")
async def list_publicaciones(
    user: CurrentUserDep,
    campaign_id: str | None = Query(None),
    influencer_id: str | None = Query(None),
    limit: int = Query(500, le=2000),
):
    """
    Lista publicaciones con filtros opcionales.
    """
    all_rows = await supabase_rest.table("publicaciones", select="*", limit=limit)

    if campaign_id:
        all_rows = [r for r in all_rows if str(r.get("campaign_id") or "") == campaign_id]
    if influencer_id:
        all_rows = [r for r in all_rows if str(r.get("influencer_id") or "") == influencer_id]

    all_rows.sort(key=lambda r: r.get("fecha_publicacion") or "", reverse=True)
    return all_rows


@router.get("/stats/{campaign_id}")
async def stats_publicaciones(
    campaign_id: str,
    user: CurrentUserDep,
):
    """
    Agregados de publicaciones para una campaña.
    Útil para los gráficos de la ficha de campaña.
    """
    rows = await supabase_rest.table(
        "publicaciones",
        select="fecha_publicacion,vistas,alcance,likes,comentarios,guardados,er_alcance,er_vistas,retencion,sentimiento_positivo,sentimiento_neutro,sentimiento_negativo",
        eq_filters={"campaign_id": campaign_id},
        limit=5000,
    )

    if not rows:
        return {
            "total": 0,
            "sum_vistas": 0,
            "sum_alcance": 0,
            "sum_likes": 0,
            "sum_comentarios": 0,
            "avg_er": None,
            "avg_retencion": None,
            "sentimiento_total": {"positivo": 0, "neutro": 0, "negativo": 0},
            "timeline": [],
        }

    sum_vistas = sum(int(r.get("vistas") or 0) for r in rows)
    sum_alcance = sum(int(r.get("alcance") or 0) for r in rows)
    sum_likes = sum(int(r.get("likes") or 0) for r in rows)
    sum_comentarios = sum(int(r.get("comentarios") or 0) for r in rows)

    er_vals = [float(r["er_alcance"] or r["er_vistas"] or 0) for r in rows if r.get("er_alcance") or r.get("er_vistas")]
    avg_er = sum(er_vals) / len(er_vals) if er_vals else None

    retencion_vals = [float(r["retencion"]) for r in rows if r.get("retencion")]
    avg_retencion = sum(retencion_vals) / len(retencion_vals) if retencion_vals else None

    sum_pos = sum(int(r.get("sentimiento_positivo") or 0) for r in rows)
    sum_neu = sum(int(r.get("sentimiento_neutro") or 0) for r in rows)
    sum_neg = sum(int(r.get("sentimiento_negativo") or 0) for r in rows)

    rows.sort(key=lambda r: r.get("fecha_publicacion") or "")
    timeline = [
        {
            "fecha": r.get("fecha_publicacion"),
            "vistas": r.get("vistas"),
            "alcance": r.get("alcance"),
            "likes": r.get("likes"),
            "comentarios": r.get("comentarios"),
            "er": r.get("er_alcance") or r.get("er_vistas"),
        }
        for r in rows
    ]

    return {
        "total": len(rows),
        "sum_vistas": sum_vistas,
        "sum_alcance": sum_alcance,
        "sum_likes": sum_likes,
        "sum_comentarios": sum_comentarios,
        "avg_er": round(avg_er, 6) if avg_er else None,
        "avg_retencion": round(avg_retencion, 4) if avg_retencion else None,
        "sentimiento_total": {
            "positivo": sum_pos,
            "neutro": sum_neu,
            "negativo": sum_neg,
        },
        "timeline": timeline,
    }
