"""
La Web Core - FastAPI Application
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from sqlalchemy import text

from shared_core import settings, close_db, init_db, supabase_rest
from app.api.v1 import api_router
from app.core.logging import configure_logging

# Sentry initialization (only in production, requires real DSN)
if settings.API_ENV == "production":
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn="https://<key>@sentry.io/<project>",
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            environment=settings.API_ENV,
            release="lawebcore-api@0.1.0",
        )
    except Exception:
        pass

configure_logging(settings.API_ENV)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("lawebcore_api_starting", env=settings.API_ENV, version="0.1.0")
    await init_db()
    from app.core.worker_enqueuer import close_worker_pool, init_worker_pool
    await init_worker_pool()

    import multiprocessing
    from app.workers.worker import WorkerSettings

    def _arq_worker_entry():
        """Entry point for the ARQ worker process."""
        import asyncio
        from arq.worker import run_worker
        asyncio.run(run_worker(WorkerSettings))

    arq_process = multiprocessing.Process(
        target=_arq_worker_entry,
        daemon=True,
        name="arq-worker",
    )
    arq_process.start()
    logger.info("arq_worker_started_as_separate_process", pid=arq_process.pid)

    yield
    logger.info("lawebcore_api_stopping")
    await close_worker_pool()
    await supabase_rest.close()
    await close_db()


app = FastAPI(
    title="La Web Core API",
    description="API interna de La Web Figital Agency - gestion de campanas, KPIs, operaciones e IA",
    version="0.1.0",
    docs_url="/api/docs" if settings.API_ENV != "production" else None,
    redoc_url="/api/redoc" if settings.API_ENV != "production" else None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.API_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Rate limiting (slowapi)
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
        headers={"Retry-After": "60"},
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "path": request.url.path},
    )


# Health endpoints
@app.get("/api/v1/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "lawebcore-api", "version": "0.1.0"}


@app.get("/api/v1/health/ready", tags=["health"])
async def readiness():
    from shared_core import db_session
    try:
        async with db_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "db": "error", "error": str(e)},
        )


@app.get("/api/v1/health/net-debug", tags=["health"])
async def net_debug():
    """Debug network connectivity to Supabase hosts."""
    import socket
    import httpx
    result = {
        "outbound_ip": None,
        "dns_pooler": None,
        "dns_direct": None,
        "tcp_pooler_6543": None,
        "tcp_direct_5432": None,
        "errors": [],
    }
    try:
        r = httpx.get("https://api.ipify.org", timeout=5)
        result["outbound_ip"] = r.text
    except Exception as e:
        result["errors"].append(f"ipify: {e}")

    for host_key, host in [
        ("dns_pooler", "aws-0-us-east-1.pooler.supabase.com"),
        ("dns_direct", "db.sdrsxeweobcnnqdxqhjb.supabase.co"),
    ]:
        try:
            result[host_key] = socket.gethostbyname(host)
        except Exception as e:
            result["errors"].append(f"{host_key}: {type(e).__name__}: {str(e)[:100]}")

    for tcp_key, host, port in [
        ("tcp_pooler_6543", "aws-0-us-east-1.pooler.supabase.com", 6543),
        ("tcp_direct_5432", "db.sdrsxeweobcnnqdxqhjb.supabase.co", 5432),
    ]:
        try:
            sock = socket.create_connection((host, port), timeout=10)
            sock.close()
            result[tcp_key] = "OK"
        except Exception as e:
            result[tcp_key] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"

    return result


# Mount v1 API
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_ENV == "development",
    )