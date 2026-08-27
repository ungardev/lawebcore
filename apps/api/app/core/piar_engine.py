"""
P.I.A.R Projection Engine — Algoritmo de proyección por marca.

Metodología: promedio ponderado por tier + peso temporal.
Sin regresión estadística — con menos de 10 campañas por marca,
una regresión da resultados frágiles.

Ver: 04_motor_de_proyeccion.md
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from dateutil.relativedelta import relativedelta

from app.core.piar_constants import (
    ESCENARIOS,
    ESCENARIOS_CONSERVADOR_AJUSTADO,
    ESCENARIOS_OPTIMISTA_AJUSTADO,
    FACTOR_ALCANCE,
    MAX_CAMPANAS_CONSIDERADAS,
    MESES_RECIENTE,
    MIN_CAMPANAS_POR_MARCA,
    PESO_ANTIGUO,
    PESO_RECIENTE,
    TASA_VIRAL_ESPERADA,
    UMBRAL_DESCARTAR_PARA_AJUSTE,
    UMBRAL_ESCALAR_PARA_AJUSTE,
)

logger = structlog.get_logger(__name__)


class PiarEngine:
    """
    Motor de proyección P.I.A.R.
    Consulta Supabase REST API y aplica la metodología de promedio ponderado.
    """

    def __init__(self, supabase_rest_client: Any):
        self._rest = supabase_rest_client

    async def _determinar_ajuste_scoring(
        self,
        publicaciones: list[dict[str, Any]],
    ) -> tuple[dict[str, float], str, float | None]:
        """
        Analiza los influencers del histórico y determina el ajuste de escenarios.

        Returns:
            (escenarios_a_usar, decision_dominante, score_promedio)
        """
        influencer_ids = list({
            str(p.get("influencer_id")) for p in publicaciones
            if p.get("influencer_id")
        })

        if not influencer_ids:
            return ESCENARIOS, "SIN_DATOS", None

        try:
            from app.core.piar_scoring import ScoreDecision, ScoringMode, calcular_score
        except ImportError:
            return ESCENARIOS, "ERROR_IMPORT", None

        decisions: list[str] = []
        scores: list[float] = []

        for inf_id in influencer_ids[:20]:
            try:
                result = await calcular_score(inf_id, ScoringMode.BY_PROFILE)
                if result.decision != ScoreDecision.DATOS_INSUFICIENTES:
                    decisions.append(result.decision.value)
                    if result.score_final is not None:
                        scores.append(result.score_final)
            except Exception:
                continue

        if not decisions:
            return ESCENARIOS, "DATOS_INSUFICIENTES", None

        escalar_pct = decisions.count("ESCALAR") / len(decisions)
        optimizar_pct = decisions.count("OPTIMIZAR") / len(decisions)
        descartar_pct = decisions.count("DESCARTAR") / len(decisions)
        score_promedio = sum(scores) / len(scores) if scores else None

        if escalar_pct >= UMBRAL_ESCALAR_PARA_AJUSTE:
            return ESCENARIOS_OPTIMISTA_AJUSTADO, "ESCALAR", score_promedio
        if descartar_pct >= UMBRAL_DESCARTAR_PARA_AJUSTE:
            return ESCENARIOS_CONSERVADOR_AJUSTADO, "DESCARTAR", score_promedio
        if optimizar_pct >= 0.5:
            return ESCENARIOS, "OPTIMIZAR", score_promedio

        return ESCENARIOS, "MIXTO", score_promedio

    async def calcular_proyeccion(
        self,
        brand_id: str,
        posts_per_tier: dict[str, int],
        reference_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Calcula la proyección para una marca dada.

        Args:
            brand_id: UUID de la marca
            posts_per_tier: dict con distribución de posts por tier, ej. {"NANO": 10, "MICRO": 4}
            reference_date: fecha de referencia (default: ahora en UTC)

        Returns:
            dict con resultados por tier + totales en 3 escenarios + auditoría
            Incluye ajuste de escenarios según calidad de creadores del histórico.
        """
        if reference_date is None:
            reference_date = datetime.now(timezone.utc)

        brand_info = await self._get_brand_info(brand_id)
        client_id = brand_info["client_id"]
        industry = await self._get_industry(client_id)

        all_publicaciones: list[dict[str, Any]] = []
        resultados_por_tier: list[dict[str, Any]] = []

        for tier, num_posts in posts_per_tier.items():
            if num_posts <= 0:
                continue

            historico = await self._seleccionar_historico(brand_id, tier, industry, reference_date)
            all_publicaciones.extend(historico.get("publicaciones", []))

            if not historico["publicaciones"]:
                logger.warning(
                    "piar_no_data",
                    brand_id=brand_id,
                    tier=tier,
                    fuente=historico["fuente"],
                )

            promedios = self._calcular_promedio_ponderado(historico)
            escenarios = self._generar_escenarios(promedios, num_posts)

            resultados_por_tier.append({
                "tier": tier,
                "num_posts": num_posts,
                "fuente": historico["fuente"],
                "num_campanas": historico["num_campanas"],
                "tasas": {
                    "er_promedio": promedios.get("er"),
                    "retencion_promedio": promedios.get("retencion"),
                },
                "escenarios": escenarios,
            })

        escenarios_a_usar, decision_dominante, score_promedio = await self._determinar_ajuste_scoring(
            all_publicaciones
        )

        ajuste_aplicado = "base"
        if escenarios_a_usar is ESCENARIOS_OPTIMISTA_AJUSTADO:
            ajuste_aplicado = "optimista_ajustado"
        elif escenarios_a_usar is ESCENARIOS_CONSERVADOR_AJUSTADO:
            ajuste_aplicado = "conservador_ajustado"

        total_escenarios = self._agregar_escenarios(resultados_por_tier)

        return {
            "brand_id": brand_id,
            "brand_name": brand_info["name"],
            "client_id": client_id,
            "industry": industry,
            "reference_date": reference_date.isoformat(),
            "calidad_creadores": {
                "decision_dominante": decision_dominante,
                "score_promedio": round(score_promedio, 2) if score_promedio is not None else None,
                "ajuste_aplicado": ajuste_aplicado,
            },
            "resultados_por_tier": resultados_por_tier,
            "total": total_escenarios,
        }

    async def _seleccionar_historico(
        self,
        brand_id: str,
        tier: str,
        industry: str | None,
        reference_date: datetime,
    ) -> dict[str, Any]:
        """
        Selecciona el histórico según la regla:
        - Si ≥ MIN_CAMPANAS_POR_MARCA (3) campañas con publicaciones → usar marca
        - Si < 3 → fallback a sector (industry)
        """
        publicaciones_marca = await self._query_publicaciones(brand_id, tier)

        campanas_unicas_marca = self._campanas_unicas(publicaciones_marca)

        if len(campanas_unicas_marca) >= MIN_CAMPANAS_POR_MARCA:
            recientes = self._ordenar_por_fecha(publicaciones_marca)[:MAX_CAMPANAS_CONSIDERADAS]
            return {
                "publicaciones": recientes,
                "fuente": "marca",
                "num_campanas": len(self._campanas_unicas(recientes)),
            }

        if industry:
            publicaciones_sector = await self._query_publicaciones_por_industry(industry, tier)
            recientes = self._ordenar_por_fecha(publicaciones_sector)[:MAX_CAMPANAS_CONSIDERADAS]
            return {
                "publicaciones": recientes,
                "fuente": "sector",
                "num_campanas": len(self._campanas_unicas(recientes)),
            }

        return {
            "publicaciones": [],
            "fuente": "ninguno",
            "num_campanas": 0,
        }

    async def _query_publicaciones(
        self,
        brand_id: str,
        tier: str,
    ) -> list[dict[str, Any]]:
        """Query publicaciones para una marca + tier específico."""
        campaigns = await self._rest.table(
            "campaigns",
            select="id,start_date",
            eq_filters={"brand_id": brand_id},
            is_null_filters=["deleted_at"],
            limit=500,
        )
        campaign_ids = [str(c["id"]) for c in campaigns if c.get("id")]

        if not campaign_ids:
            return []

        influencers = await self._rest.table(
            "influencers",
            select="id",
            eq_filters={"primary_tier": tier},
            limit=5000,
        )
        influencer_ids = [str(i["id"]) for i in influencers if i.get("id")]

        if not influencer_ids:
            rows = await self._rest.table(
                "publicaciones",
                select="*,campaigns(start_date)",
                limit=5000,
            )
            return [r for r in rows if str(r.get("campaign_id", "")) in campaign_ids]

        rows = await self._rest.table(
            "publicaciones",
            select="*,campaigns(start_date)",
            limit=5000,
        )
        result = []
        for r in rows:
            cid = str(r.get("campaign_id", ""))
            iid = str(r.get("influencer_id") or "")
            if cid in campaign_ids and (not influencer_ids or iid in influencer_ids):
                result.append(r)
        return result

    async def _query_publicaciones_por_industry(
        self,
        industry: str,
        tier: str,
    ) -> list[dict[str, Any]]:
        """Query publicaciones para un sector completo + tier."""
        clients = await self._rest.table(
            "clients",
            select="id",
            eq_filters={"industry": industry},
            limit=500,
        )
        client_ids = [str(c["id"]) for c in clients if c.get("id")]

        if not client_ids:
            return []

        brands = await self._rest.table(
            "brands",
            select="id",
            limit=5000,
        )
        brand_ids = [str(b["id"]) for b in brands if str(b.get("client_id", "")) in client_ids and b.get("id")]

        if not brand_ids:
            return []

        campaigns = await self._rest.table(
            "campaigns",
            select="id",
            limit=5000,
        )
        campaign_ids = [
            str(c["id"]) for c in campaigns
            if str(c.get("brand_id", "")) in brand_ids
        ]

        if not campaign_ids:
            return []

        influencers = await self._rest.table(
            "influencers",
            select="id",
            eq_filters={"primary_tier": tier},
            limit=5000,
        )
        influencer_ids = [str(i["id"]) for i in influencers if i.get("id")]

        rows = await self._rest.table(
            "publicaciones",
            select="*,campaigns(start_date)",
            limit=5000,
        )
        result = []
        for r in rows:
            cid = str(r.get("campaign_id", ""))
            iid = str(r.get("influencer_id") or "")
            if cid in campaign_ids and (not influencer_ids or iid in influencer_ids):
                result.append(r)
        return result

    async def _get_brand_info(self, brand_id: str) -> dict[str, Any]:
        rows = await self._rest.table("brands", select="id,name,client_id", eq_filters={"id": brand_id})
        if not rows:
            return {"name": "Desconocida", "client_id": brand_id}
        return rows[0]

    async def _get_industry(self, client_id: str) -> str | None:
        rows = await self._rest.table("clients", select="industry", eq_filters={"id": client_id})
        if not rows:
            return None
        return rows[0].get("industry") or None

    def _campanas_unicas(self, publicaciones: list[dict[str, Any]]) -> set[str]:
        return {str(p.get("campaign_id", "")) for p in publicaciones if p.get("campaign_id")}

    def _ordenar_por_fecha(
        self,
        publicaciones: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Ordena por fecha_publicacion descendente, toma las MAX_CAMPANAS_CONSIDERADAS campañas más recientes."""

        def get_date(p: dict[str, Any]) -> datetime:
            raw = p.get("fecha_publicacion")
            if isinstance(raw, datetime):
                return raw
            if isinstance(raw, str):
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    return datetime.min
            return datetime.min

        sorted_pubs = sorted(publicaciones, key=get_date, reverse=True)

        seen_campaigns: set[str] = set()
        result: list[dict[str, Any]] = []
        for p in sorted_pubs:
            cid = str(p.get("campaign_id", ""))
            if cid and cid not in seen_campaigns:
                if len(seen_campaigns) >= MAX_CAMPANAS_CONSIDERADAS:
                    break
                seen_campaigns.add(cid)
            result.append(p)

        return result

    def _calcular_promedio_ponderado(self, historico: dict[str, Any]) -> dict[str, float | None]:
        """
        Calcula promedios ponderados de er y retencion.
        Peso temporal: 1.5 para campañas en los últimos 6 meses, 1.0 para más antiguas.
        Valores N/A se ignoran (no se tratan como 0).
        """
        publicaciones = historico.get("publicaciones", [])
        if not publicaciones:
            return {"er": None, "retencion": None, "vistas_promedio": None}

        ahora = datetime.now(timezone.utc)
        cutoff = ahora - relativedelta(months=MESES_RECIENTE)

        total_er_weighted: float = 0.0
        total_retencion_weighted: float = 0.0
        total_vistas_weighted: float = 0.0
        total_weight: float = 0.0

        for p in publicaciones:
            campaign_start_raw = None
            if isinstance(p.get("campaigns"), dict):
                campaign_start_raw = p["campaigns"].get("start_date")
            elif isinstance(p.get("campaigns"), list) and p.get("campaigns"):
                campaign_start_raw = p["campaigns"][0].get("start_date") if isinstance(p["campaigns"][0], dict) else None

            campaign_date: datetime | None = None
            if campaign_start_raw:
                if isinstance(campaign_start_raw, str):
                    try:
                        campaign_date = datetime.fromisoformat(campaign_start_raw.replace("Z", "+00:00"))
                    except ValueError:
                        campaign_date = None
                elif isinstance(campaign_start_raw, datetime):
                    campaign_date = campaign_start_raw

            peso = PESO_RECIENTE if (campaign_date and campaign_date >= cutoff) else PESO_ANTIGUO

            er = p.get("er_alcance") or p.get("er_vistas")
            if er is not None and er != "N/A":
                try:
                    total_er_weighted += float(er) * peso
                except (ValueError, TypeError):
                    pass

            retencion = p.get("retencion")
            if retencion is not None and retencion != "N/A":
                try:
                    total_retencion_weighted += float(retencion) * peso
                except (ValueError, TypeError):
                    pass

            vistas = p.get("vistas")
            if vistas is not None and vistas != "N/A":
                try:
                    total_vistas_weighted += float(vistas) * peso
                except (ValueError, TypeError):
                    pass

            total_weight += peso

        if total_weight == 0:
            return {"er": None, "retencion": None, "vistas_promedio": None}

        return {
            "er": total_er_weighted / total_weight,
            "retencion": total_retencion_weighted / total_weight,
            "vistas_promedio": total_vistas_weighted / total_weight,
        }

    def _generar_escenarios(
        self,
        promedios: dict[str, float | None],
        num_posts: int,
    ) -> dict[str, dict[str, Any]]:
        """
        Genera 3 escenarios multiplicando solo los volúmenes.
        Las tasas (ER, retención) NO se escalan — solo el volumen cambia.
        """
        er = promedios.get("er") or 0.0
        vistas_promedio = promedios.get("vistas_promedio") or 0.0
        retencion = promedios.get("retencion")

        escenarios: dict[str, dict[str, Any]] = {}

        for nombre, factor in ESCENARIOS.items():
            vistas = vistas_promedio * factor * num_posts
            alcance = vistas * FACTOR_ALCANCE
            engagement = alcance * er
            posts_virales = round(num_posts * TASA_VIRAL_ESPERADA * factor)

            escenarios[nombre] = {
                "vistas_proyectadas": round(vistas),
                "alcance_proyectado": round(alcance),
                "engagement_proyectado": round(engagement),
                "posts_virales_esperados": posts_virales,
            }

        return escenarios

    def _agregar_escenarios(
        self,
        resultados_por_tier: list[dict[str, Any]],
    ) -> dict[str, dict[str, int]]:
        """Agrega los totales de todos los tiers para cada escenario."""
        totales: dict[str, dict[str, int]] = {
            "conservador": {"vistas": 0, "alcance": 0, "engagement": 0, "posts_virales": 0},
            "base": {"vistas": 0, "alcance": 0, "engagement": 0, "posts_virales": 0},
            "optimista": {"vistas": 0, "alcance": 0, "engagement": 0, "posts_virales": 0},
        }

        for resultado in resultados_por_tier:
            for escenario_nombre, valores in resultado["escenarios"].items():
                totales[escenario_nombre]["vistas"] += valores["vistas_proyectadas"]
                totales[escenario_nombre]["alcance"] += valores["alcance_proyectado"]
                totales[escenario_nombre]["engagement"] += valores["engagement_proyectado"]
                totales[escenario_nombre]["posts_virales"] += valores["posts_virales_esperados"]

        return totales
