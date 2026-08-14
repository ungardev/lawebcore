"""Helper para enqueue jobs al worker ARQ desde la API."""

from __future__ import annotations

import structlog
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from shared_core import settings

logger = structlog.get_logger(__name__)

_pool: ArqRedis | None = None


async def init_worker_pool() -> None:
    """Inicializa el pool Redis ARQ en startup de la API."""
    global _pool
    if _pool is not None:
        return
    try:
        redis_settings = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
        _pool = await create_pool(redis_settings)
        logger.info("arq_pool_initialized", url=str(settings.ARQ_REDIS_URL)[:50])
    except Exception as e:
        logger.warning("arq_pool_init_failed", error=str(e))
        _pool = None


async def close_worker_pool() -> None:
    """Cierra el pool Redis ARQ en shutdown de la API."""
    global _pool
    if _pool is not None:
        try:
            await _pool.aclose()
        except Exception:
            pass
        _pool = None


async def enqueue_discovery_run(run_id: str) -> bool:
    """
    Encola un discovery_run al worker ARQ.
    Devuelve True si se enqueo, False si fallo (best-effort).
    """
    global _pool
    if _pool is None:
        try:
            redis_settings = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
            _pool = await create_pool(redis_settings)
        except Exception as e:
            logger.warning("arq_pool_unavailable", error=str(e))
            return False

    try:
        job = await _pool.enqueue_job(
            "discovery_run_task",
            run_id,
            _job_id=f"discovery:{run_id}",
        )
        if job is None:
            logger.warning(
                "discovery_run_enqueue_deduped",
                run_id=run_id,
                hint="job_id ya usado en la última hora — reintento de run fallido silenciosamente",
            )
            return False
        logger.info("discovery_run_enqueued", run_id=run_id)
        return True
    except Exception as e:
        logger.error("discovery_run_enqueue_failed", run_id=run_id, error=str(e))
        return False
