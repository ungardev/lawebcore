"""Tests for apify_client — cache, cost tracking, retry logic."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from discovery.tools.apify_client import ApifyClient


class TestApifyClientCostTracking:
    """M2 fix: CostTracker must accumulate costs per discovery run."""

    def test_record_and_get_cost(self):
        client = ApifyClient(token="test")
        client.discovery_run_id = "run-123"

        client.record_cost("run-123", 0.50)
        client.record_cost("run-123", 0.30)

        assert client.get_total_cost("run-123") == pytest.approx(0.80)
        assert client.get_and_clear_cost("run-123") == pytest.approx(0.80)
        assert client.get_total_cost("run-123") == 0.0

    def test_costs_are_per_run(self):
        client = ApifyClient(token="test")
        client.discovery_run_id = "run-1"

        client.record_cost("run-1", 0.25)
        client.record_cost("run-2", 0.75)

        assert client.get_total_cost("run-1") == pytest.approx(0.25)
        assert client.get_total_cost("run-2") == pytest.approx(0.75)


class TestApifyClientCacheKey:
    """Cache key must be deterministic regardless of dict key order."""

    def test_cache_key_deterministic(self):
        client = ApifyClient(token="test")

        key1 = client._build_cache_key("actor-1", {"a": 1, "b": 2})
        key2 = client._build_cache_key("actor-1", {"b": 2, "a": 1})

        assert key1 == key2, "Cache key must be same regardless of dict key order"

    def test_different_input_different_key(self):
        client = ApifyClient(token="test")

        key1 = client._build_cache_key("actor-1", {"username": "doglover"})
        key2 = client._build_cache_key("actor-1", {"username": "catlover"})

        assert key1 != key2, "Different input must produce different cache key"

    def test_cache_key_format(self):
        client = ApifyClient(token="test")
        key = client._build_cache_key("apify~instagram-profile-scraper", {"usernames": ["doglover"]})

        assert key.startswith("apify:cache:apify~instagram-profile-scraper:")


class TestApifyClientRetry:
    """M4 fix: Retry/backoff on 429/5xx errors."""

    def test_is_retryable_429(self):
        import httpx
        client = ApifyClient(token="test")

        exc = httpx.HTTPStatusError("rate limited", request=MagicMock(), response=MagicMock(status_code=429))
        assert client._is_retryable_error(exc) is True

    def test_is_retryable_500(self):
        import httpx
        client = ApifyClient(token="test")

        exc = httpx.HTTPStatusError("server error", request=MagicMock(), response=MagicMock(status_code=500))
        assert client._is_retryable_error(exc) is True

    def test_is_retryable_404_not_retryable(self):
        import httpx
        client = ApifyClient(token="test")

        exc = httpx.HTTPStatusError("not found", request=MagicMock(), response=MagicMock(status_code=404))
        assert client._is_retryable_error(exc) is False

    def test_is_retryable_timeout(self):
        client = ApifyClient(token="test")

        assert client._is_retryable_error(TimeoutError("timed out")) is True
        assert client._is_retryable_error(asyncio.TimeoutError()) is True

    def test_is_not_retryable_other(self):
        import httpx
        client = ApifyClient(token="test")

        exc = httpx.HTTPStatusError("bad request", request=MagicMock(), response=MagicMock(status_code=400))
        assert client._is_retryable_error(exc) is False


import asyncio
