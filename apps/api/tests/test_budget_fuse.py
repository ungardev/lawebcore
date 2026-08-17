"""Tests for Hito 21: single accounting point + NOSCRIPT fallback + fail-closed.

Verifies:
  §2.1: reserve_and_record is the SINGLE point — no double counting
  §2.2: cache hits do not charge budget
  §2.3: NOSCRIPT fallback when Redis restarts or SCRIPT FLUSH
  §2.4: fail closed on Redis errors (not open)
  §2.5: MAX_CALLS_PER_RUN now covers discovery + enrichment (real cap)
"""

from unittest.mock import AsyncMock, MagicMock, patch, ANY

import pytest


class TestSingleAccountingPoint:
    """§2.1 + §2.2: Single reserve_and_record call, no double counting."""

    @pytest.mark.asyncio
    async def test_reserve_and_record_called_once_per_request(self):
        """A single HTTP request to HikerAPI calls reserve_and_record exactly once."""
        from app.core.budget_fuse import BudgetFuse

        fuse = BudgetFuse(cost_per_call_usd=0.02, max_calls_per_run=120)

        mock_redis = AsyncMock()
        mock_redis.script_load = AsyncMock(return_value="abc123")
        mock_redis.evalsha = AsyncMock(return_value=1)

        with patch.object(fuse, "_get_redis", return_value=mock_redis):
            result = await fuse.reserve_and_record("run-001", "hikerapi")

        assert result is True
        mock_redis.evalsha.assert_called_once()
        mock_redis.script_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_reserve_and_record_increments_both_counters(self):
        """reserve_and_record increments both run counter AND monthly spend atomically."""
        from app.core.budget_fuse import BudgetFuse

        fuse = BudgetFuse(cost_per_call_usd=0.02, max_calls_per_run=120)

        mock_redis = AsyncMock()
        mock_redis.script_load = AsyncMock(return_value="abc123")
        mock_redis.evalsha = AsyncMock(return_value=1)

        with patch.object(fuse, "_get_redis", return_value=mock_redis):
            await fuse.reserve_and_record("run-001", "hikerapi")

        call_args = mock_redis.evalsha.call_args
        assert call_args is not None
        _, call_kwargs = call_args
        assert call_args[0][0] == "abc123"
        assert call_args[0][1] == 2
        assert "run_key" in str(call_args) or call_args[0][2] is not None
        assert call_args[0][5] == 0.02

    @pytest.mark.asyncio
    async def test_run_limit_returns_false(self):
        """When MAX_CALLS_PER_RUN is reached, reserve_and_record returns False."""
        from app.core.budget_fuse import BudgetFuse

        fuse = BudgetFuse(cost_per_call_usd=0.02, max_calls_per_run=120)

        mock_redis = AsyncMock()
        mock_redis.script_load = AsyncMock(return_value="abc123")
        mock_redis.evalsha = AsyncMock(return_value=0)

        with patch.object(fuse, "_get_redis", return_value=mock_redis):
            result = await fuse.reserve_and_record("run-001", "hikerapi")

        assert result is False

    @pytest.mark.asyncio
    async def test_cache_hit_does_not_call_reserve(self):
        """When HikerAPIClient._get() serves from cache, reserve_and_record is never called."""
        from discovery.tools.hikerapi_client import HikerAPIClient

        client = HikerAPIClient(api_key="test-key")
        client.budget_fuse = MagicMock()
        client.budget_fuse.reserve_and_record = AsyncMock(return_value=True)
        client.run_id = "run-001"

        with patch.object(client, "_get_cached", return_value={"user": {"username": "test"}}):
            with patch.object(client, "_get_redis", return_value=AsyncMock()):
                result = await client._get("/v2/user/by/username", params={"username": "test"}, cache_ttl=3600)

        assert result is not None
        client.budget_fuse.reserve_and_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_replay_mode_does_not_call_reserve(self):
        """When RUN_MODE=replay and no cache, ReplayMiss is raised without calling reserve."""
        from discovery.tools.hikerapi_client import HikerAPIClient
        from discovery.exceptions import ReplayMiss

        client = HikerAPIClient(api_key="test-key")
        client.budget_fuse = MagicMock()
        client.budget_fuse.reserve_and_record = AsyncMock(return_value=True)
        client.run_id = "run-001"

        with patch.object(client, "_get_cached", return_value=None):
            with patch("discovery.tools.hikerapi_client.settings") as mock_settings:
                mock_settings.RUN_MODE = "replay"
                mock_settings.HIKERAPI_API_KEY = "test"
                mock_settings.ARQ_REDIS_URL = "redis://localhost"
                mock_settings.HIKERAPI_5XX_BREAKER_THRESHOLD = 5
                mock_settings.HIKERAPI_5XX_BREAKER_TTL_S = 300

                with pytest.raises(ReplayMiss):
                    await client._get("/v2/user/by/username", params={"username": "test"}, cache_ttl=0)

        client.budget_fuse.reserve_and_record.assert_not_called()


class TestNoscriptFallback:
    """§2.3: NOSCRIPT fallback when Redis restarts or SCRIPT FLUSH is executed."""

    @pytest.mark.asyncio
    async def test_noscript_triggers_eval_fallback(self):
        """When evalsha raises NOSCRIPT, the code falls back to eval which re-registers the script."""
        from app.core.budget_fuse import BudgetFuse

        fuse = BudgetFuse(cost_per_call_usd=0.02, max_calls_per_run=120)

        mock_redis = AsyncMock()
        mock_redis.script_load = AsyncMock(return_value="abc123")
        mock_redis.evalsha = AsyncMock(side_effect=Exception("NOSCRIPT No matching script"))
        mock_redis.eval = AsyncMock(return_value=1)

        with patch.object(fuse, "_get_redis", return_value=mock_redis):
            result = await fuse.reserve_and_record("run-001", "hikerapi")

        assert result is True
        mock_redis.evalsha.assert_called_once()
        mock_redis.eval.assert_called_once()
        fuse._lua_sha = None

    @pytest.mark.asyncio
    async def test_noscript_error_logged(self):
        """When NOSCRIPT fallback is triggered, a warning log is emitted."""
        from app.core.budget_fuse import BudgetFuse
        import structlog

        fuse = BudgetFuse(cost_per_call_usd=0.02, max_calls_per_run=120)

        mock_redis = AsyncMock()
        mock_redis.script_load = AsyncMock(return_value="abc123")
        mock_redis.evalsha = AsyncMock(side_effect=Exception("NOSCRIPT No matching script"))
        mock_redis.eval = AsyncMock(return_value=1)

        with patch.object(fuse, "_get_redis", return_value=mock_redis):
            with patch("structlog.get_logger") as mock_logger:
                mock_logger.return_value.warning = MagicMock()
                await fuse.reserve_and_record("run-001", "hikerapi")
                mock_logger.return_value.warning.assert_called()
                call_args = mock_logger.return_value.warning.call_args
                assert "budget_fuse_noscript_fallback" in str(call_args)

        fuse._lua_sha = None

    @pytest.mark.asyncio
    async def test_non_noscript_exception_raised(self):
        """Non-NOSCRIPT exceptions are re-raised, not caught by the fallback."""
        from app.core.budget_fuse import BudgetFuse

        fuse = BudgetFuse(cost_per_call_usd=0.02, max_calls_per_run=120)

        mock_redis = AsyncMock()
        mock_redis.script_load = AsyncMock(return_value="abc123")
        mock_redis.evalsha = AsyncMock(side_effect=ConnectionError("Redis connection refused"))

        with patch.object(fuse, "_get_redis", return_value=mock_redis):
            with pytest.raises(ConnectionError):
                await fuse.reserve_and_record("run-001", "hikerapi")


class TestFailClosedOnRedisError:
    """§2.4: fail closed on Redis errors — return False instead of True (dangerous at $0.02/call)."""

    @pytest.mark.asyncio
    async def test_redis_connection_error_returns_false(self):
        """When Redis is unavailable, reserve_and_record returns False (fail closed)."""
        from app.core.budget_fuse import BudgetFuse

        fuse = BudgetFuse(cost_per_call_usd=0.02, max_calls_per_run=120)

        mock_redis = AsyncMock()
        mock_redis.script_load = AsyncMock(side_effect=ConnectionError("Connection refused"))

        with patch.object(fuse, "_get_redis", return_value=mock_redis):
            result = await fuse.reserve_and_record("run-001", "hikerapi")

        assert result is False, "Should return False (fail closed), not True"

    @pytest.mark.asyncio
    async def test_redis_error_logged_as_error(self):
        """Redis errors are logged as error, not warning (fail closed = serious)."""
        from app.core.budget_fuse import BudgetFuse
        import structlog

        fuse = BudgetFuse(cost_per_call_usd=0.02, max_calls_per_run=120)

        mock_redis = AsyncMock()
        mock_redis.script_load = AsyncMock(side_effect=ConnectionError("Connection refused"))

        with patch.object(fuse, "_get_redis", return_value=mock_redis):
            with patch("structlog.get_logger") as mock_logger:
                mock_logger.return_value.error = MagicMock()
                await fuse.reserve_and_record("run-001", "hikerapi")
                mock_logger.return_value.error.assert_called()
                call_args = mock_logger.return_value.error.call_args
                assert "budget_fuse_reserve_error_failing_closed" in str(call_args)


class TestDiscoveryCountsAgainstRunCap:
    """§2.5: MAX_CALLS_PER_RUN now covers discovery calls too (was only enrichment before)."""

    @pytest.mark.asyncio
    async def test_discovery_call_increments_run_counter(self):
        """A discovery call (search_hashtag) should call reserve_and_record."""
        from discovery.tools.hikerapi_client import HikerAPIClient

        client = HikerAPIClient(api_key="test-key")

        fuse = MagicMock()
        fuse.reserve_and_record = AsyncMock(return_value=True)
        fuse.max_calls_per_run = 120
        client.budget_fuse = fuse
        client.run_id = "run-001"

        with patch.object(client, "_get_cached", return_value=None):
            with patch.object(client, "_get_client") as mock_get_client:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(return_value={"id": "123", "media_count": 1000})
                mock_response.raise_for_status = MagicMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                with patch("discovery.tools.hikerapi_client.settings") as mock_settings:
                    mock_settings.RUN_MODE = "live"
                    mock_settings.HIKERAPI_API_KEY = "test"
                    mock_settings.ARQ_REDIS_URL = "redis://localhost"
                    mock_settings.HIKERAPI_5XX_BREAKER_THRESHOLD = 5
                    mock_settings.HIKERAPI_5XX_BREAKER_TTL_S = 300

                    result = await client._get("/v2/hashtag/by/name", params={"name": "test"}, cache_ttl=0)

        fuse.reserve_and_record.assert_called_once_with("run-001", provider="hikerapi")

    @pytest.mark.asyncio
    async def test_enrichment_call_increments_run_counter(self):
        """An enrichment call (enrich_profile) should call reserve_and_record."""
        from discovery.tools.hikerapi_client import HikerAPIClient

        client = HikerAPIClient(api_key="test-key")

        fuse = MagicMock()
        fuse.reserve_and_record = AsyncMock(return_value=True)
        fuse.max_calls_per_run = 120
        client.budget_fuse = fuse
        client.run_id = "run-001"

        with patch.object(client, "_get_cached", return_value=None):
            with patch.object(client, "_get_client") as mock_get_client:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(return_value={"user": {"username": "test", "pk": "123"}})
                mock_response.raise_for_status = MagicMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                with patch("discovery.tools.hikerapi_client.settings") as mock_settings:
                    mock_settings.RUN_MODE = "live"
                    mock_settings.HIKERAPI_API_KEY = "test"
                    mock_settings.ARQ_REDIS_URL = "redis://localhost"
                    mock_settings.HIKERAPI_5XX_BREAKER_THRESHOLD = 5
                    mock_settings.HIKERAPI_5XX_BREAKER_TTL_S = 300

                    result = await client._get("/v2/user/by/username", params={"username": "test"}, cache_ttl=0)

        fuse.reserve_and_record.assert_called_once_with("run-001", provider="hikerapi")


class TestBudgetExhaustedRaises:
    """When reserve_and_record returns False, HikerAPIClient._get() raises BudgetExhausted."""

    @pytest.mark.asyncio
    async def test_budget_exhausted_raised_when_reserve_fails(self):
        """When reserve_and_record returns False (cap hit), BudgetExhausted is raised."""
        from discovery.tools.hikerapi_client import HikerAPIClient
        from discovery.exceptions import BudgetExhausted

        client = HikerAPIClient(api_key="test-key")

        fuse = MagicMock()
        fuse.reserve_and_record = AsyncMock(return_value=False)
        fuse.max_calls_per_run = 5
        fuse.monthly_budget_usd = 10.0
        client.budget_fuse = fuse
        client.run_id = "run-001"

        with patch.object(client, "_get_cached", return_value=None):
            with patch("discovery.tools.hikerapi_client.settings") as mock_settings:
                mock_settings.RUN_MODE = "live"
                mock_settings.HIKERAPI_API_KEY = "test"
                mock_settings.ARQ_REDIS_URL = "redis://localhost"
                mock_settings.HIKERAPI_5XX_BREAKER_THRESHOLD = 5
                mock_settings.HIKERAPI_5XX_BREAKER_TTL_S = 300

                with pytest.raises(BudgetExhausted) as exc_info:
                    await client._get("/v2/user/by/username", params={"username": "test"}, cache_ttl=0)

                assert "Límite de llamadas por run alcanzado" in str(exc_info.value)


class TestDefaultCostPerCall:
    """Verifies that the default cost_per_call_usd in BudgetFuse is 0.02 (HikerAPI plan Start)."""

    def test_budget_fuse_default_cost_is_0_02(self):
        """Default cost_per_call_usd should be 0.02, not the legacy 0.0006."""
        from app.core.budget_fuse import BudgetFuse

        fuse = BudgetFuse()
        assert fuse.cost_per_call_usd == 0.02, (
            f"Default cost_per_call_usd should be 0.02 (HikerAPI Start plan), "
            f"got {fuse.cost_per_call_usd}"
        )
