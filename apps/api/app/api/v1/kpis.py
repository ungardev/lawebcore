"""KPIs endpoints: definitions + campaign KPI values."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared_core import get_db
from app.core.security import CurrentUserDep
from app.schemas import KPIRead, KPIValueCreate

router = APIRouter()


@router.get("/definitions", response_model=list[KPIRead])
async def list_definitions(user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM kpi_definitions WHERE is_active = TRUE ORDER BY category, name"))
    return [KPIRead.model_validate(r) for r in result.mappings().all()]


@router.post("/values")
async def record_kpi_value(
    payload: KPIValueCreate,
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    # Look up kpi_definition by code
    kd = (await db.execute(text("SELECT id FROM kpi_definitions WHERE code = :code"), {"code": payload.kpi_code})).mappings().first()
    if not kd:
        raise HTTPException(status_code=400, detail=f"Unknown kpi_code: {payload.kpi_code}")

    sql = text("""
        INSERT INTO campaign_kpi_values (campaign_id, kpi_definition_id, value, period_start, period_end, source, notes, recorded_by)
        VALUES (:campaign_id, :kpi_id, :value, :period_start, :period_end, :source, :notes, :recorded_by)
        ON CONFLICT (campaign_id, kpi_definition_id, period_start, period_end, source) DO UPDATE
        SET value = EXCLUDED.value, recorded_at = NOW()
        RETURNING *
    """)
    params = payload.model_dump()
    params["kpi_id"] = str(kd["id"])
    params["campaign_id"] = str(payload.campaign_id)
    params["recorded_by"] = str(user.id)
    result = await db.execute(sql, params)
    await db.commit()
    return {"status": "recorded", "value_id": str(result.mappings().first()["id"])}


@router.get("/benchmarks")
async def get_benchmarks(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    kpi_code: str | None = None,
    scope_type: str | None = None,
):
    """Returns benchmarks, optionally filtered by KPI and scope."""
    sql = """
        SELECT b.*, kd.code AS kpi_code, kd.name AS kpi_name
        FROM benchmarks b
        JOIN kpi_definitions kd ON kd.id = b.kpi_definition_id
        WHERE b.is_active = TRUE
    """
    params: dict = {}
    if kpi_code:
        sql += " AND kd.code = :kpi_code"
        params["kpi_code"] = kpi_code
    if scope_type:
        sql += " AND b.scope_type = :scope_type"
        params["scope_type"] = scope_type
    sql += " ORDER BY b.scope_type, kd.code"
    result = await db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]