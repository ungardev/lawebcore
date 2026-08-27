"""Influencers endpoints."""
from fastapi import APIRouter, HTTPException, Query
from shared_core import railway_pg

from app.core.security import CurrentUserDep
from app.schemas import InfluencerCreate, InfluencerMetricsRead, InfluencerRead

router = APIRouter()


@router.get("", response_model=list[InfluencerRead])
async def list_influencers(
    user: CurrentUserDep,
    tier: str | None = Query(None),
    search: str | None = Query(None),
    tag: str | None = Query(None),
    status: str | None = Query("active"),
    limit: int = Query(100, le=500),
):
    all_rows = await railway_pg.table("influencers", select="*", limit=10000)
    if tier:
        all_rows = [r for r in all_rows if (r.get("primary_tier") or "").upper() == tier.upper()]
    if status:
        all_rows = [r for r in all_rows if r.get("status") == status]
    if search:
        s = search.lower()
        all_rows = [r for r in all_rows
                    if s in (r.get("full_name") or "").lower()
                    or s in (r.get("primary_handle") or "").lower()
                    or s in (r.get("email") or "").lower()]
    if tag:
        all_rows = [r for r in all_rows if tag in (r.get("tags") or [])]
    return [InfluencerRead.model_validate(r) for r in all_rows[:limit]]


@router.post("", response_model=InfluencerRead, status_code=201)
async def create_influencer(payload: InfluencerCreate, user: CurrentUserDep):
    data = payload.model_dump()
    data["primary_tier"] = payload.primary_tier.upper()
    data["created_by"] = str(user.id)
    result = await railway_pg.insert("influencers", data)
    return InfluencerRead.model_validate(result[0])


@router.get("/{influencer_id}/metrics", response_model=list[InfluencerMetricsRead])
async def get_metrics(influencer_id: str, user: CurrentUserDep):
    rows = await railway_pg.table(
        "influencer_metrics_snapshot",
        select="*",
        eq_filters={"influencer_id": influencer_id},
        order="snapshot_date.desc",
        limit=100,
    )
    return [InfluencerMetricsRead.model_validate(r) for r in rows]


@router.get("/{influencer_id}", response_model=InfluencerRead)
async def get_influencer(influencer_id: str, user: CurrentUserDep):
    rows = await railway_pg.table(
        "influencers",
        select="*",
        eq_filters={"id": influencer_id},
        is_null_filters=["deleted_at"],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Influencer not found")
    return InfluencerRead.model_validate(rows[0])
