"""
La Web Core - FastAPI Application
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.db import close_db, init_db
from app.api.v1 import api_router
from app.core.logging import configure_logging

configure_logging(settings.API_ENV)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("lawebcore_api_starting", env=settings.API_ENV, version="0.1.0")
    await init_db()
    yield
    logger.info("lawebcore_api_stopping")
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
    from app.core.db import db_session
    try:
        async with db_session() as session:
            await session.execute("SELECT 1")
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "db": "error", "error": str(e)},
        )


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