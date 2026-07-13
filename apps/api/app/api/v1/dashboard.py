"""Dashboard endpoints - using Supabase REST API."""
from decimal import Decimal
from fastapi import APIRouter, Query
from app.core.supabase_rest import supabase_rest
from app.core.security import CurrentUserDep
from app.schemas import DashboardKPIs

router = APIRouter()


@router.get("/summary", response_model=DashboardKPIs)
async def summary(user: CurrentUserDep):
    """Returns aggregated KPIs for the executive dashboard."""
    campaigns = await supabase_rest.table("campaigns", select="status,budget_total")
    clients = await supabase_rest.table("clients", select="id", is_null_filters=["deleted_at"])
    brands = await supabase_rest.table("brands", select="id", is_null_filters=["deleted_at"])
    influencers = await supabase_rest.table("influencers", select="id", is_null_filters=["deleted_at"])

    total_campaigns = len(campaigns)
    active_campaigns = sum(1 for c in campaigns if c.get("status") not in ("TERMINADA", "CANCELADA"))
    completed_campaigns = sum(1 for c in campaigns if c.get("status") == "TERMINADA")
    total_clients = len(clients)
    total_brands = len(brands)
    total_influencers = len(influencers)
    total_budget_usd = sum(Decimal(str(c.get("budget_total") or 0)) for c in campaigns)

    kpi_values = await supabase_rest.table(
        "campaign_kpi_values",
        select="value,kpi_definition_id",
        limit=10000,
    )
    kpi_defs_resp = await supabase_rest.table("kpi_definitions", select="id,code", limit=500)
    kpi_defs = {str(k["id"]): k["code"] for k in kpi_defs_resp}

    reach_values = [v["value"] for v in kpi_values if kpi_defs.get(str(v["kpi_definition_id"])) == "reach" and v["value"] is not None]
    engagement_values = [v["value"] for v in kpi_values if kpi_defs.get(str(v["kpi_definition_id"])) == "engagement_rate" and v["value"] is not None]

    total_reach = int(sum(reach_values)) if reach_values else 0
    avg_engagement_rate = Decimal(str(sum(engagement_values) / len(engagement_values))) if engagement_values else None

    try:
        all_pubs = await supabase_rest.table(
            "publicaciones",
            select="id,campaign_id,sentimiento_positivo,sentimiento_neutro,sentimiento_negativo,comentarios_analizados",
            limit=10000,
        )
        pubs_with_sentiment = [p for p in all_pubs if p.get("comentarios_analizados")]
        publicaciones_analizadas = len(pubs_with_sentiment)
        campanas_ids = set(str(p.get("campaign_id")) for p in pubs_with_sentiment if p.get("campaign_id"))
        campanas_analizadas = len(campanas_ids)

        sentiment_scores = []
        for p in pubs_with_sentiment:
            pos = int(p.get("sentimiento_positivo") or 0)
            neu = int(p.get("sentimiento_neutro") or 0)
            neg = int(p.get("sentimiento_negativo") or 0)
            total = pos + neu + neg
            if total > 0:
                sentiment_scores.append((pos - neg) / total)
        sentimiento_promedio = Decimal(str(sum(sentiment_scores) / len(sentiment_scores))) if sentiment_scores else None
    except Exception:
        import structlog
        logger = structlog.get_logger()
        logger.error("sentiment_kpi_query_failed", error="fallback to zero values")
        publicaciones_analizadas = 0
        campanas_analizadas = 0
        sentimiento_promedio = None

    return DashboardKPIs(
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        completed_campaigns=completed_campaigns,
        total_clients=total_clients,
        total_brands=total_brands,
        total_influencers=total_influencers,
        total_budget_usd=total_budget_usd,
        total_reach=total_reach,
        avg_engagement_rate=avg_engagement_rate,
        publicaciones_analizadas=publicaciones_analizadas,
        campanas_analizadas=campanas_analizadas,
        sentimiento_promedio=sentimiento_promedio,
    )


@router.get("/by-status")
async def by_status(user: CurrentUserDep):
    """Campaigns grouped by status (counts + budget)."""
    campaigns = await supabase_rest.table("campaigns", select="status,budget_total", limit=10000)
    status_map: dict[str, dict] = {}
    for c in campaigns:
        s = c.get("status") or "UNKNOWN"
        if s not in status_map:
            status_map[s] = {"status": s, "count": 0, "total_budget": Decimal("0")}
        status_map[s]["count"] += 1
        status_map[s]["total_budget"] += Decimal(str(c.get("budget_total") or 0))
    return list(status_map.values())


@router.get("/top-clients")
async def top_clients(user: CurrentUserDep, limit: int = Query(10, ge=1, le=100)):
    """Top clients by number of campaigns and total budget."""
    clients = await supabase_rest.table("clients", select="id,code,name", is_null_filters=["deleted_at"], limit=500)
    campaigns = await supabase_rest.table("campaigns", select="client_id,budget_total", is_null_filters=["deleted_at"], limit=10000)

    campaign_count_by_client: dict[str, int] = {}
    budget_by_client: dict[str, Decimal] = {}
    for c in campaigns:
        cid = str(c.get("client_id") or "")
        if cid not in campaign_count_by_client:
            campaign_count_by_client[cid] = 0
            budget_by_client[cid] = Decimal("0")
        campaign_count_by_client[cid] += 1
        budget_by_client[cid] += Decimal(str(c.get("budget_total") or 0))

    client_rows = []
    for cl in clients:
        cid = str(cl["id"])
        client_rows.append({
            "id": cid,
            "code": cl.get("code") or "",
            "name": cl.get("name") or "",
            "campaign_count": campaign_count_by_client.get(cid, 0),
            "total_budget": budget_by_client.get(cid, Decimal("0")),
        })

    client_rows.sort(key=lambda x: (x["campaign_count"], x["total_budget"]), reverse=True)
    return client_rows[:limit]
