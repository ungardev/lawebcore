"""Budget fuse for the Lens discovery pipeline.

Tracks cumulative monthly spend per provider in Redis and enforces:
  - MONTHLY_BUDGET_USD: hard cap per calendar month
  - MAX_CALLS_PER_RUN: per-run call limit
  - BUDGET_ALERT_THRESHOLD: warn at this % of monthly budget

Accounting model (hito 21):
    `reserve_and_record()` is the SINGLE point where a call is booked. It
    atomically increments both the per-run counter and the monthly spend.
    It is called from HikerAPIClient._get(), after the cache lookup misses
    and before the HTTP request — so cached responses are never charged.

    `record_call()` is kept for non-HikerAPI providers only. Never call it
    for a call that already went through reserve_and_record(): that double
    counts the monthly spend.

Usage:
    fuse = BudgetFuse()
    await fuse.assert_budget_available(run_id)   # raises BudgetExhausted
    allowed = await fuse.reserve_and_record(run_id)  # False if run cap hit
    await fuse.get_current_spend()               # {this_month_usd, pct_used, ...}
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

    _RESERVE_AND_RECORD_SCRIPT = """
local run_key = KEYS[1]
local month_key = KEYS[2]
local max_calls = tonumber(ARGV[1])
local cost = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])

local count = redis.call('GET', run_key)
count = count and tonumber(count) or 0

if count < max_calls then
    redis.call('INCR', run_key)
    redis.call('EXPIRE', run_key, ttl)
    redis.call('INCRBYFLOAT', month_key, cost)
    redis.call('EXPIRE', month_key, 3456000)
    return 1
else
    return 0
end
"""

    def __init__(
        self,
        monthly_budget_usd: float = 10.0,
        max_calls_per_run: int = 120,
        alert_threshold: float = 0.7,
        cost_per_call_usd: float = 0.02,  # HikerAPI plan "Start" — ver config.py
    ):
        self.monthly_budget_usd = monthly_budget_usd
        self.max_calls_per_run = max_calls_per_run
        self.alert_threshold = alert_threshold
        self.cost_per_call_usd = cost_per_call_usd
        self._redis = None
        self._lua_sha = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as redis_async
            from shared_core.config import settings

            self._redis = redis_async.from_url(settings.ARQ_REDIS_URL, decode_responses=False)
        return self._redis

    async def _get_lua_sha(self, r) -> str:
        if self._lua_sha is None:
            self._lua_sha = await r.script_load(self._RESERVE_AND_RECORD_SCRIPT)
        return self._lua_sha

    async def reserve_and_record(self, run_id: str, provider: str = "hikerapi") -> bool:
        """Atomically check and increment run counter + monthly spend.

        Returns True if the call was allowed (counter incremented).
        Returns False if MAX_CALLS_PER_RUN was already reached.

        This closes the TOCTOU race where concurrent coroutines could all
        read counter < limit before any incremented it.

        This is the SINGLE accounting point: it books both the run counter
        and the monthly spend. Do not also call record_call() for the same
        request — that double counts (hito 21).
        """
        month_key = self._month_key(provider)
        run_key = self._run_key(run_id)
        cost = self.cost_per_call_usd
        ttl = 60 * 60 * 24  # 24h

        try:
            r = await self._get_redis()
            try:
                sha = await self._get_lua_sha(r)
                result = await r.evalsha(
                    sha, 2, run_key, month_key,
                    self.max_calls_per_run, cost, ttl,
                )
            except Exception as e:
                # NOSCRIPT: Redis restarted or SCRIPT FLUSH wiped the cache.
                # Fall back to EVAL, which re-registers the script.
                if "NOSCRIPT" not in str(e).upper():
                    raise
                logger.warning("budget_fuse_noscript_fallback")
                self._lua_sha = None
                result = await r.eval(
                    self._RESERVE_AND_RECORD_SCRIPT, 2, run_key, month_key,
                    self.max_calls_per_run, cost, ttl,
                )
            allowed = int(result) == 1
            if allowed:
                logger.info(
                    "budget_fuse_call_reserved",
                    run_id=run_id,
                    provider=provider,
                    cost_usd=cost,
                )
            else:
                logger.warning(
                    "budget_fuse_run_limit_reached",
                    run_id=run_id,
                    provider=provider,
                    max_calls=self.max_calls_per_run,
                )
            return allowed
        except Exception as e:
            # Fail CLOSED (hito 21). A $0.02/call provider with a broken fuse
            # can burn the whole monthly budget in one run. Redis is already a
            # hard dependency (ARQ), so blocking here costs nothing extra.
            logger.error("budget_fuse_reserve_error_failing_closed", error=str(e))
            return False

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

    async def record_call(
        self,
        run_id: str,
        provider: str = "hikerapi",
        call_count: int = 1,
        record_run_counter: bool = True,
    ) -> None:
        """Record API calls and accumulate monthly spend atomically.

        Args:
            record_run_counter: If False, only records monthly spend (no run-key
                increment). Use when run counter is managed atomically via
                reserve_and_record() to avoid double-counting.
        """
        cost = call_count * self.cost_per_call_usd
        month_key = self._month_key(provider)
        run_key = self._run_key(run_id)

        try:
            r = await self._get_redis()
            pipe = r.pipeline()
            pipe.incrbyfloat(month_key, cost)
            pipe.expire(month_key, 60 * 60 * 24 * 40)
            if record_run_counter:
                pipe.incr(run_key)
                pipe.expire(run_key, 60 * 60 * 24)
            await pipe.execute()
            logger.info(
                "budget_fuse_call_recorded",
                run_id=run_id,
                provider=provider,
                calls=call_count,
                cost_usd=cost,
                run_counter_recorded=record_run_counter,
            )
        except Exception as e:
            logger.warning("budget_fuse_record_error", error=str(e))

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

    async def get_run_calls(self, run_id: str) -> int:
        """Número de llamadas HTTP reales cobradas a este run (hito 22).

        Es la fuente de verdad del costo del run: desde el hito 21,
        reserve_and_record() incrementa este contador una vez por request real
        (los cache hits y el modo replay no lo tocan).
        """
        try:
            r = await self._get_redis()
            raw = await r.get(self._run_key(run_id))
            return int(raw) if raw else 0
        except Exception as e:
            logger.warning("budget_fuse_get_run_calls_error", run_id=run_id, error=str(e))
            return 0

    async def reset_run_counter(self, run_id: str) -> None:
        """Delete the per-run call counter. Called at end of run."""
        try:
            r = await self._get_redis()
            await r.delete(self._run_key(run_id))
        except Exception as e:
            logger.warning("budget_fuse_reset_error", run_id=run_id, error=str(e))
