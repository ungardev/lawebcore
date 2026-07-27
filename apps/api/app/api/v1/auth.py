"""Auth endpoints - local user authentication via Railway Postgres."""

from uuid import UUID

import bcrypt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.security import CurrentUserDep, create_access_token, get_current_user
from shared_core import supabase_rest


router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    full_name: str | None


class UserRead(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    status: str
    created_at: str | None


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """Authenticate user with email + password. Returns HS256 JWT."""
    rows = await supabase_rest.select(
        table="users",
        select="id,email,full_name,role,status,password_hash",
        filters=[f"email={body.email}"],
        limit=1,
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = rows[0]
    password_hash = user.get("password_hash")
    if not password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not bcrypt.checkpw(body.password.encode(), password_hash.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user_status = user.get("status", "active")
    if user_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {user_status}",
        )

    user_id_str = str(user["id"])
    token = create_access_token(
        user_id=UUID(user_id_str),
        email=str(user["email"]),
        role=str(user.get("role", "authenticated")),
        full_name=str(user.get("full_name")) if user.get("full_name") else None,
    )

    return LoginResponse(
        access_token=token,
        user_id=user_id_str,
        email=str(user["email"]),
        role=str(user.get("role", "authenticated")),
        full_name=str(user.get("full_name")) if user.get("full_name") else None,
    )


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUserDep):
    """Returns the profile of the authenticated user."""
    rows = await supabase_rest.select(
        table="users",
        select="id,email,full_name,role,status,created_at",
        filters=[f"id={user.id}"],
        limit=1,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")
    u = rows[0]
    return UserRead(
        id=str(u["id"]),
        email=str(u["email"]),
        full_name=u.get("full_name"),
        role=str(u.get("role", "authenticated")),
        status=str(u.get("status", "active")),
        created_at=u.get("created_at"),
    )


@router.post("/logout")
async def logout(user: CurrentUserDep):
    """Logout is handled client-side by discarding the JWT."""
    return {"status": "logged_out", "user_id": str(user.id)}
