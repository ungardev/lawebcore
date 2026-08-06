"""Unified cost tracking for the Lens discovery pipeline.

Tracks costs from:
  - Apify API calls (per-actor, from usageTotalUsd)
  - DeepSeek API calls (per-operation, from token counts)

All costs are persisted to the api_costs table at the end of a run,
with the correct request_count per operation type.

Usage:
    tracker = DiscoveryCostTracker()
    tracker.record_apify_cost(run_id, "instagram-hashtag-scraper", 0.021, {"hashtags": 3})
    tracker.record_deepseek_cost(run_id, 0.003, 1200, 400, "profile_generation", {"fingerprint": "..."})
    await tracker.flush(run_id)
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import structlog

from shared_core.supabase_rest import supabase_rest

logger = structlog.get_logger(__name__)

try:
    from app.core.metrics import lens_apify_cost_usd_total
    _HAS_METRICS = True
except Exception:
    _HAS_METRICS = False


@dataclass
class ApifyCostRecord:
    actor_id: str
    cost_usd: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeepSeekCostRecord:
    operation: str
    cost_usd: float
    tokens_input: int
    tokens_output: int
    metadata: dict[str, Any] = field(default_factory=dict)


class DiscoveryCostTracker:
    """Accumulates and persists all costs for a single discovery run."""

    def __init__(self):
        self._apify_costs: dict[str, list[ApifyCostRecord]] = {}
        self._deepseek_costs: dict[str, list[DeepSeekCostRecord]] = {}

    def record_apify_cost(
        self,
        run_id: str,
        actor_id: str,
        cost_usd: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a single Apify actor call cost."""
        if run_id not in self._apify_costs:
            self._apify_costs[run_id] = []
        self._apify_costs[run_id].append(
            ApifyCostRecord(actor_id=actor_id, cost_usd=cost_usd, metadata=metadata or {})
        )
        if _HAS_METRICS:
            lens_apify_cost_usd_total.labels(actor_id=actor_id).inc(cost_usd)
        logger.info(
            "cost_apify_recorded",
            run_id=run_id,
            actor_id=actor_id,
            cost_usd=cost_usd,
        )

    def record_deepseek_cost(
        self,
        run_id: str,
        cost_usd: float,
        tokens_input: int,
        tokens_output: int,
        operation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a DeepSeek API call cost."""
        if run_id not in self._deepseek_costs:
            self._deepseek_costs[run_id] = []
        self._deepseek_costs[run_id].append(
            DeepSeekCostRecord(
                operation=operation,
                cost_usd=cost_usd,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                metadata=metadata or {},
            )
        )
        logger.info(
            "cost_deepseek_recorded",
            run_id=run_id,
            operation=operation,
            cost_usd=cost_usd,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
        )

    def get_run_summary(self, run_id: str) -> dict[str, Any]:
        """Return a summary of all costs for a run."""
        apify_records = self._apify_costs.get(run_id, [])
        deepseek_records = self._deepseek_costs.get(run_id, [])

        total_apify = sum(r.cost_usd for r in apify_records)
        total_deepseek = sum(r.cost_usd for r in deepseek_records)
        total_tokens_in = sum(r.tokens_input for r in deepseek_records)
        total_tokens_out = sum(r.tokens_output for r in deepseek_records)
        apify_call_count = len(apify_records)
        deepseek_call_count = len(deepseek_records)

        return {
            "run_id": run_id,
            "total_apify_usd": round(total_apify, 6),
            "total_deepseek_usd": round(total_deepseek, 6),
            "total_usd": round(total_apify + total_deepseek, 6),
            "apify_call_count": apify_call_count,
            "deepseek_call_count": deepseek_call_count,
            "deepseek_tokens_input": total_tokens_in,
            "deepseek_tokens_output": total_tokens_out,
        }

    async def flush(self, run_id: str) -> dict[str, Any]:
        """Persist all pending costs for a run to the api_costs table.

        Returns the run cost summary.
        """
        summary = self.get_run_summary(run_id)

        apify_records = self._apify_costs.pop(run_id, [])
        deepseek_records = self._deepseek_costs.pop(run_id, [])

        for record in apify_records:
            await supabase_rest.insert("api_costs", {
                "provider": "apify",
                "operation": record.actor_id,
                "entity_id": run_id,
                "cost_usd": round(record.cost_usd, 6),
                "request_count": 1,
                "metadata": record.metadata,
            })

        for record in deepseek_records:
            await supabase_rest.insert("api_costs", {
                "provider": "deepseek",
                "operation": record.operation,
                "entity_id": run_id,
                "cost_usd": round(record.cost_usd, 6),
                "tokens_input": record.tokens_input,
                "tokens_output": record.tokens_output,
                "metadata": record.metadata,
            })

        logger.info(
            "costs_flushed",
            run_id=run_id,
            apify_records=len(apify_records),
            deepseek_records=len(deepseek_records),
            total_apify_usd=summary["total_apify_usd"],
            total_deepseek_usd=summary["total_deepseek_usd"],
        )

        return summary


_tracker: DiscoveryCostTracker | None = None


def get_discovery_cost_tracker() -> DiscoveryCostTracker:
    """Return the global discovery cost tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = DiscoveryCostTracker()
    return _tracker
