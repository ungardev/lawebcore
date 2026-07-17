"""Rate limiting middleware usando slowapi."""

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from shared_core import settings


def get_user_identifier(request: Request) -> str:
    """Usa el JWT sub claim si está autenticado, si no el IP."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        import json
        import base64
        try:
            token = auth_header.split(" ")[1]
            _, payload, _ = token.split(".")
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding
            claims = json.loads(base64.b64decode(payload + "=="))
            return claims.get("sub", get_remote_address(request))
        except Exception:
            return get_remote_address(request)
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_identifier, default_limits=["300/minute"])


def register_discovery_limits() -> None:
    """Registra los límites específicos para endpoints de discovery."""
    from app.api.v1.discovery import router as discovery_router

    for route in discovery_router.routes:
        if hasattr(route, "path"):
            route.limiter = limiter
            if "/conversations" in route.path or "/search" in route.path:
                route.kwargs["ratelimit"] = f"{settings.RATE_LIMIT_DISCOVERY_PER_MIN}/minute"


def add_rate_limit_exceeded_handler(app):
    """Agrega el handler global para cuando se excede el rate limit."""

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return Response(
            content='{"detail":"Rate limit exceeded. Please slow down."}',
            status_code=429,
            media_type="application/json",
            headers={
                "Retry-After": str(exc.detail.get("retry_after", 60)),
                "X-RateLimit-Limit": str(exc.detail.get("limit", "")),
            },
        )
