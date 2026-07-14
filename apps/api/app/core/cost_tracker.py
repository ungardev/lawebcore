"""Cost tracking middleware y utilities para APIs externas."""

import time
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class CostTracker:
    """Tracker de costos de APIs externas (Apify, Meta, TikTok, LLM, etc.)."""

    def __init__(self):
        self._pending: list[dict[str, Any]] = []

    def record(
        self,
        provider: str,
        operation: str,
        cost_usd: float,
        request_count: int = 1,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        entity_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Registra un costo para ser persistido luego."""
        self._pending.append({
            "provider": provider,
            "operation": operation,
            "cost_usd": cost_usd,
            "request_count": request_count,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "entity_id": entity_id,
            "metadata": metadata or {},
        })

    async def flush(self, db_session) -> int:
        """Persiste todos los costos pendientes en la BD y retorna la cantidad."""
        if not self._pending:
            return 0

        from sqlalchemy import insert
        from app.models.operation import ApiCost  # noqa: F401

        inserted = 0
        for record in self._pending:
            try:
                await db_session.execute(
                    insert(ApiCost).values(**record)
                )
                inserted += 1
            except Exception as e:
                logger.warning("cost_record_failed", error=str(e), record=record)

        self._pending.clear()
        logger.info("costs_flushed", count=inserted)
        return inserted


_cost_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    """Accede al tracker global."""
    return _cost_tracker


@asynccontextmanager
async def track_cost(
    provider: str,
    operation: str,
    entity_id: UUID | None = None,
):
    """Context manager para trackear costo y latencia de una operación."""
    start = time.monotonic()
    cost_usd = 0.0
    tokens_in = None
    tokens_out = None

    try:
        yield
    finally:
        elapsed = time.monotonic() - start
        _cost_tracker.record(
            provider=provider,
            operation=operation,
            cost_usd=cost_usd,
            entity_id=entity_id,
            metadata={"latency_ms": int(elapsed * 1000)},
        )


async def flush_costs(db_session) -> int:
    """Wrapper global para hacer flush de todos los costos pendientes."""
    return await _cost_tracker.flush(db_session)
