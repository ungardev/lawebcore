"""Clients endpoints."""
from fastapi import APIRouter, HTTPException, Query
from app.core.supabase_rest import supabase_rest
from app.core.security import CurrentUserDep
from app.schemas import ClientRead, ClientCreate

router = APIRouter()


@router.get("", response_model=list[ClientRead], summary="List clients")
async def list_clients(
    user: CurrentUserDep,
    search: str | None = Query(None),
    is_active: bool | None = Query(True),
    limit: int = Query(100, le=500),
):
    all_rows = await supabase_rest.table("clients", select="*", limit=10000)
    if is_active is not None:
        all_rows = [r for r in all_rows if r.get("is_active") == is_active]
    if search:
        s = search.lower()
        all_rows = [r for r in all_rows if s in (r.get("name") or "").lower() or s in (r.get("code") or "").lower()]
    return [ClientRead.model_validate(r) for r in all_rows[:limit]]


@router.post("", response_model=ClientRead, status_code=201, summary="Create client")
async def create_client(payload: ClientCreate, user: CurrentUserDep):
    data = payload.model_dump()
    data["code"] = payload.code.upper()
    data["created_by"] = str(user.id)
    result = await supabase_rest.insert("clients", data)
    return ClientRead.model_validate(result[0])


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(client_id: str, user: CurrentUserDep):
    rows = await supabase_rest.table("clients", select="*",         eq_filters={"id": client_id},
        is_null_filters=["deleted_at"])
    if not rows:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientRead.model_validate(rows[0])
