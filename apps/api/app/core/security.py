"""Security: Supabase JWT verification, password hashing, RBAC helpers."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Authenticated user derived from Supabase JWT."""
    id: UUID
    email: str
    role: str = "authenticated"
    raw_claims: dict


def verify_supabase_token(token: str) -> dict:
    """
    Verify a Supabase JWT using the project's JWT secret.
    Returns the decoded claims.
    """
    if not settings.SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET not configured",
        )
    try:
        claims = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return claims
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> CurrentUser:
    """FastAPI dependency that returns the current authenticated user."""
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = verify_supabase_token(creds.credentials)
    user_id = claims.get("sub")
    email = claims.get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims (sub, email)",
        )
    return CurrentUser(
        id=UUID(user_id),
        email=email,
        role=claims.get("role", "authenticated"),
        raw_claims=claims,
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*allowed_roles: str):
    """
    Dependency factory: returns a dependency that checks if the user has
    at least one of the allowed role codes.
    """
    async def _check(user: CurrentUserDep) -> CurrentUser:
        # En una implementacion real, consultamos user_roles en DB
        # Aqui simplificamos: el rol viene en el claim custom 'app_role'
        user_role = user.raw_claims.get("app_role", "")
        if user_role == "admin_general":
            return user
        if user_role in allowed_roles:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {list(allowed_roles)}",
        )
    return _check