"""Tests for result_ranker — LWFA scoring, ER normalization, composite scale."""

import pytest
from discovery.result_ranker import (
    calculate_lwfa_composite,
    calculate_ica,
    calculate_geo_foco_real,
    ResultRanker,
)
from discovery.schemas import BriefStructured, CandidateMetrics, Platform


class TestCalculateLwfaComposite:
    """H1 fix verification: composite must return 0–100."""

    def test_composite_is_0_to_100_scale(self):
        """Composite score must be on 0–100 scale, not 0–1."""
        result = calculate_lwfa_composite(
            engagement_rate=0.03,
            business_intent=0.5,
            velocity_score=50.0,
            geo_foco=0.8,
            consistency_score=0.5,
            clips_pct=30.0,
            ica_score=25.0,
        )
        assert 0 <= result <= 100, f"Composite {result} out of 0-100 range"
        assert result > 1.0, "Composite appears to still be on 0-1 scale"

    def test_composite_zero_for_minimal_values(self):
        result = calculate_lwfa_composite(
            engagement_rate=0.0,
            business_intent=0.0,
            velocity_score=0.0,
            geo_foco=0.0,
            consistency_score=0.0,
            clips_pct=0.0,
            ica_score=0.0,
        )
        assert result == 0.0

    def test_composite_good_candidate_exceeds_15(self):
        """A 'good' candidate must score > 15 to pass MIN_SCORE filter."""
        result = calculate_lwfa_composite(
            engagement_rate=0.05,
            business_intent=0.8,
            velocity_score=80.0,
            geo_foco=0.9,
            consistency_score=0.7,
            clips_pct=40.0,
            ica_score=30.0,
        )
        assert result > 15, f"Good candidate scored {result}, should exceed MIN_SCORE=15"

    def test_ica_influences_composite(self):
        """M1 fix: ICA score must affect composite."""
        base = calculate_lwfa_composite(
            engagement_rate=0.03,
            business_intent=0.5,
            velocity_score=50.0,
            geo_foco=0.8,
            consistency_score=0.5,
            clips_pct=0.0,
            ica_score=0.0,
        )
        with_ica = calculate_lwfa_composite(
            engagement_rate=0.03,
            business_intent=0.5,
            velocity_score=50.0,
            geo_foco=0.8,
            consistency_score=0.5,
            clips_pct=0.0,
            ica_score=50.0,
        )
        assert with_ica > base, "ICA score should increase composite"


class TestCalculateIca:
    """M1 fix: ICA must use real BUY_INTENT detection."""

    def test_ica_returns_zero_for_empty(self):
        assert calculate_ica([], 0) == 0.0
        assert calculate_ica(None, 1000) == 0.0

    def test_ica_detects_buy_intent(self):
        comments = [
            "donde lo puedo comprar",
            "tiene disponible en tienda",
            "me encanta este reels",
            "cuanto cuesta",
            "envio a provincia?",
            "que bonito",
        ]
        result = calculate_ica(comments, views=1000)
        assert result > 0, "Should detect buy intent in comments with price/link keywords"
        assert result <= 100, "ICA must be 0-100"

    def test_ica_zero_for_no_buy_intent(self):
        comments = ["me encanta", "que lindo", "wow fantastic"]
        result = calculate_ica(comments, views=1000)
        assert result == 0.0


class TestCalculateGeoFoco:
    """Geo-Foco Real for Venezuela validation."""

    def test_geo_foco_ve_signals(self):
        result = calculate_geo_foco_real(
            geotags=["Caracas, Venezuela", "Maracaibo"],
            captions=["Un día en Caracas 🇻🇪", "Probando producto"],
            profile_bio="Venezolano de Caracas",
        )
        assert result > 0.5, "Profile with VE signals should score > 0.5"

    def test_geo_foco_no_signals(self):
        result = calculate_geo_foco_real(
            geotags=[],
            captions=[],
            profile_bio="",
        )
        assert result == 0.5, "No signals should return neutral 0.5"


class TestResultRanker:
    """End-to-end ranker tests."""

    def test_rank_good_candidate(self):
        ranker = ResultRanker()
        candidate = CandidateMetrics(
            platform=Platform.INSTAGRAM,
            handle="test_influencer",
            followers=15000,
            following=500,
            posts_count=200,
            engagement_rate=0.06,
            country="VE",
            city="Caracas",
            bio="Amante de los perros 🐶",
            audience_gender_split={"female": 0.65, "male": 0.35},
            audience_age_buckets={"18-24": 0.4, "25-34": 0.4},
            audience_interests=["mascotas", "perros"],
        )
        brief = BriefStructured(
            product_name="Dog Chow",
            industry="pet_food",
            niches=["mascotas"],
            audience_gender="all",
            audience_age_min=18,
            audience_age_max=45,
            audience_countries=["VE"],
            audience_cities=["Caracas"],
        )
        result = ranker.rank(candidate, brief)

        assert result.match_score > 15, f"Match score {result.match_score} should exceed MIN_SCORE"
        assert result.niche_relevance > 0
        assert result.geo_relevance > 0

    def test_rank_no_followers_zero_score(self):
        """Profile with 0 followers should not score high."""
        ranker = ResultRanker()
        candidate = CandidateMetrics(
            platform=Platform.INSTAGRAM,
            handle="nobody",
            followers=0,
            following=0,
            posts_count=0,
            engagement_rate=0.0,
        )
        brief = BriefStructured(
            product_name="Dog Chow",
            industry="pet_food",
            niches=["mascotas"],
            audience_gender="all",
            audience_age_min=18,
            audience_age_max=45,
            audience_countries=["VE"],
        )
        result = ranker.rank(candidate, brief)
        assert result.match_score < 15, "Zero-follower profile should not pass MIN_SCORE"
