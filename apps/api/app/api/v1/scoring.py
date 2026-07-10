"""P.I.A.R. Scoring + Benchmarks endpoints."""

from fastapi import APIRouter, HTTPException, Query

from app.core.piar_scoring import (
    calcular_score,
    calcular_score_profile,
    ScoringMode,
    ScoreDecision,
)
from app.core.piar_benchmarks import (
    get_all_benchmarks_formatted,
    get_benchmark_status_for_influencer,
    compare_with_benchmark,
    get_benchmark_by_followers,
)
from app.core.supabase_rest import supabase_rest
from app.core.security import CurrentUserDep

router = APIRouter()


@router.get("/influencers/{influencer_id}/score", summary="Score de influencer")
async def get_influencer_score(
    influencer_id: str,
    user: CurrentUserDep,
    mode: str = Query(default="BY_PROFILE", description="BY_POST | BY_WAVE | BY_PROFILE"),
    campaign_id: str | None = Query(default=None, description="Solo para modo BY_WAVE"),
):
    """
    Calcula el score de un influencer.

    3 modos:
    - BY_PROFILE (default): Score acumulado de todas sus publicaciones. Refleja el valor real del creador.
    - BY_WAVE: Score promediado de las publicaciones de una campaña específica.
    - BY_POST: Score de una publicación individual.

    Retorna:
        - score_retention, score_engagement, score_viralidad (1-3 pts cada uno)
        - score_final = promedio de los 3
        - decision: ESCALAR (≥2.5) | OPTIMIZAR (1.8-2.5) | DESCARTAR (<1.8) | DATOS_INSUFICIENTES
        - benchmark_status: semáforo verde/amarillo/rojo por dimensión
        - publicaciones_count: número de publicaciones consideradas
    """
    scoring_mode = ScoringMode(mode.upper())
    result = await calcular_score(influencer_id, scoring_mode, campaign_id)
    return result.to_dict()


@router.get("/influencers/{influencer_id}/benchmark-status", summary="Estado de benchmark LWFA")
async def get_influencer_benchmark_status(
    influencer_id: str,
    user: CurrentUserDep,
):
    """
    Compara los KPIs promediados del influencer contra su benchmark LWFA.

    Retorna semáforo (green/yellow/red) para ER, V/F y CPV,
    más el benchmark matched (sub-tier y role_description).
    """
    status, benchmark = await get_benchmark_status_for_influencer(influencer_id)
    if not benchmark:
        raise HTTPException(
            status_code=404,
            detail="No se encontró benchmark para este influencer (verifica followers en snapshots)",
        )
    return {
        **status.to_dict(),
        "benchmark_aplicado": {
            "subtier": benchmark.get("subtier"),
            "followers_min": benchmark.get("followers_min"),
            "followers_max": benchmark.get("followers_max"),
            "er_range": f"{benchmark.get('er_min')}% – {benchmark.get('er_max')}%",
            "vf_range": f"{benchmark.get('vf_min')}x – {benchmark.get('vf_max')}x",
            "cpv_ideal": f"${benchmark.get('cpv_ideal')}",
            "role": benchmark.get("role_description"),
        },
    }


@router.get("/benchmarks", summary="Todos los benchmarks LWFA")
async def list_benchmarks(user: CurrentUserDep):
    """
    Retorna la tabla completa de benchmarks LWFA (9 categorías).
    """
    return await get_all_benchmarks_formatted()


@router.get("/benchmarks/{subtier}", summary="Benchmark por sub-tier")
async def get_benchmark_by_tier(subtier: str, user: CurrentUserDep):
    """
    Retorna el benchmark para una sub-tier específica.
    Ejemplo: NANO_BAJO, MICRO_MEDIO, MACRO_ALTO
    """
    benchmark = await get_benchmark_by_followers(None)
    rows = await supabase_rest.table(
        "tier_benchmarks",
        select="*",
        eq_filters={"subtier": subtier.upper()},
        limit=1,
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Benchmark no encontrado: {subtier}")
    row = rows[0]
    return {
        "subtier": row["subtier"],
        "followers_range": f"{row['followers_min']:,} – {row['followers_max']:,}",
        "vf_range": f"{row['vf_min']}x – {row['vf_max']}x",
        "er_range": f"{row['er_min']}% – {row['er_max']}%",
        "cpv_ideal": f"${row['cpv_ideal']:.4f}",
        "role": row.get("role_description"),
    }


@router.get("/influencers", summary="Lista influencers con filtros de decisión")
async def list_influencers_with_score(
    user: CurrentUserDep,
    decision: str | None = Query(None, description="Filtrar por decisión: ESCALAR | OPTIMIZAR | DESCARTAR | DATOS_INSUFICIENTES"),
    subtier: str | None = Query(None, description="Filtrar por sub-tier"),
    limit: int = Query(100, le=500),
):
    """
    Lista influencers con sus scores calculados.

    Opcionalmente filtra por decisión (ESCALAR/OPTIMIZAR/DESCARTAR)
    o por sub-tier (NANO_BAJO, MICRO_MEDIO, etc.)
    """
    rows = await supabase_rest.table(
        "influencers",
        select="id,full_name,primary_handle,primary_tier,sub_tier,status",
        eq_filters={"status": "active"},
        limit=limit,
    )

    result = []
    for row in rows:
        inf_id = str(row["id"])
        score_breakdown = await calcular_score_profile(inf_id)
        score_dict = score_breakdown.to_dict()

        if decision and score_dict["decision"] != decision.upper():
            continue
        if subtier and score_dict.get("subtier") != subtier.upper():
            continue

        result.append({
            **row,
            "score": score_dict,
        })

    return result
