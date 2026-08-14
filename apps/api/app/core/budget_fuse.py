"""Budget fuse for the Lens discovery pipeline.

Tracks cumulative monthly spend per provider in Redis and enforces:
  - MONTHLY_BUDGET_USD: hard cap per calendar month
  - MAX_CALLS_PER_RUN: per-run call limit
  - BUDGET_ALERT_THRESHOLD: warn at this % of monthly budget

Usage:
    fuse = BudgetFuse()
    await fuse.assert_budget_available(run_id)  # raises BudgetExhausted
    await fuse.record_call("hikerapi", cost_usd=0.0006)
    await fuse.get_current_spend()  # {this_month_usd, pct_used, ...}
"""

from dataclasses import dataclass

import structlog
from discovery.exceptions import BudgetExhausted

logger = structlog.get_logger(__name__)


@dataclass
class BudgetState:
    this_month_usd: float
    this_month_calls: int
    this_run_calls: int
    pct_used: float
    alert_sent: bool


class BudgetFuse:
    """Redis-backed budget tracking and enforcement for Lens."""

    def __init__(
        self,
        monthly_budget_usd: float = 10.0,
        max_calls_per_run: int = 120,
        alert_threshold: float = 0.7,
        cost_per_call_usd: float = 0.0006,
    ):
        self.monthly_budget_usd = monthly_budget_usd
        self.max_calls_per_run = max_calls_per_run
        self.alert_threshold = alert_threshold
        self.cost_per_call_usd = cost_per_call_usd
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as redis_async
            from shared_core.config import settings

            self._redis = redis_async.from_url(settings.ARQ_REDIS_URL, decode_responses=False)
        return self._redis

    def _month_key(self, provider: str) -> str:
        import datetime
        month = datetime.datetime.utcnow().strftime("%Y-%m")
        return f"lens:budget:{provider}:{month}"

    def _run_key(self, run_id: str) -> str:
        return f"lens:budget:run:{run_id}"

    def _alert_key(self, provider: str) -> str:
        import datetime
        month = datetime.datetime.utcnow().strftime("%Y-%m")
        return f"lens:budget:alerted:{provider}:{month}"

    async def assert_budget_available(self, run_id: str, provider: str = "hikerapi") -> None:
        """Raises BudgetExhausted if monthly budget is exhausted.

        Sends a warning log if approaching the threshold.
        """
        r = await self._get_redis()
        month_key = self._month_key(provider)
        alert_key = self._alert_key(provider)

        current_spent = 0.0
        try:
            raw = await r.get(month_key)
            if raw:
                current_spent = float(raw)
        except Exception as e:
            logger.warning("budget_fuse_redis_read_error", error=str(e))

        pct = current_spent / self.monthly_budget_usd if self.monthly_budget_usd > 0 else 0

        if pct >= 1.0:
            logger.error(
                "budget_fuse_monthly_exhausted",
                provider=provider,
                spent_usd=current_spent,
                budget_usd=self.monthly_budget_usd,
            )
            raise BudgetExhausted(
                f"Presupuesto mensual agotado: ${current_spent:.4f} de ${self.monthly_budget_usd:.2f} gastados. "
                f"Recarga en hikerapi.com/billing",
                current_usd=current_spent,
                budget_usd=self.monthly_budget_usd,
            )

        if pct >= self.alert_threshold:
            alerted = await r.get(alert_key)
            if not alerted:
                logger.warning(
                    "budget_fuse_threshold_warning",
                    provider=provider,
                    spent_usd=current_spent,
                    budget_usd=self.monthly_budget_usd,
                    pct=f"{pct:.1%}",
                    hint="70% threshold reached — consider pausing",
                )
                await r.set(alert_key, "1")

    async def can_make_call(self, run_id: str) -> bool:
        """Returns False if this run has hit MAX_CALLS_PER_RUN."""
        try:
            r = await self._get_redis()
            run_key = self._run_key(run_id)
            count_raw = await r.get(run_key)
            count = int(count_raw) if count_raw else 0
            return count < self.max_calls_per_run
        except Exception as e:
            logger.warning("budget_fuse_run_counter_error", error=str(e))
            return True

    async def record_call(self, run_id: str, provider: str = "hikerapi", call_count: int = 1) -> None:
        """Record API calls and accumulate monthly spend atomically."""
        cost = call_count * self.cost_per_call_usd
        month_key = self._month_key(provider)
        run_key = self._run_key(run_id)

        try:
            r = await self._get_redis()
            pipe = r.pipeline()
            pipe.incrbyfloat(month_key, cost)
            pipe.expire(month_key, 60 * 60 * 24 * 40)
            pipe.incr(run_key)
            pipe.expire(run_key, 60 * 60 * 24)
            await pipe.execute()
            logger.info(
                "budget_fuse_call_recorded",
                run_id=run_id,
                provider=provider,
                calls=call_count,
                cost_usd=cost,
            )
        except Exception as e:
            logger.warning("budget_fuse_record_error", error=str(e))

    async def check_run_limit(self, run_id: str) -> bool:
        """Returns True if run can continue, False if at limit."""
        return await self.can_make_call(run_id)

    async def get_current_spend(self, provider: str = "hikerapi") -> BudgetState:
        """Return current spend state for observability."""
        try:
            r = await self._get_redis()
            raw = await r.get(self._month_key(provider))
            this_month_usd = float(raw) if raw else 0.0
            pct = this_month_usd / self.monthly_budget_usd if self.monthly_budget_usd > 0 else 0
            alerted_raw = await r.get(self._alert_key(provider))
            alert_sent = bool(alerted_raw)
        except Exception as e:
            logger.warning("budget_fuse_get_spend_error", error=str(e))
            this_month_usd = 0.0
            pct = 0.0
            alert_sent = False
        return BudgetState(
            this_month_usd=round(this_month_usd, 6),
            this_month_calls=0,
            this_run_calls=0,
            pct_used=round(pct, 4),
            alert_sent=alert_sent,
        )

    async def reset_run_counter(self, run_id: str) -> None:
        """Delete the per-run call counter. Called at end of run."""
        try:
            r = await self._get_redis()
            await r.delete(self._run_key(run_id))
        except Exception as e:
            logger.warning("budget_fuse_reset_error", run_id=run_id, error=str(e))
