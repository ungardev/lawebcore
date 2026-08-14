"""Circuit breaker for HikerAPI — prevents calling a degraded provider.

State machine:
  CLOSED (normal) -> failures accumulate
  After FAILURE_THRESHOLD consecutive failures -> OPEN
  After BREAKER_TTL_S in OPEN -> HALF-OPEN (allow 1 test call)
  Test call succeeds -> CLOSED (counter resets)
  Test call fails -> OPEN again

Uses Redis for state so it survives worker restarts and is shared
across all concurrent runs.
"""

import json
import time
from dataclasses import dataclass
from enum import StrEnum

import redis
import redis.asyncio as redis_async
import structlog

logger = structlog.get_logger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    breaker_ttl_s: int = 300
    half_open_test_timeout_s: int = 5


@dataclass
class CircuitBreakerResult:
    state: CircuitState
    consecutive_failures: int
    opened_at: float | None


class HikerAPICircuitBreaker:
    """Redis-backed circuit breaker for HikerAPI.

    Usage:
        breaker = HikerAPICircuitBreaker()
        await breaker.record_success()
        await breaker.record_failure(status_code=502)
        if not await breaker.can_proceed():
            raise SourceUnavailable("Circuit breaker open", provider="hikerapi")
    """

    def __init__(
        self,
        provider: str = "hikerapi",
        config: CircuitBreakerConfig | None = None,
    ):
        self.provider = provider
        self.config = config or CircuitBreakerConfig()
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            from shared_core.config import settings

            self._redis = redis_async.from_url(settings.ARQ_REDIS_URL, decode_responses=False)
        return self._redis

    def _key(self, suffix: str) -> str:
        return f"lens:cb:{self.provider}:{suffix}"

    async def _get_state(self) -> CircuitBreakerResult:
        try:
            r = await self._get_redis()
            raw = await r.get(self._key("state"))
            if not raw:
                return CircuitBreakerResult(
                    state=CircuitState.CLOSED,
                    consecutive_failures=0,
                    opened_at=None,
                )
            data = json.loads(raw)
            return CircuitBreakerResult(
                state=CircuitState(data.get("state", CircuitState.CLOSED)),
                consecutive_failures=data.get("failures", 0),
                opened_at=data.get("opened_at"),
            )
        except (json.JSONDecodeError, redis.RedisError, OSError) as e:
            logger.warning("circuit_breaker_redis_error", error=str(e))
            return CircuitBreakerResult(
                state=CircuitState.CLOSED,
                consecutive_failures=0,
                opened_at=None,
            )

    async def _set_state(self, state: CircuitState, failures: int, opened_at: float | None) -> None:
        try:
            r = await self._get_redis()
            data = {
                "state": str(state),
                "failures": failures,
                "opened_at": opened_at,
            }
            if state == CircuitState.OPEN:
                await r.setex(self._key("state"), self.config.breaker_ttl_s * 3, json.dumps(data))
            else:
                await r.set(self._key("state"), json.dumps(data))
        except (redis_async.RedisError, OSError) as e:
            logger.warning("circuit_breaker_redis_write_error", error=str(e))

    async def can_proceed(self) -> bool:
        """Returns True if calls are allowed. False if circuit is OPEN."""
        result = await self._get_state()
        if result.state == CircuitState.CLOSED:
            return True
        if result.state == CircuitState.OPEN:
            if result.opened_at and (time.time() - result.opened_at) >= self.config.breaker_ttl_s:
                await self._set_state(CircuitState.HALF_OPEN, failures=0, opened_at=None)
                logger.info("circuit_breaker_half_open", provider=self.provider)
                return True
            return False
        if result.state == CircuitState.HALF_OPEN:
            return True
        return True

    async def record_success(self) -> None:
        """Reset failures counter and close circuit."""
        current = await self._get_state()
        if current.state != CircuitState.CLOSED:
            logger.info("circuit_breaker_closed", provider=self.provider)
        await self._set_state(CircuitState.CLOSED, failures=0, opened_at=None)

    async def record_failure(self, status_code: int | None = None) -> None:
        """Record a failure. Opens circuit after FAILURE_THRESHOLD consecutive failures."""
        if status_code and status_code < 500:
            return
        current = await self._get_state()
        new_failures = current.consecutive_failures + 1
        if new_failures >= self.config.failure_threshold:
            logger.warning(
                "circuit_breaker_opened",
                provider=self.provider,
                failures=new_failures,
            )
            await self._set_state(CircuitState.OPEN, failures=new_failures, opened_at=time.time())
        else:
            await self._set_state(current.state, failures=new_failures, opened_at=current.opened_at)
            logger.info(
                "circuit_breaker_failure",
                provider=self.provider,
                failures=new_failures,
                threshold=self.config.failure_threshold,
            )

    async def get_status(self) -> CircuitBreakerResult:
        """Return current circuit state for observability."""
        return await self._get_state()
