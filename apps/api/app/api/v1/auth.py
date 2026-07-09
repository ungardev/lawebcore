"""Auth endpoints - sync user profile from Supabase JWT."""

from fastapi import APIRouter, HTTPException, status
from supabase import create_client, Client as SupabaseClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.config import settings
from app.core.db import get_db
from app.core.security import CurrentUserDep, get_current_user
from app.schemas import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead, summary="Current user profile")
async def get_me(user: CurrentUserDep, db: AsyncSession = Depends(get_db)):
    """Returns the profile of the authenticated user; auto-creates if missing."""
    # Intentar leer de la tabla users (mirror de auth.users)
    result = await db.execute(text("SELECT * FROM users WHERE id = :uid"), {"uid": str(user.id)})
    row = result.mappings().first()
    if row:
        return UserRead.model_validate(row)
    # Si no existe, auto-crear perfil basico
    await db.execute(
        text("""
        INSERT INTO users (id, email, full_name, status)
        VALUES (:uid, :email, :full_name, 'active')
        ON CONFLICT (id) DO NOTHING
        """),
        {"uid": str(user.id), "email": user.email, "full_name": user.email.split("@")[0]},
    )
    await db.commit()
    result = await db.execute(text("SELECT * FROM users WHERE id = :uid"), {"uid": str(user.id)})
    return UserRead.model_validate(result.mappings().first())


@router.post("/logout", summary="Logout (client-side token discard)")
async def logout(user: CurrentUserDep):
    """Logout is handled client-side by discarding the JWT. Endpoint exists for audit hooks."""
    return {"status": "logged_out", "user_id": str(user.id)}