"""Security: Supabase JWT verification (ES256 + JWKS), password hashing, RBAC helpers."""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from shared_core import settings


security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Authenticated user derived from Supabase JWT."""
    id: UUID
    email: str
    role: str = "authenticated"
    raw_claims: dict


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """
    Fetch JWKS from Supabase (cached for process lifetime).
    The JWKS contains the public keys needed to verify ES256 tokens.
    """
    if not settings.SUPABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL not configured",
        )
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch JWKS: {e}",
        )


def verify_supabase_token(token: str) -> dict:
    """
    Verify a Supabase JWT using the project's public key (ES256).
    Returns the decoded claims.
    """
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        kid = header.get("kid")

        if alg != "ES256":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Unsupported algorithm: {alg}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        jwks = _get_jwks()
        matching_key = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == kid),
            None,
        )
        if not matching_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No matching public key found for token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        claims = jwt.decode(
            token,
            matching_key,
            algorithms=["ES256"],
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
