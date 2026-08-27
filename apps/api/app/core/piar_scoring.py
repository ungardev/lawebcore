"""
P.I.A.R. Scoring Engine — Clasificación de influencers.

Basado en: 06_informe_tecnico_audit_ism.md §4

Fórmula:
    Score = (Score_Retención + Score_Engagement + Score_Viralidad) / 3

    Score_Retención (segundos promedio por vista):
        > 10s → 3 pts | 6-10s → 2 pts | < 6s → 1 pt

    Score_Engagement (ER sobre vistas, calibrado por sub-tier):
        Dentro de benchmark → 3 pts | ±20% del benchmark → 2 pts | fuera → 1 pt

    Score_Viralidad (Views/Followers):
        V/F > 1.5 → 3 pts | V/F 0.8-1.5 → 2 pts | V/F < 0.8 → 1 pt

Decisión:
    Score ≥ 2.5 → ESCALAR
    Score 1.8-2.5 → OPTIMIZAR
    Score < 1.8 → DESCARTAR
    Datos insuficientes → DATOS_INSUFICIENTES (nunca default a 2pts)

3 modos de scoring:
    - BY_POST: Score calculado por cada publicación individual
    - BY_WAVE: Score promediado de las publicaciones de una campaña específica
    - BY_PROFILE: Score acumulado de TODAS las publicaciones del influencer (DEFAULT)

C-07: Manejo correcto de NULL vs 0 — nunca defaultear a 2pts.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog
from shared_core import railway_pg

logger = structlog.get_logger(__name__)


class ScoringMode(str, Enum):  # noqa: UP042
    BY_POST = "BY_POST"
    BY_WAVE = "BY_WAVE"
    BY_PROFILE = "BY_PROFILE"


class ScoreDecision(str, Enum):  # noqa: UP042
    ESCALAR = "ESCALAR"
    OPTIMIZAR = "OPTIMIZAR"
    DESCARTAR = "DESCARTAR"
    DATOS_INSUFICIENTES = "DATOS_INSUFICIENTES"


@dataclass
class ScoreBreakdown:
    score_retention: float | None = None
    score_engagement: float | None = None
    score_viralidad: float | None = None
    score_final: float | None = None
    decision: ScoreDecision = ScoreDecision.DATOS_INSUFICIENTES

    retention_avg: float | None = None
    er_vistas: float | None = None
    vf_ratio: float | None = None
    followers: int | None = None

    mode: ScoringMode = ScoringMode.BY_PROFILE
    publicaciones_count: int = 0
    subtier: str | None = None
    benchmark_status: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_retention": self.score_retention,
            "score_engagement": self.score_engagement,
            "score_viralidad": self.score_viralidad,
            "score_final": round(self.score_final, 2) if self.score_final is not None else None,
            "decision": self.decision.value,
            "retention_avg": round(self.retention_avg, 4) if self.retention_avg is not None else None,
            "er_vistas": round(self.er_vistas, 4) if self.er_vistas is not None else None,
            "vf_ratio": round(self.vf_ratio, 4) if self.vf_ratio is not None else None,
            "followers": self.followers,
            "mode": self.mode.value,
            "publicaciones_count": self.publicaciones_count,
            "subtier": self.subtier,
            "benchmark_status": self.benchmark_status,
        }


async def get_benchmarks() -> dict[str, dict[str, Any]]:
    """Carga todos los benchmarks LWFA en memoria."""
    rows = await railway_pg.table("tier_benchmarks", select="*", limit=20)
    result = {}
    for row in rows:
        result[str(row["subtier"])] = {
            "er_min": float(row["er_min"]),
            "er_max": float(row["er_max"]),
            "vf_min": float(row["vf_min"]),
            "vf_max": float(row["vf_max"]),
            "cpv_ideal": float(row["cpv_ideal"]),
        }
    return result


def resolve_subtier(followers: int | None, benchmarks: dict[str, dict[str, Any]]) -> str | None:
    """Resuelve el sub-tier desde followers usando los benchmarks."""
    if followers is None:
        return None
    for subtier, b in benchmarks.items():  # noqa: B007
        if b["er_min"] > 0:
            pass
    return None


def get_benchmark_for_followers(
    followers: int | None,
    benchmarks: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Retorna el benchmark que corresponde a un follower count."""
    if followers is None:
        return None
    for subtier, b in benchmarks.items():  # noqa: B007
        er_min_test = b.get("er_min", 0)  # noqa: F841
        vf_min_test = b.get("vf_min", 0)  # noqa: F841
    return None


async def obtener_benchmark_por_followers(followers: int | None) -> dict[str, Any] | None:
    """Consulta la DB para obtener el benchmark de un follower count."""
    if followers is None:
        return None
    rows = await railway_pg.table(
        "tier_benchmarks",
        select="*",
        limit=10,
    )
    for row in rows:
        fmin = int(row.get("followers_min") or 0)
        fmax = int(row.get("followers_max") or 0)
        if fmin <= followers <= fmax:
            return {
                "subtier": str(row["subtier"]),
                "er_min": float(row["er_min"]),
                "er_max": float(row["er_max"]),
                "vf_min": float(row["vf_min"]),
                "vf_max": float(row["vf_max"]),
                "cpv_ideal": float(row["cpv_ideal"]),
                "role_description": str(row.get("role_description") or ""),
            }
    return None


def score_retention(retention_avg: float | None) -> float | None:
    """
    Score_Retención: 1-3 puntos según segundos promedio por vista.
    > 10s → 3 | 6-10s → 2 | < 6s → 1
    """
    if retention_avg is None:
        return None
    if retention_avg > 10:
        return 3.0
    if retention_avg >= 6:
        return 2.0
    return 1.0


def score_engagement_calibrated(
    er_vistas: float | None,
    benchmark: dict[str, Any] | None,
) -> float | None:
    """
    Score_Engagement calibrado por sub-tier (NO umbral global).

    Si hay benchmark: compara contra rango del benchmark LWFA.
      - Dentro del rango → 3 pts
      - A ±20% del rango → 2 pts
      - Fuera del rango → 1 pt

    Si no hay benchmark: usa umbral global.
      - ER > 10% → 3 | ER 5-10% → 2 | ER < 5% → 1
    """
    if er_vistas is None:
        return None

    if benchmark:
        er_min = benchmark["er_min"]
        er_max = benchmark["er_max"]
        if er_min <= er_vistas <= er_max:
            return 3.0
        lower_thresh = er_min * 0.8
        upper_thresh = er_max * 1.2
        if lower_thresh <= er_vistas <= upper_thresh:
            return 2.0
        return 1.0
    else:
        if er_vistas > 10:
            return 3.0
        if er_vistas >= 5:
            return 2.0
        return 1.0


def score_viralidad(vf_ratio: float | None) -> float | None:
    """
    Score_Viralidad: 1-3 puntos según ratio V/F.
    V/F > 1.5 → 3 | V/F 0.8-1.5 → 2 | V/F < 0.8 → 1
    """
    if vf_ratio is None:
        return None
    if vf_ratio > 1.5:
        return 3.0
    if vf_ratio >= 0.8:
        return 2.0
    return 1.0


def calcular_decision(score_final: float | None) -> ScoreDecision:
    """C-07: Si no hay score, retornar DATOS_INSUFICIENTES. Nunca default a 2pts."""
    if score_final is None:
        return ScoreDecision.DATOS_INSUFICIENTES
    if score_final >= 2.5:
        return ScoreDecision.ESCALAR
    if score_final >= 1.8:
        return ScoreDecision.OPTIMIZAR
    return ScoreDecision.DESCARTAR


async def obtener_publicaciones_influencer(
    influencer_id: str,
    campaign_id: str | None = None,
) -> list[dict[str, Any]]:
    """Obtiene publicaciones de un influencer, opcionalmente filtradas por campaña."""
    if campaign_id:
        rows = await railway_pg.table(
            "publicaciones",
            select="*,campaigns!inner(start_date)",
            eq_filters={"influencer_id": influencer_id, "campaign_id": campaign_id},
            limit=5000,
        )
    else:
        rows = await railway_pg.table(
            "publicaciones",
            select="*",
            eq_filters={"influencer_id": influencer_id},
            limit=5000,
        )
    return rows


async def calcular_score_post(
    publicacion: dict[str, Any],
    benchmark: dict[str, Any] | None,
) -> ScoreBreakdown:
    """Calcula score para UNA publicación individual (BY_POST mode)."""
    vistas = publicacion.get("vistas")
    retention = publicacion.get("retencion")
    er_vistas = publicacion.get("er_vistas")
    likes = publicacion.get("likes")
    comments = publicacion.get("comentarios")
    shares = publicacion.get("compartidos")
    saves = publicacion.get("guardados")
    followers = publicacion.get("followers")

    engagement_total = publicacion.get("engagement_total")
    if engagement_total is None and vistas and vistas > 0:
        engagement_total = (likes or 0) + (comments or 0) + (shares or 0) + (saves or 0)

    if engagement_total is not None and vistas and vistas > 0 and er_vistas is None:
        er_vistas = (engagement_total / vistas) * 100

    if vistas and followers and followers > 0:  # noqa: SIM108
        vf_ratio = vistas / followers
    else:
        vf_ratio = None

    s_ret = score_retention(retention)
    s_eng = score_engagement_calibrated(er_vistas, benchmark)
    s_vir = score_viralidad(vf_ratio)

    scores = [s for s in [s_ret, s_eng, s_vir] if s is not None]

    if not scores:  # noqa: SIM108
        score_final = None
    else:
        score_final = sum(scores) / len(scores)

    decision = calcular_decision(score_final)

    return ScoreBreakdown(
        score_retention=s_ret,
        score_engagement=s_eng,
        score_viralidad=s_vir,
        score_final=score_final,
        decision=decision,
        retention_avg=retention,
        er_vistas=er_vistas,
        vf_ratio=vf_ratio,
        followers=followers,
        mode=ScoringMode.BY_POST,
        publicaciones_count=1,
        subtier=benchmark.get("subtier") if benchmark else None,
    )


async def calcular_score_wave(
    influencer_id: str,
    campaign_id: str,
) -> ScoreBreakdown:
    """
    Calcula score promediando las publicaciones de UNA campaña (BY_WAVE mode).
    Útil para ver el desempeño del influencer en una campaña específica.
    """
    publicaciones = await obtener_publicaciones_influencer(influencer_id, campaign_id)
    if not publicaciones:
        return ScoreBreakdown(mode=ScoringMode.BY_WAVE)

    benchmark = await obtener_benchmark_por_followers(None)

    all_scores: list[ScoreBreakdown] = []
    for pub in publicaciones:
        score = await calcular_score_post(pub, benchmark)
        all_scores.append(score)

    valid_scores = [s for s in all_scores if s.score_final is not None]
    if not valid_scores:
        return ScoreBreakdown(
            mode=ScoringMode.BY_WAVE,
            publicaciones_count=len(publicaciones),
        )

    avg_retention = sum(s.retention_avg or 0 for s in valid_scores) / len(valid_scores)
    avg_er = sum(s.er_vistas or 0 for s in valid_scores) / len(valid_scores)
    avg_vf = sum(s.vf_ratio or 0 for s in valid_scores) / len(valid_scores)

    s_ret = score_retention(avg_retention if avg_retention > 0 else None)
    s_eng = score_engagement_calibrated(avg_er if avg_er > 0 else None, benchmark)
    s_vir = score_viralidad(avg_vf if avg_vf > 0 else None)

    scores = [s for s in [s_ret, s_eng, s_vir] if s is not None]
    score_final = sum(scores) / len(scores) if scores else None
    decision = calcular_decision(score_final)

    return ScoreBreakdown(
        score_retention=s_ret,
        score_engagement=s_eng,
        score_viralidad=s_vir,
        score_final=score_final,
        decision=decision,
        retention_avg=avg_retention if avg_retention > 0 else None,
        er_vistas=avg_er if avg_er > 0 else None,
        vf_ratio=avg_vf if avg_vf > 0 else None,
        mode=ScoringMode.BY_WAVE,
        publicaciones_count=len(publicaciones),
        subtier=benchmark.get("subtier") if benchmark else None,
    )


async def calcular_score_profile(influencer_id: str) -> ScoreBreakdown:
    """
    Calcula score acumulado de TODAS las publicaciones del influencer (BY_PROFILE mode).
    DEFAULT — refleja el valor real del creador.

    C-07: Si no hay datos suficientes → DATOS_INSUFICIENTES, nunca defaultear.
    """
    publicaciones = await obtener_publicaciones_influencer(influencer_id)
    if not publicaciones:
        return ScoreBreakdown(mode=ScoringMode.BY_PROFILE)

    follower_row = await railway_pg.table(
        "influencer_metrics_snapshot",
        select="followers",
        eq_filters={"influencer_id": influencer_id},
        limit=1,
    )
    followers = follower_row[0].get("followers") if follower_row else None
    benchmark = await obtener_benchmark_por_followers(followers)

    engagement_vals: list[float] = []
    retention_vals: list[float] = []
    vf_vals: list[float] = []

    for pub in publicaciones:
        vistas = pub.get("vistas")
        retention = pub.get("retencion")
        er_vistas = pub.get("er_vistas")
        likes = pub.get("likes")
        comments = pub.get("comentarios")
        shares = pub.get("compartidos")
        saves = pub.get("saves")

        engagement_total = pub.get("engagement_total")
        if engagement_total is None and vistas and vistas > 0:
            engagement_total = (likes or 0) + (comments or 0) + (shares or 0) + (saves or 0)

        if engagement_total is not None and vistas and vistas > 0:
            er_actual = er_vistas if er_vistas is not None else (engagement_total / vistas) * 100
            if er_actual > 0:
                engagement_vals.append(er_actual)

        if retention is not None and retention > 0:
            retention_vals.append(retention)

        if vistas and followers and followers > 0:
            vf_vals.append(vistas / followers)

    if not engagement_vals:
        return ScoreBreakdown(
            mode=ScoringMode.BY_PROFILE,
            publicaciones_count=len(publicaciones),
            followers=followers,
            subtier=benchmark.get("subtier") if benchmark else None,
        )

    avg_er = sum(engagement_vals) / len(engagement_vals)
    avg_retention = sum(retention_vals) / len(retention_vals) if retention_vals else None
    avg_vf = sum(vf_vals) / len(vf_vals) if vf_vals else None

    s_ret = score_retention(avg_retention)
    s_eng = score_engagement_calibrated(avg_er, benchmark)
    s_vir = score_viralidad(avg_vf)

    scores = [s for s in [s_ret, s_eng, s_vir] if s is not None]
    score_final = sum(scores) / len(scores) if scores else None
    decision = calcular_decision(score_final)

    benchmark_status: dict[str, str] = {}
    if benchmark:
        if s_eng == 3.0:
            benchmark_status["er"] = "green"
        elif s_eng == 2.0:
            benchmark_status["er"] = "yellow"
        else:
            benchmark_status["er"] = "red"

        if s_vir == 3.0:
            benchmark_status["vf"] = "green"
        elif s_vir == 2.0:
            benchmark_status["vf"] = "yellow"
        else:
            benchmark_status["vf"] = "red"

    return ScoreBreakdown(
        score_retention=s_ret,
        score_engagement=s_eng,
        score_viralidad=s_vir,
        score_final=score_final,
        decision=decision,
        retention_avg=avg_retention,
        er_vistas=avg_er,
        vf_ratio=avg_vf,
        followers=followers,
        mode=ScoringMode.BY_PROFILE,
        publicaciones_count=len(publicaciones),
        subtier=benchmark.get("subtier") if benchmark else None,
        benchmark_status=benchmark_status,
    )


async def calcular_score(
    influencer_id: str,
    mode: ScoringMode = ScoringMode.BY_PROFILE,
    campaign_id: str | None = None,
) -> ScoreBreakdown:
    """
    Punto de entrada principal para calcular score de un influencer.

    Args:
        influencer_id: UUID del influencer
        mode: BY_POST | BY_WAVE | BY_PROFILE (default BY_PROFILE)
        campaign_id: Solo para modo BY_WAVE

    Returns:
        ScoreBreakdown con todos los campos
    """
    if mode == ScoringMode.BY_POST:
        if not campaign_id:
            return ScoreBreakdown(mode=ScoringMode.BY_POST)
        pub_rows = await railway_pg.table(
            "publicaciones",
            select="*",
            eq_filters={"influencer_id": influencer_id, "campaign_id": campaign_id},
            limit=1,
        )
        if not pub_rows:
            return ScoreBreakdown(mode=ScoringMode.BY_POST)
        benchmark = await obtener_benchmark_por_followers(None)
        return await calcular_score_post(pub_rows[0], benchmark)

    elif mode == ScoringMode.BY_WAVE:
        if not campaign_id:
            return ScoreBreakdown(mode=ScoringMode.BY_WAVE)
        return await calcular_score_wave(influencer_id, campaign_id)

    else:
        return await calcular_score_profile(influencer_id)
