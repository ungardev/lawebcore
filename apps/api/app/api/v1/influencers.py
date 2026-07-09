"""Influencers endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import CurrentUserDep
from app.schemas import InfluencerRead, InfluencerCreate, InfluencerMetricsRead

router = APIRouter()


@router.get("", response_model=list[InfluencerRead])
async def list_influencers(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    tier: str | None = Query(None),
    search: str | None = Query(None),
    tag: str | None = Query(None),
    status: str | None = Query("active"),
    limit: int = Query(100, le=500),
):
    params: dict = {"limit": limit}
    where = ["deleted_at IS NULL"]
    if tier:
        where.append("primary_tier = :tier"); params["tier"] = tier.upper()
    if status:
        where.append("status = :status"); params["status"] = status
    if search:
        where.append("(full_name ILIKE :search OR primary_handle ILIKE :search OR email ILIKE :search)")
        params["search"] = f"%{search}%"
    if tag:
        where.append(":tag = ANY(tags)"); params["tag"] = tag
    sql = f"""
        SELECT * FROM influencers WHERE {' AND '.join(where)}
        ORDER BY full_name LIMIT :limit
    """
    result = await db.execute(text(sql), params)
    return [InfluencerRead.model_validate(r) for r in result.mappings().all()]


@router.post("", response_model=InfluencerRead, status_code=201)
async def create_influencer(
    payload: InfluencerCreate,
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    sql = text("""
        INSERT INTO influencers (
            full_name, email, phone, country, primary_tier, primary_handle,
            bio, content_niches, languages, tags, source, source_id, created_by
        ) VALUES (
            :full_name, :email, :phone, :country, :primary_tier, :primary_handle,
            :bio, :content_niches, :languages, :tags, :source, :source_id, :created_by
        )
        RETURNING *
    """)
    params = payload.model_dump()
    params["created_by"] = str(user.id)
    params["primary_tier"] = payload.primary_tier.upper()
    try:
        result = await db.execute(sql, params)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create influencer: {e}")
    return InfluencerRead.model_validate(result.mappings().first())


@router.get("/{influencer_id}/metrics", response_model=list[InfluencerMetricsRead])
async def get_metrics(influencer_id: str, user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    sql = text("""
        SELECT * FROM influencer_metrics_snapshot
        WHERE influencer_id = :id
        ORDER BY snapshot_date DESC LIMIT 100
    """)
    result = await db.execute(sql, {"id": influencer_id})
    return [InfluencerMetricsRead.model_validate(r) for r in result.mappings().all()]


@router.get("/{influencer_id}", response_model=InfluencerRead)
async def get_influencer(influencer_id: str, user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    sql = text("SELECT * FROM influencers WHERE id = :id AND deleted_at IS NULL")
    result = await db.execute(sql, {"id": influencer_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Influencer not found")
    return InfluencerRead.model_validate(row)