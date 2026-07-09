"""Clients endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import CurrentUserDep
from app.schemas import ClientRead, ClientCreate

router = APIRouter()


@router.get("", response_model=list[ClientRead], summary="List clients")
async def list_clients(
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None),
    is_active: bool | None = Query(True),
    limit: int = Query(100, le=500),
):
    params: dict = {"limit": limit}
    where = ["deleted_at IS NULL"]
    if is_active is not None:
        where.append("is_active = :is_active")
        params["is_active"] = is_active
    if search:
        where.append("(name ILIKE :search OR code ILIKE :search)")
        params["search"] = f"%{search}%"
    sql = f"""
        SELECT * FROM clients
        WHERE {' AND '.join(where)}
        ORDER BY name
        LIMIT :limit
    """
    result = await db.execute(text(sql), params)
    return [ClientRead.model_validate(r) for r in result.mappings().all()]


@router.post("", response_model=ClientRead, status_code=201, summary="Create client")
async def create_client(
    payload: ClientCreate,
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    sql = text("""
        INSERT INTO clients (code, name, legal_name, tax_id, industry, website, created_by)
        VALUES (:code, :name, :legal_name, :tax_id, :industry, :website, :created_by)
        RETURNING *
    """)
    try:
        result = await db.execute(sql, {
            "code": payload.code.upper(),
            "name": payload.name,
            "legal_name": payload.legal_name,
            "tax_id": payload.tax_id,
            "industry": payload.industry,
            "website": payload.website,
            "created_by": str(user.id),
        })
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create client: {e}")
    return ClientRead.model_validate(result.mappings().first())


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(client_id: str, user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM clients WHERE id = :id AND deleted_at IS NULL"),
        {"id": client_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientRead.model_validate(row)