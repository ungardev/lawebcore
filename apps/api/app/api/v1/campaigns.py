"""Campaigns endpoints - CRUD + Kanban + Status changes + KPIs + links."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query
from shared_core import railway_pg

from app.core.security import CurrentUserDep
from app.schemas import (
    CampaignCreate,
    CampaignDetail,
    CampaignKPIRead,
    CampaignLinkRead,
    CampaignRead,
    CampaignStatusChange,
    CampaignUpdate,
    InsightRead,
)

router = APIRouter()

VALID_STATUSES = {"BRIEF", "CONTACTANDO", "PLAN_DE_CUENTAS", "PULL", "CAMPAÑA INTERNA", "REPORTE", "TERMINADA", "CANCELADA", "PAUSADA"}


@router.get("", response_model=list[CampaignRead], summary="List campaigns")
async def list_campaigns(
    user: CurrentUserDep,
    client_id: str | None = Query(None),
    brand_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    objective: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(100, le=500),
):
    """List campaigns with filters. Returns lightweight projection."""
    all_rows = await railway_pg.table("campaigns", select="*", limit=10000)
    filtered = []
    for r in all_rows:
        if r.get("deleted_at") is not None:
            continue
        if client_id and str(r.get("client_id") or "") != client_id:
            continue
        if brand_id and str(r.get("brand_id") or "") != brand_id:
            continue
        if status_filter and r.get("status") != status_filter:
            continue
        if objective and r.get("objective") != objective:
            continue
        if search:
            name = (r.get("name") or "").lower()
            code = (r.get("code") or "").lower()
            if search.lower() not in name and search.lower() not in code:
                continue
        filtered.append(r)
    return [CampaignRead.model_validate(r) for r in filtered[:limit]]


@router.get("/kanban", summary="Campaigns grouped by status (Kanban)")
async def kanban_view(
    user: CurrentUserDep,
    client_id: str | None = Query(None),
    brand_id: str | None = Query(None),
):
    """Returns campaigns grouped by status, for the Kanban board."""
    rows = await railway_pg.table(
        "campaigns",
        select="id,code,name,status,objective,brand_id,client_id,num_influencers,budget_total,end_date,updated_at",
        is_null_filters=["deleted_at"],
        limit=10000,
        order="updated_at.desc",
    )

    columns: dict[str, list] = {s: [] for s in VALID_STATUSES}
    for r in rows:
        if client_id and str(r.get("client_id") or "") != client_id:
            continue
        if brand_id and str(r.get("brand_id") or "") != brand_id:
            continue
        s = r.get("status") or "UNKNOWN"
        if s not in columns:
            columns[s] = []
        columns[s].append({
            "id": str(r["id"]),
            "code": r.get("code") or "",
            "name": r.get("name") or "",
            "objective": r.get("objective") or "",
            "client_id": str(r.get("client_id") or ""),
            "brand_id": str(r.get("brand_id") or ""),
            "num_influencers": r.get("num_influencers") or 0,
            "budget_total": float(r.get("budget_total") or 0),
            "end_date": r.get("end_date"),
            "updated_at": r.get("updated_at"),
        })
    return {"columns": columns, "total": sum(len(v) for v in columns.values())}


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(campaign_id: str, user: CurrentUserDep):
    rows = await railway_pg.table(
        "campaigns",
        select="*",
        eq_filters={"id": campaign_id},
        is_null_filters=["deleted_at"],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign = rows[0]

    brand_rows = await railway_pg.table("brands", select="*", eq_filters={"id": str(campaign.get("brand_id") or "")})
    brand = brand_rows[0] if brand_rows else None

    client_rows = await railway_pg.table("clients", select="*", eq_filters={"id": str(campaign.get("client_id") or "")})
    client = client_rows[0] if client_rows else None

    kpi_values = await railway_pg.table(
        "campaign_kpi_values",
        select="value,kpi_definition_id,source,recorded_at",
        eq_filters={"campaign_id": campaign_id},
        limit=500,
    )
    kpi_defs_resp = await railway_pg.table("kpi_definitions", select="id,code,name,category", limit=500)
    kpi_defs = {str(k["id"]): k for k in kpi_defs_resp}

    kpis = []
    for v in kpi_values:
        kd = kpi_defs.get(str(v["kpi_definition_id"]) or {})
        if kd:
            kpis.append(CampaignKPIRead(
                kpi_code=kd.get("code") or "",
                kpi_name=kd.get("name") or "",
                category=kd.get("category") or "",
                value=v.get("value") or 0,
                source=v.get("source") or "",
                recorded_at=v.get("recorded_at") or "",
            ))

    links = await railway_pg.table(
        "campaign_links",
        select="*",
        eq_filters={"campaign_id": campaign_id},
        order="link_type",
    )

    insights = await railway_pg.table(
        "insights",
        select="*",
        eq_filters={"campaign_id": campaign_id},
        order="created_at.desc",
    )

    return CampaignDetail(
        **campaign,
        brand=brand,
        client=client,
        kpis=kpis,
        links=[CampaignLinkRead(**l) for l in links],
        insights=[InsightRead(**i) for i in insights],
    )


@router.post("", response_model=CampaignRead, status_code=201)
async def create_campaign(payload: CampaignCreate, user: CurrentUserDep):
    all_campaigns = await railway_pg.table("campaigns", select="code", limit=10000)
    camp_codes = [c.get("code") or "" for c in all_campaigns if c.get("code", "").startswith("CAMP-")]
    nums = [int(c.split("-")[1]) for c in camp_codes if c.split("-")[1].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    code = f"CAMP-{next_num:04d}"

    data = payload.model_dump()
    data["code"] = code
    data["owner_user_id"] = str(user.id)
    data["created_by"] = str(user.id)
    data["business_unit_id"] = str(user.business_unit_id) if user.business_unit_id else "00000000-0000-0000-0000-000000000003"
    data["client_id"] = str(payload.client_id)
    data["brand_id"] = str(payload.brand_id)
    data["secondary_objectives"] = list(payload.secondary_objectives)
    data["influencer_tiers"] = list(payload.influencer_tiers)
    data["tags"] = list(payload.tags)
    data["budget_currency"] = "USD"

    result = await railway_pg.insert("campaigns", data)
    return CampaignRead.model_validate(result[0])


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    user: CurrentUserDep,
):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        rows = await railway_pg.table("campaigns", select="*", eq_filters={"id": campaign_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return CampaignRead.model_validate(rows[0])

    result = await railway_pg.update("campaigns", updates, {"id": campaign_id})
    return CampaignRead.model_validate(result[0])


@router.post("/{campaign_id}/status", response_model=CampaignRead, summary="Change status")
async def change_status(
    campaign_id: str,
    payload: CampaignStatusChange,
    user: CurrentUserDep,
):
    if payload.to_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {sorted(VALID_STATUSES)}")
    result = await railway_pg.update("campaigns", {"status": payload.to_status}, {"id": campaign_id})
    return CampaignRead.model_validate(result[0])


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: str, user: CurrentUserDep):
    await railway_pg.update(
        "campaigns",
        {"deleted_at": datetime.now(UTC).isoformat()},
        eq_filters={"id": campaign_id},
    )
    return None
