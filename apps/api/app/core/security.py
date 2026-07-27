"""Security: Local JWT verification (HS256), password hashing, RBAC helpers."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from shared_core import settings


security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    id: UUID
    email: str
    role: str = "authenticated"
    full_name: str | None = None
    raw_claims: dict


def create_access_token(user_id: UUID, email: str, role: str, full_name: str | None = None) -> str:
    """Create a HS256 JWT signed with ADMIN_TOKEN."""
    exp = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "app_role": role,
        "full_name": full_name or "",
        "exp": exp,
        "iat": datetime.now(timezone.utc),
        "iss": "lawebcore-api",
        "aud": "lawebcore-web",
    }
    return jwt.encode(payload, settings.ADMIN_TOKEN, algorithm="HS256")


def verify_local_token(token: str) -> dict:
    """Verify a local HS256 JWT signed with ADMIN_TOKEN. Returns the decoded claims."""
    try:
        claims = jwt.decode(
            token,
            settings.ADMIN_TOKEN,
            algorithms=["HS256"],
            audience="lawebcore-web",
            issuer="lawebcore-api",
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
    """FastAPI dependency that returns the current authenticated user from local JWT."""
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = verify_local_token(creds.credentials)
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
        full_name=claims.get("full_name"),
        raw_claims=claims,
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*allowed_roles: str):
    """
    Dependency factory: returns a dependency that checks if the user has
    at least one of the allowed role codes.
    """
    async def _check(user: CurrentUserDep) -> CurrentUser:
        user_role = user.role
        if user_role == "admin_general":
            return user
        if user_role in allowed_roles:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {list(allowed_roles)}",
        )
    return _check
