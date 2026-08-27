"""
P.I.A.R. Benchmarks Engine — Comparación contra benchmarks LWFA.

Basado en: 06_informe_tecnico_audit_ism.md §6

Compara los KPIs reales de un influencer o publicación contra los
benchmarks LWFA (9 sub-tier) y retorna un semáforo:
    green  = dentro del rango esperado
    yellow = ±20% fuera del rango
    red    = muy fuera del rango

Los benchmarks LWFA son del mercado venezolano/LATAM real, no genéricos.
"""

from dataclasses import dataclass
from typing import Any

import structlog
from shared_core import railway_pg

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkStatus:
    er_status: str = "unknown"   # green | yellow | red | unknown
    vf_status: str = "unknown"
    cpv_status: str = "unknown"
    overall: str = "unknown"
    subtier: str | None = None
    role_description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "er_status": self.er_status,
            "vf_status": self.vf_status,
            "cpv_status": self.cpv_status,
            "overall": self.overall,
            "subtier": self.subtier,
            "role_description": self.role_description,
        }


async def get_all_benchmarks() -> list[dict[str, Any]]:
    """Obtiene todos los benchmarks LWFA desde Supabase."""
    rows = await railway_pg.table("tier_benchmarks", select="*", limit=20)
    return rows


async def get_benchmark_by_subtier(subtier: str) -> dict[str, Any] | None:
    """Obtiene un benchmark específico por sub-tier."""
    rows = await railway_pg.table(
        "tier_benchmarks",
        select="*",
        eq_filters={"subtier": subtier},
        limit=1,
    )
    return rows[0] if rows else None


async def get_benchmark_by_followers(followers: int | None) -> dict[str, Any] | None:
    """Resuelve el benchmark más apropiado para un follower count."""
    if followers is None:
        return None
    rows = await railway_pg.table("tier_benchmarks", select="*", limit=20)
    for row in rows:
        fmin = int(row.get("followers_min") or 0)
        fmax = int(row.get("followers_max") or 0)
        if fmin <= followers <= fmax:
            return row
    return rows[0] if rows else None


def _semaphore(actual: float | None, min_val: float, max_val: float) -> str:
    """
    Retorna green/yellow/red según la posición del valor vs el rango.
    green  = dentro del rango [min, max]
    yellow = a ±20% del rango
    red    = fuera del rango por más de ±20%
    """
    if actual is None:
        return "unknown"

    if min_val <= actual <= max_val:
        return "green"

    lower_thresh = min_val * 0.8
    upper_thresh = max_val * 1.2

    if lower_thresh <= actual <= upper_thresh:
        return "yellow"

    return "red"


def _semaphore_cpv(actual: float | None, ideal: float) -> str:
    """
    Semáforo para CPV: compara contra el CPV ideal del benchmark.
    green  = dentro de ±20% del ideal
    yellow = entre 20% y 50% del ideal
    red    = más de 50% sobre el ideal (sobreprecio)
    """
    if actual is None:
        return "unknown"

    if ideal <= 0:
        return "unknown"

    ratio = actual / ideal

    if ratio <= 1.2:
        return "green"
    if ratio <= 1.5:
        return "yellow"
    return "red"


def compare_with_benchmark(
    actual_er: float | None,
    actual_vf: float | None,
    actual_cpv: float | None,
    benchmark: dict[str, Any],
) -> BenchmarkStatus:
    """
    Compara KPIs reales contra un benchmark LWFA específico.

    Args:
        actual_er:   ER sobre vistas en %
        actual_vf:   V/F ratio (views / followers)
        actual_cpv:  Costo por engagement en USD
        benchmark:   Fila de tier_benchmarks
    """
    er_min = float(benchmark.get("er_min") or 0)
    er_max = float(benchmark.get("er_max") or 0)
    vf_min = float(benchmark.get("vf_min") or 0)
    vf_max = float(benchmark.get("vf_max") or 0)
    cpv_ideal = float(benchmark.get("cpv_ideal") or 0)

    er_status = _semaphore(actual_er, er_min, er_max)
    vf_status = _semaphore(actual_vf, vf_min, vf_max)
    cpv_status = _semaphore_cpv(actual_cpv, cpv_ideal)

    statuses = [er_status, vf_status]
    if cpv_status != "unknown":
        statuses.append(cpv_status)

    green_count = statuses.count("green")
    yellow_count = statuses.count("yellow")
    red_count = statuses.count("red")

    if red_count > 0:
        overall = "red"
    elif yellow_count > 0:
        overall = "yellow"
    elif green_count == len(statuses):
        overall = "green"
    else:
        overall = "unknown"

    return BenchmarkStatus(
        er_status=er_status,
        vf_status=vf_status,
        cpv_status=cpv_status,
        overall=overall,
        subtier=str(benchmark.get("subtier") or ""),
        role_description=str(benchmark.get("role_description") or ""),
    )


async def get_benchmark_status_for_influencer(
    influencer_id: str,
) -> tuple[BenchmarkStatus, dict[str, Any] | None]:
    """
    Obtiene el benchmark status para un influencer completo.

    1. Obtiene el follower count más reciente del snapshot
    2. Resuelve el benchmark correspondiente
    3. Calcula los promedios de ER y V/F de sus publicaciones
    4. Retorna el semáforo
    """
    snapshot_rows = await railway_pg.table(
        "influencer_metrics_snapshot",
        select="followers",
        eq_filters={"influencer_id": influencer_id},
        order="snapshot_date.desc",
        limit=1,
    )
    followers = snapshot_rows[0].get("followers") if snapshot_rows else None

    benchmark = await get_benchmark_by_followers(followers)
    if not benchmark:
        return BenchmarkStatus(), None

    pub_rows = await railway_pg.table(
        "publicaciones",
        select="er_vistas,vistas,likes,comentarios,guardados,compartidos",
        eq_filters={"influencer_id": influencer_id},
        limit=1000,
    )

    if not pub_rows:
        return compare_with_benchmark(None, None, None, benchmark), benchmark

    er_vals = [float(p["er_vistas"]) for p in pub_rows if p.get("er_vistas") is not None]
    avg_er = sum(er_vals) / len(er_vals) if er_vals else None

    vf_vals = []
    for p in pub_rows:
        vistas = p.get("vistas")
        if vistas and followers and followers > 0:
            vf_vals.append(float(vistas) / float(followers))

    avg_vf = sum(vf_vals) / len(vf_vals) if vf_vals else None

    status = compare_with_benchmark(avg_er, avg_vf, None, benchmark)
    return status, benchmark


async def get_all_benchmarks_formatted() -> list[dict[str, Any]]:
    """Retorna todos los benchmarks formateados para la UI."""
    rows = await get_all_benchmarks()
    return [
        {
            "subtier": row["subtier"],
            "followers_range": f"{row['followers_min']:,} – {row['followers_max']:,}",
            "vf_range": f"{row['vf_min']}x – {row['vf_max']}x",
            "er_range": f"{row['er_min']}% – {row['er_max']}%",
            "cpv_ideal": f"${row['cpv_ideal']:.4f}",
            "role": row.get("role_description", ""),
        }
        for row in rows
    ]
