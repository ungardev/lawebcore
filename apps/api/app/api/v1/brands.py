"""Brands endpoints."""
from fastapi import APIRouter, HTTPException, Query
from shared_core import railway_pg

from app.core.security import CurrentUserDep
from app.schemas import BrandCreate, BrandRead

router = APIRouter()


@router.get("", response_model=list[BrandRead])
async def list_brands(
    user: CurrentUserDep,
    client_id: str | None = Query(None),
    search: str | None = Query(None),
    is_active: bool | None = Query(True),
    limit: int = Query(100, le=500),
):
    all_rows = await railway_pg.table("brands", select="*", limit=10000)
    if client_id:
        all_rows = [r for r in all_rows if str(r.get("client_id") or "") == client_id]
    if is_active is not None:
        all_rows = [r for r in all_rows if r.get("is_active") == is_active]
    if search:
        s = search.lower()
        all_rows = [r for r in all_rows if s in (r.get("name") or "").lower() or s in (r.get("code") or "").lower()]
    return [BrandRead.model_validate(r) for r in all_rows[:limit]]


@router.post("", response_model=BrandRead, status_code=201)
async def create_brand(payload: BrandCreate, user: CurrentUserDep):
    data = payload.model_dump()
    data["client_id"] = str(payload.client_id)
    result = await railway_pg.insert("brands", data)
    return BrandRead.model_validate(result[0])
