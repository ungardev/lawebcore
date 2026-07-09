"""Brands endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import CurrentUserDep
from app.schemas import BrandRead, BrandCreate

router = APIRouter()


@router.get("", response_model=list[BrandRead])
async def list_brands(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    client_id: str | None = Query(None),
    search: str | None = Query(None),
    is_active: bool | None = Query(True),
    limit: int = Query(100, le=500),
):
    params: dict = {"limit": limit}
    where = ["deleted_at IS NULL"]
    if client_id:
        where.append("client_id = :client_id")
        params["client_id"] = client_id
    if is_active is not None:
        where.append("is_active = :is_active")
        params["is_active"] = is_active
    if search:
        where.append("(name ILIKE :search OR code ILIKE :search)")
        params["search"] = f"%{search}%"
    sql = f"""
        SELECT * FROM brands WHERE {' AND '.join(where)}
        ORDER BY name LIMIT :limit
    """
    result = await db.execute(text(sql), params)
    return [BrandRead.model_validate(r) for r in result.mappings().all()]


@router.post("", response_model=BrandRead, status_code=201)
async def create_brand(payload: BrandCreate, user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    sql = text("""
        INSERT INTO brands (client_id, code, name, category)
        VALUES (:client_id, :code, :name, :category)
        RETURNING *
    """)
    try:
        result = await db.execute(sql, payload.model_dump())
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create brand: {e}")
    return BrandRead.model_validate(result.mappings().first())