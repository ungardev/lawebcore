"""
La Web Core - FastAPI Application
"""

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from shared_core import close_db, init_db, settings
from sqlalchemy import text

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

import multiprocessing  # noqa: E402


def _arq_worker_entry():
    """Entry point for the ARQ worker process."""
    import asyncio

    from arq.worker import run_worker

    from app.workers.worker import WorkerSettings
    asyncio.run(run_worker(WorkerSettings))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("lawebcore_api_starting", env=settings.API_ENV, version="0.1.0")

    if os.environ.get("SKIP_MIGRATIONS_ON_STARTUP", "false").lower() != "true":
        try:
            from scripts.apply_migrations import apply_migrations
            await apply_migrations()
        except Exception as e:
            logger.warning("migrations_failed_on_startup", error=str(e))
    else:
        logger.info("migrations_skipped_on_startup", reason="SKIP_MIGRATIONS_ON_STARTUP=true")

    await init_db()
    from discovery.memory import migrate_discovery_conversations_schema
    await migrate_discovery_conversations_schema()
    from app.core.worker_enqueuer import close_worker_pool, init_worker_pool
    await init_worker_pool()

    ctx = multiprocessing.get_context("spawn")
    arq_process = ctx.Process(
        target=_arq_worker_entry,
        daemon=True,
        name="arq-worker",
    )
    arq_process.start()
    logger.info("arq_worker_started_as_separate_process", pid=arq_process.pid)

    yield
    logger.info("lawebcore_api_stopping")
    await close_worker_pool()
    await railway_pg.close()  # noqa: F821
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
from slowapi import Limiter  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402

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


@app.get("/api/v1/health/sources", tags=["health"])
async def health_sources():
    """Check status of all Instagram data sources (HikerAPI, Apify) and remaining credits."""
    import os

    from discovery.tools.hikerapi_client import HikerAPIClient

    result = {
        "active_source": os.getenv("INSTAGRAM_SOURCE", "hikerapi"),
        "sources": {},
    }

    hikerapi_key = os.getenv("HIKERAPI_API_KEY", "")
    if hikerapi_key:
        try:
            client = HikerAPIClient(api_key=hikerapi_key)
            balance_resp, status_code = await client._get_debug("/sys/balance")
            await client.close()
            if balance_resp:
                balance = (
                    balance_resp.get("requests")
                    or balance_resp.get("user_credit_balance")
                    or balance_resp.get("balance")
                    or balance_resp.get("credits")
                    or balance_resp.get("credit_balance")
                    or balance_resp.get("data", {}).get("balance")
                    or balance_resp.get("response", {}).get("balance")
                )
                result["sources"]["hikerapi"] = {
                    "status": "ok",
                    "balance": balance,
                    "rate_limit": balance_resp.get("rate"),
                    "currency": balance_resp.get("currency"),
                    "amount": balance_resp.get("amount"),
                    "status_code": status_code,
                    "response_raw": str(balance_resp)[:500],
                    "key_prefix": hikerapi_key[:8] + "..." if len(hikerapi_key) > 8 else hikerapi_key,
                }
            else:
                result["sources"]["hikerapi"] = {
                    "status": "error",
                    "status_code": status_code,
                    "error": f"No response from /sys/balance (status={status_code})",
                }
        except Exception as e:
            result["sources"]["hikerapi"] = {
                "status": "error",
                "error": str(e),
            }
    else:
        result["sources"]["hikerapi"] = {
            "status": "not_configured",
            "error": "HIKERAPI_API_KEY env var not set",
        }

    apify_key = os.getenv("APIFY_API_KEY", "")
    if apify_key:
        result["sources"]["apify"] = {
            "status": "available",
            "key_prefix": apify_key[:8] + "..." if len(apify_key) > 8 else apify_key,
        }
    else:
        result["sources"]["apify"] = {
            "status": "not_configured",
        }

    return result


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
        r = httpx.get("https://api.ipify.org", timeout=5)  # noqa: ASYNC210
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
