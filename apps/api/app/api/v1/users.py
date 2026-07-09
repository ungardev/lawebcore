"""Users endpoint - list users (admin) or self."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import CurrentUserDep
from app.schemas import UserRead

router = APIRouter()


@router.get("", response_model=list[UserRead], summary="List users")
async def list_users(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    bu_id: str | None = Query(None, description="Filter by business unit"),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    """List users visible to the current user. Admin sees all; others see their BU."""
    params: dict = {"limit": limit}
    where = []
    if bu_id:
        where.append("primary_bu_id = :bu_id")
        params["bu_id"] = bu_id
    if status:
        where.append("status = :status")
        params["status"] = status
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT * FROM users {where_sql}
        ORDER BY full_name
        LIMIT :limit
    """
    result = await db.execute(text(sql), params)
    return [UserRead.model_validate(r) for r in result.mappings().all()]


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: str, user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM users WHERE id = :uid"), {"uid": user_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.model_validate(row)