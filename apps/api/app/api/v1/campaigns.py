"""Campaigns endpoints - CRUD + Kanban + Status changes + KPIs + links."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import CurrentUserDep
from app.schemas import (
    CampaignRead, CampaignCreate, CampaignUpdate,
    CampaignStatusChange, CampaignDetail, CampaignLinkRead,
    CampaignKPIRead, InsightRead,
)

router = APIRouter()

VALID_STATUSES = {"BRIEF", "CONTACTANDO", "PLAN_DE_CUENTAS", "PULL", "CAMPAÑA INTERNA", "REPORTE", "TERMINADA", "CANCELADA", "PAUSADA"}


@router.get("", response_model=list[CampaignRead], summary="List campaigns")
async def list_campaigns(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    client_id: str | None = Query(None),
    brand_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    objective: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(100, le=500),
):
    """List campaigns with filters. Returns lightweight projection."""
    params: dict = {"limit": limit}
    where = ["c.deleted_at IS NULL"]
    if client_id:
        where.append("c.client_id = :client_id"); params["client_id"] = client_id
    if brand_id:
        where.append("c.brand_id = :brand_id"); params["brand_id"] = brand_id
    if status_filter:
        where.append("c.status = :status"); params["status"] = status_filter
    if objective:
        where.append("c.objective = :objective"); params["objective"] = objective
    if search:
        where.append("(c.name ILIKE :search OR c.code ILIKE :search)")
        params["search"] = f"%{search}%"

    sql = f"""
        SELECT c.* FROM campaigns c
        WHERE {' AND '.join(where)}
        ORDER BY c.updated_at DESC
        LIMIT :limit
    """
    result = await db.execute(text(sql), params)
    return [CampaignRead.model_validate(r) for r in result.mappings().all()]


@router.get("/kanban", summary="Campaigns grouped by status (Kanban)")
async def kanban_view(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    client_id: str | None = Query(None),
    brand_id: str | None = Query(None),
):
    """Returns campaigns grouped by status, for the Kanban board."""
    params: dict = {}
    where = ["deleted_at IS NULL"]
    if client_id:
        where.append("client_id = :client_id"); params["client_id"] = client_id
    if brand_id:
        where.append("brand_id = :brand_id"); params["brand_id"] = brand_id
    sql = f"""
        SELECT id, code, name, status, objective, brand_id, client_id,
               num_influencers, budget_total, end_date, updated_at
        FROM campaigns
        WHERE {' AND '.join(where)}
        ORDER BY updated_at DESC
    """
    result = await db.execute(text(sql), params)
    rows = result.mappings().all()

    # Group by status
    columns: dict[str, list] = {s: [] for s in VALID_STATUSES}
    for r in rows:
        s = r["status"]
        if s not in columns:
            columns[s] = []
        columns[s].append({
            "id": str(r["id"]),
            "code": r["code"],
            "name": r["name"],
            "objective": r["objective"],
            "client_id": str(r["client_id"]),
            "brand_id": str(r["brand_id"]),
            "num_influencers": r["num_influencers"],
            "budget_total": float(r["budget_total"]) if r["budget_total"] else None,
            "end_date": r["end_date"].isoformat() if r["end_date"] else None,
            "updated_at": r["updated_at"].isoformat(),
        })
    return {"columns": columns, "total": len(rows)}


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(campaign_id: str, user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    sql = text("SELECT * FROM campaigns WHERE id = :id AND deleted_at IS NULL")
    result = await db.execute(sql, {"id": campaign_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign = CampaignRead.model_validate(row)

    # Brand
    brand = (await db.execute(text("SELECT * FROM brands WHERE id = :id"), {"id": str(campaign.brand_id)})).mappings().first()
    # Client
    client = (await db.execute(text("SELECT * FROM clients WHERE id = :id"), {"id": str(campaign.client_id)})).mappings().first()
    # KPIs
    kpi_sql = text("""
        SELECT kd.code AS kpi_code, kd.name AS kpi_name, kd.category, ckv.value, ckv.source, ckv.recorded_at
        FROM campaign_kpi_values ckv
        JOIN kpi_definitions kd ON kd.id = ckv.kpi_definition_id
        WHERE ckv.campaign_id = :id
        ORDER BY kd.category, kd.name
    """)
    kpis = (await db.execute(kpi_sql, {"id": campaign_id})).mappings().all()
    # Links
    links = (await db.execute(text("SELECT * FROM campaign_links WHERE campaign_id = :id ORDER BY link_type"), {"id": campaign_id})).mappings().all()
    # Insights
    insights = (await db.execute(text("SELECT * FROM insights WHERE campaign_id = :id ORDER BY created_at DESC"), {"id": campaign_id})).mappings().all()

    return CampaignDetail(
        **campaign.model_dump(),
        brand=brand,
        client=client,
        kpis=[CampaignKPIRead(**dict(k)) for k in kpis],
        links=[CampaignLinkRead(**dict(l)) for l in links],
        insights=[InsightRead(**dict(i)) for i in insights],
    )


@router.post("", response_model=CampaignRead, status_code=201)
async def create_campaign(payload: CampaignCreate, user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    # Auto-generate code
    count_sql = text("SELECT COUNT(*) AS c FROM campaigns WHERE code LIKE 'CAMP-%'")
    count = (await db.execute(count_sql)).scalar() or 0
    code = f"CAMP-{count + 1:04d}"

    sql = text("""
        INSERT INTO campaigns (
            code, client_id, brand_id, name, objective, campaign_type,
            secondary_objectives, influencer_tiers, start_date, end_date,
            budget_total, num_influencers, target_audience, tags, notes,
            owner_user_id, created_by, business_unit_id
        )
        VALUES (
            :code, :client_id, :brand_id, :name, :objective, :campaign_type,
            :secondary_objectives, :influencer_tiers, :start_date, :end_date,
            :budget_total, :num_influencers, :target_audience, :tags, :notes,
            :owner_user_id, :created_by, '00000000-0000-0000-0000-000000000003'::uuid
        )
        RETURNING *
    """)
    params = payload.model_dump()
    params["code"] = code
    params["secondary_objectives"] = list(payload.secondary_objectives)
    params["influencer_tiers"] = list(payload.influencer_tiers)
    params["tags"] = list(payload.tags)
    params["owner_user_id"] = str(user.id)
    params["created_by"] = str(user.id)
    # Convert UUIDs to str for asyncpg
    params["client_id"] = str(payload.client_id)
    params["brand_id"] = str(payload.brand_id)
    try:
        result = await db.execute(sql, params)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create campaign: {e}")
    return CampaignRead.model_validate(result.mappings().first())


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return await get_campaign(campaign_id, user, db)

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    sql = text(f"UPDATE campaigns SET {set_clauses} WHERE id = :id RETURNING *")
    updates["id"] = campaign_id
    result = await db.execute(sql, updates)
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CampaignRead.model_validate(row)


@router.post("/{campaign_id}/status", response_model=CampaignRead, summary="Change status")
async def change_status(
    campaign_id: str,
    payload: CampaignStatusChange,
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    if payload.to_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {sorted(VALID_STATUSES)}")
    # History trigger inserts a row automatically; we just update status
    sql = text("""
        UPDATE campaigns SET status = :status WHERE id = :id RETURNING *
    """)
    result = await db.execute(sql, {"status": payload.to_status, "id": campaign_id})
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CampaignRead.model_validate(row)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: str, user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    await db.execute(text("UPDATE campaigns SET deleted_at = NOW() WHERE id = :id"), {"id": campaign_id})
    await db.commit()
    return None