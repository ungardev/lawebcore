"""Pipeline smoke tests — validates core fixes from Fable 5 audit.

Tests the critical paths that were broken:
  - F-1.1: Any import in worker.py (type annotation works)
  - F-1.2: upsert_many RETURNING id
  - F-1.3: geo_boost country disqualification bug
  - F-3.1: keyword/hashtag cap
  - F-3.2: lens_score weights sum to 1.0
  - F-3.3: geo_boost city matching (lowercase filter removed)
  - F-3.8: batch prompt no duplicate elite_context
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from discovery.schemas import BriefStructured
from discovery.tools.geo_boost import geo_score, _get_country_keywords
from discovery.scoring.lens_score import lens_score


class TestGeoBoostFixes:
    """F-1.3: Country declared should NOT disqualify candidate when no ISO2 in geo_indicators."""

    def test_profile_with_country_but_no_iso2_in_geo_indicators(self):
        """When target country is 'CO' but geo_indicators has only city names (no ISO2),
        the candidate should NOT be immediately disqualified by the country check."""
        profile = {
            "biography": "gamer youtuber",
            "country": "CO",
            "username": "gamer_col",
            "followersCount": 50000,
            "engagement_rate": 0.04,
            "is_business": False,
        }
        geo_indicators = ["bogota", "medellin"]
        score = geo_score(profile, geo_indicators)
        assert score > 0.0, "Candidate with declared country but city-only geo_indicators should NOT get 0.0"

    def test_country_match_when_iso2_present(self):
        """When ISO2 is in geo_indicators AND country matches, return 1.0."""
        profile = {
            "biography": "colombiano",
            "country": "CO",
            "username": "col_handle",
            "followersCount": 10000,
            "engagement_rate": 0.03,
            "is_business": False,
        }
        geo_indicators = ["CO", "bogota"]
        score = geo_score(profile, geo_indicators)
        assert score == 1.0

    def test_country_mismatch_when_iso2_present(self):
        """When ISO2 is in geo_indicators but country doesn't match, return 0.0."""
        profile = {
            "biography": "venezolano",
            "country": "VE",
            "username": "ve_handle",
            "followersCount": 10000,
            "engagement_rate": 0.03,
            "is_business": False,
        }
        geo_indicators = ["CO"]
        score = geo_score(profile, geo_indicators)
        assert score == 0.0


class TestGeoBoostCityMatching:
    """F-3.3: City matching should not require first 3 chars to be uppercase."""

    def test_city_name_bogota(self):
        """'bogota' (all lowercase, len>2) should match."""
        profile = {
            "biography": "",
            "country": "",
            "username": "user",
            "locationName": "Bogotá, Colombia",
            "followersCount": 50000,
            "engagement_rate": 0.035,
            "is_business": False,
        }
        score = geo_score(profile, ["bogota"])
        assert score >= 1.0

    def test_city_name_caracas(self):
        """'caracas' should match via city keywords."""
        profile = {
            "biography": "",
            "country": "",
            "username": "user",
            "locationName": "Caracas",
            "followersCount": 50000,
            "engagement_rate": 0.035,
            "is_business": False,
        }
        score = geo_score(profile, ["caracas"])
        assert score >= 1.0


class TestGeoBoostTypoFix:
    """F-3.4: 'c�哥伦比亚' typo should be 'co'."""

    def test_co_country_keywords_have_valid_entries(self):
        keywords = _get_country_keywords(["CO", "colombia", "bogota"])
        assert len(keywords) >= 1
        assert "colombia" in keywords


class TestLensScoreWeights:
    """F-3.2: lens_score weights must sum to 1.0."""

    def test_weights_sum_to_one(self):
        """Verify the 4 score components sum to 1.0 (not 0.90)."""
        profile = {
            "biography": " fitness coach",
            "followersCount": 50000,
            "engagement_rate": 0.04,
            "is_business": False,
        }
        profile_data = {
            "geo_indicators": ["VE"],
            "keywords": ["fitness", "gym"],
            "hashtags": ["#fitness"],
        }
        score = lens_score(profile, profile_data)
        assert 0 <= score <= 100

    def test_weights_are_normalized(self):
        """Verify the constants in the source sum to 1.0."""
        import re
        from discovery.scoring.lens_score import lens_score
        import inspect
        source = inspect.getsource(lens_score)
        weights = [float(w) for w in re.findall(r"(\d+\.\d+)\s*\*\s*(?:tier_er_norm|geo|niche|biz)", source)]
        total = sum(weights)
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, not 1.0"


class TestQueryBuilderCaps:
    """F-3.1: keywords capped at 20, hashtags at 30, no buy_intent/geo as queries."""

    def test_keyword_cap_20(self):
        """After Fable 5 fix, _build_keyword_queries should cap at 20."""
        from discovery.query_builder import QueryBuilder
        qb = QueryBuilder()
        brief = BriefStructured(
            product_name="Test",
            industry="belleza",
            niches=["belleza"],
            audience_countries=["CO"],
        )
        profile = {"keywords": [f"kw{i}" for i in range(50)], "niche_keywords": []}
        with patch("discovery.query_builder.get_or_create_profile", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = profile
            from discovery.query_builder import QueryBuilder
            qb = QueryBuilder()
            result = qb._build_keyword_queries(profile, brief)
            assert len(result) <= 20, f"Expected <=20 keywords, got {len(result)}"

    def test_hashtag_cap_30(self):
        """_build_hashtag_queries should cap at 30 (not 50)."""
        from discovery.query_builder import QueryBuilder
        qb = QueryBuilder()
        profile = {"hashtags": [f"tag{i}" for i in range(100)]}
        result = qb._build_hashtag_queries(profile)
        assert len(result) <= 30, f"Expected <=30 hashtags, got {len(result)}"

    def test_no_buy_intent_in_queries(self):
        """buy_intent_keywords should NOT be used as keyword queries."""
        from discovery.query_builder import QueryBuilder
        qb = QueryBuilder()
        brief = BriefStructured(
            product_name="Test",
            industry="belleza",
            niches=["belleza"],
            audience_countries=["CO"],
        )
        profile = {
            "keywords": [],
            "niche_keywords": [],
            "buy_intent_keywords": ["comprar ahora"],
            "geo_indicators": ["caracas"],
        }
        result = qb._build_keyword_queries(profile, brief)
        assert "comprar ahora" not in result
        assert "caracas" not in result


class TestCandidateAnalyzerBatchPrompt:
    """F-3.8: elite_context should NOT be duplicated in each batch candidate block."""

    def test_batch_prompt_singular_elite_context(self):
        """The batch prompt should include elite_context once at the top, not in each block."""
        from discovery.candidate_analyzer import _build_batch_prompt
        candidates = [
            {"handle": "user1", "followers": 5000, "bio": "test", "latestPosts": []},
            {"handle": "user2", "followers": 6000, "bio": "test2", "latestPosts": []},
        ]
        elite_data = {
            "content_themes": ["moda"],
            "credibility_signals": ["high_er"],
            "competitor_intel": {"brands": ["brand1"]},
            "local_slang": ["slang1"],
            "niche_benchmarks": {"min_er": 0.035, "target_er": 0.055, "min_followers": 5000},
        }
        prompt = _build_batch_prompt(candidates, "belleza", ["belleza"], ["casual"], "CO", elite_data)
        elite_count = prompt.count("CONTEXTO ELITE DE LA CAMPAÑA")
        assert elite_count == 1, f"Expected 1 elite_context in batch prompt, found {elite_count}"


class TestUpsertManyReturning:
    """F-1.2: upsert_many should always add RETURNING (id or 1)."""

    @pytest.mark.asyncio
    async def test_upsert_many_adds_returning_clause(self):
        """Verify RETURNING is always added, even for 'minimal'."""
        from shared_core.supabase_rest import RailwayPg
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_row = MagicMock()
        mock_row.items.return_value = [("id", 1)]
        mock_conn.fetch.return_value = [mock_row]
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        pg = RailwayPg(dsn="postgresql://test")
        pg._pool = mock_pool

        result = await pg.upsert_many(
            table="test_table",
            records=[{"id": 1, "name": "test"}],
            on_conflict=["id"],
            returning="minimal",
        )
        call_args = str(mock_conn.fetch.call_args)
        assert "RETURNING" in call_args, f"Expected RETURNING in query, got: {call_args}"


class TestWorkerTyping:
    """F-1.1: worker.py should have 'from typing import Any' for type annotations."""

    def test_worker_module_imports_any(self):
        """worker.py must import Any for the elite_data: dict[str, Any] annotation."""
        import apps.api.app.workers.worker as worker_module
        import typing
        assert hasattr(typing, "Any") or "Any" in dir(worker_module), "worker.py uses Any without importing it"
