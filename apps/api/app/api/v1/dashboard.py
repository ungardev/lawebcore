"""Dashboard endpoints - aggregated KPIs."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import CurrentUserDep
from app.schemas import DashboardKPIs

router = APIRouter()


@router.get("/summary", response_model=DashboardKPIs)
async def summary(user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    """Returns aggregated KPIs for the executive dashboard."""
    sql = text("""
        SELECT
          (SELECT COUNT(*) FROM campaigns WHERE deleted_at IS NULL) AS total_campaigns,
          (SELECT COUNT(*) FROM campaigns WHERE deleted_at IS NULL AND status NOT IN ('TERMINADA','CANCELADA')) AS active_campaigns,
          (SELECT COUNT(*) FROM campaigns WHERE deleted_at IS NULL AND status = 'TERMINADA') AS completed_campaigns,
          (SELECT COUNT(*) FROM clients WHERE deleted_at IS NULL) AS total_clients,
          (SELECT COUNT(*) FROM brands WHERE deleted_at IS NULL) AS total_brands,
          (SELECT COUNT(*) FROM influencers WHERE deleted_at IS NULL) AS total_influencers,
          (SELECT COALESCE(SUM(budget_total), 0) FROM campaigns WHERE deleted_at IS NULL) AS total_budget_usd,
          (SELECT COALESCE(SUM(ckv.value), 0)
             FROM campaign_kpi_values ckv
             JOIN kpi_definitions kd ON kd.id = ckv.kpi_definition_id
             WHERE kd.code = 'reach') AS total_reach,
          (SELECT AVG(ckv.value) FROM campaign_kpi_values ckv
             JOIN kpi_definitions kd ON kd.id = ckv.kpi_definition_id
             WHERE kd.code = 'engagement_rate') AS avg_engagement_rate
    """)
    row = (await db.execute(sql)).mappings().first()
    return DashboardKPIs(**dict(row))


@router.get("/by-status")
async def by_status(user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    """Campaigns grouped by status (counts + budget)."""
    sql = text("""
        SELECT status, COUNT(*) AS count, COALESCE(SUM(budget_total), 0) AS total_budget
        FROM campaigns WHERE deleted_at IS NULL
        GROUP BY status ORDER BY status
    """)
    result = await db.execute(sql)
    return [dict(r) for r in result.mappings().all()]


@router.get("/top-clients")
async def top_clients(user: CurrentUserDep, db: AsyncSession = Depends(get_db), limit: int = 10):
    """Top clients by number of campaigns and total budget."""
    sql = text("""
        SELECT c.id, c.code, c.name,
               COUNT(camp.id) AS campaign_count,
               COALESCE(SUM(camp.budget_total), 0) AS total_budget
        FROM clients c
        LEFT JOIN campaigns camp ON camp.client_id = c.id AND camp.deleted_at IS NULL
        WHERE c.deleted_at IS NULL
        GROUP BY c.id, c.code, c.name
        ORDER BY campaign_count DESC, total_budget DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, {"limit": limit})
    return [dict(r) for r in result.mappings().all()]