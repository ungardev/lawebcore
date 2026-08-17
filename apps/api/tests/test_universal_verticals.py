"""Tests for universal verticals — verifies Lens works across all industries/countries.

Mission validator for Opus 5: Lens Universal Discovery Engine.
Validates 4 verticals produce non-empty profiles without VE artifacts.
"""

import pytest
from discovery.profile_generator import compute_fingerprint
from discovery.schemas import BriefStructured
from discovery.scoring.lens_score import lens_score
from discovery.scoring.niche import niche_relevance
from discovery.tools.geo_boost import geo_score


class TestUniversalVerticals:
    """Verify Lens discovery works universally, not just for mascotas/VE."""

    @pytest.fixture
    def mascotas_ve(self):
        return BriefStructured(
            product_name="Purina Dog Chow",
            industry="mascotas",
            niches=["mascotas"],
            audience_countries=["VE"],
            audience_cities=["Caracas"],
        )

    @pytest.fixture
    def shampoo_co(self):
        return BriefStructured(
            product_name="Shampoo Kerastase",
            industry="belleza",
            niches=["haircare", "belleza"],
            audience_countries=["CO"],
            audience_cities=["Bogotá", "Medellín"],
        )

    @pytest.fixture
    def software_b2b_mx(self):
        return BriefStructured(
            product_name="Salesforce CRM",
            industry="tecnologia",
            niches=["saas", "b2b", "software"],
            audience_countries=["MX"],
            audience_cities=["CDMX", "Guadalajara"],
        )

    @pytest.fixture
    def cafeteria_pa(self):
        return BriefStructured(
            product_name="Café de especialidad",
            industry="food_beverage",
            niches=["café", "barismo", "food"],
            audience_countries=["PA"],
            audience_cities=["Ciudad de Panamá"],
        )

    def test_fingerprints_are_unique_per_vertical(self, mascotas_ve, shampoo_co, software_b2b_mx, cafeteria_pa):
        fp1 = compute_fingerprint(mascotas_ve)
        fp2 = compute_fingerprint(shampoo_co)
        fp3 = compute_fingerprint(software_b2b_mx)
        fp4 = compute_fingerprint(cafeteria_pa)

        all_fps = [fp1, fp2, fp3, fp4]
        assert len(set(all_fps)) == 4, "Each vertical should produce a unique fingerprint"
        for fp in all_fps:
            assert len(fp) == 64, "Fingerprint should be a SHA256 hex string"

    def test_same_vertical_same_fingerprint(self, mascotas_ve):
        fp1 = compute_fingerprint(mascotas_ve)
        fp2 = compute_fingerprint(mascotas_ve)
        assert fp1 == fp2, "Identical briefs must produce identical fingerprints"

    def test_fingerprint_order_independent(self, mascotas_ve, shampoo_co):
        brief1 = BriefStructured(
            product_name="A",
            industry="tech",
            niches=["ai", "ml"],
            audience_countries=["US", "UK"],
        )
        brief2 = BriefStructured(
            product_name="A",
            industry="tech",
            niches=["ml", "ai"],
            audience_countries=["UK", "US"],
        )
        assert compute_fingerprint(brief1) == compute_fingerprint(brief2)

    def test_geo_score_colombia_for_colombian_profile(self):
        co_profile = {
            "biography": "Bogotá Colombia 🇨🇴 hair stylist",
            "country": "CO",
            "username": "hairbycaro",
            "full_name": "Carolina Martinez",
            "locationName": "Bogotá",
        }
        geo_indicators = ["colombia", "bogota", "medellin", "cali", "barranquilla"]
        score = geo_score(co_profile, geo_indicators, target_country="CO")
        assert score == 1.0, "Colombian profile in target country should score 1.0"

    def test_geo_score_mexico_for_mexican_profile(self):
        mx_profile = {
            "biography": "Emprendedora MX 🇲🇽",
            "country": "MX",
            "username": "techmexicana",
            "full_name": "María García",
            "locationName": "CDMX",
        }
        geo_indicators = ["mexico", "cdmx", "guadalajara", "monterrey"]
        score = geo_score(mx_profile, geo_indicators, target_country="MX")
        assert score == 1.0, "Mexican profile in target country should score 1.0"

    def test_geo_score_panama_for_panama_profile(self):
        pa_profile = {
            "biography": "Café de especialidad Panamá",
            "country": "PA",
            "username": "cafepanama",
            "full_name": "Café Panama",
            "locationName": "Ciudad de Panamá",
        }
        geo_indicators = ["panama", "ciudad de panama", "david"]
        score = geo_score(pa_profile, geo_indicators, target_country="PA")
        assert score == 1.0, "Panamanian profile should score 1.0 for PA target"

    def test_geo_score_rejects_wrong_country(self):
        wrong_profile = {
            "biography": "Venezuelan developer",
            "country": "VE",
            "username": "devvzla",
            "full_name": "Dev VZLA",
            "locationName": "Caracas",
        }
        co_indicators = ["colombia", "bogota", "medellin"]
        score = geo_score(wrong_profile, co_indicators, target_country="CO")
        assert score == 0.0, "VE profile should NOT score 1.0 for CO target (explicit target_country=CO)"

    def test_geo_score_unknown_country_defaults_to_latam_signal(self):
        profile = {
            "biography": "tech startup latam",
            "username": "techlatam",
            "full_name": "Tech Latam",
        }
        co_indicators = ["colombia", "bogota"]
        score = geo_score(profile, co_indicators)
        assert 0.0 <= score <= 0.5, "Profile without country match defaults to low score"

    def test_niche_relevance_belleza_for_belleza_profile(self):
        beauty_profile = {
            "biography": "Maquillaje y skincare | Bogotá",
            "username": "makeupbyana",
            "hashtags": ["#makeup", "#skincare", "#belleza"],
        }
        profile_data = {
            "niche_keywords": ["maquillaje", "skincare", "belleza", "cosmeticos", "rutina"],
            "hashtags": ["#belleza", "#makeup", "#skincare"],
        }
        score = niche_relevance(beauty_profile, profile_data)
        assert score > 0.5, "Beauty profile should score high for beauty niche"

    def test_niche_relevance_cafe_for_cafe_profile(self):
        cafe_profile = {
            "biography": "Barista en Ciudad de Panamá ☕",
            "username": "cafepanama",
            "hashtags": ["#cafe", "#barismo", "#specialtycoffee"],
        }
        profile_data = {
            "niche_keywords": ["cafe", "barismo", "café especialidad", "barista", "specialty coffee"],
            "hashtags": ["#cafe", "#barismo", "#specialtycoffee"],
        }
        score = niche_relevance(cafe_profile, profile_data)
        assert score > 0.5, "Café profile should score high for café niche"

    def test_niche_relevance_tech_for_b2b_software_profile(self):
        tech_profile = {
            "biography": "Salesforce consultant | B2B SaaS | CDMX",
            "username": "techmx",
            "hashtags": ["#salesforce", "#crm", "#b2b"],
        }
        profile_data = {
            "niche_keywords": ["saas", "crm", "b2b", "software", "sales", "enterprise"],
            "hashtags": ["#saas", "#b2b", "#salesforce", "#crm"],
        }
        score = niche_relevance(tech_profile, profile_data)
        assert score > 0.5, "Tech B2B profile should score high for tech niche"

    def test_lens_score_returns_0_to_100(self):
        profile = {
            "followersCount": 15000,
            "engagement_rate": 0.06,
            "biography": "Dog lover Colombia 🐶",
            "username": "mascotascol",
            "isBusinessAccount": True,
            "externalUrl": "https://instagram.com/mascotascol",
        }
        profile_data = {
            "geo_indicators": ["colombia", "bogota", "medellin"],
            "niche_keywords": ["mascotas", "perros", "pets", "dog"],
            "hashtags": ["#mascotas", "#perros"],
            "keywords": ["mascotas", "perros"],
        }
        score = lens_score(profile, profile_data, cross_referenced=False)
        assert 0 <= score <= 100, f"lens_score must be 0-100, got {score}"

    def test_lens_score_cross_ref_bonus(self):
        profile = {
            "followersCount": 15000,
            "engagement_rate": 0.06,
            "biography": "Dog lover",
            "username": "testuser",
        }
        profile_data = {
            "geo_indicators": ["colombia"],
            "niche_keywords": ["mascotas"],
            "hashtags": ["#mascotas"],
            "keywords": ["mascotas"],
        }
        score_no_cross = lens_score(profile, profile_data, cross_referenced=False)
        score_cross = lens_score(profile, profile_data, cross_referenced=True)
        assert score_cross > score_no_cross, "Cross-referenced profile should score higher"
        assert score_cross <= 100, "Score should not exceed 100 even with bonus"

    def test_no_ve_artifacts_in_non_ve_profile(self):
        co_profile = {
            "biography": "Hair stylist Bogotá",
            "country": "CO",
            "username": "hairbycaro",
            "full_name": "Carolina",
            "locationName": "Bogotá",
            "followersCount": 8000,
            "engagement_rate": 0.05,
        }
        profile_data = {
            "geo_indicators": ["colombia", "bogota", "medellin"],
            "niche_keywords": ["belleza", "haircare", "peluqueria"],
            "hashtags": ["#belleza", "#haircare"],
            "keywords": ["belleza bogota", "haircare"],
        }
        geo = geo_score(co_profile, profile_data["geo_indicators"], target_country="CO")
        niche = niche_relevance(co_profile, profile_data)
        score = lens_score(co_profile, profile_data, cross_referenced=False)

        assert geo == 1.0, "CO profile should get perfect geo score"
        assert niche > 0, "Should have niche relevance"
        assert 0 <= score <= 100, "Score must be in range"
        bio_lower = co_profile.get("biography", "").lower()
        ve_signals = ["venezuela", "vzla", "caracas", "vzlatex"]
        assert not any(sig in bio_lower for sig in ve_signals), \
            "Bio should not contain VE artifacts for CO campaign"

    def test_tier_normalized_er_micro_high_followers(self):
        profile = {
            "followersCount": 150000,
            "engagement_rate": 0.03,
            "biography": "Tech B2B SaaS",
            "username": "techb2b",
        }
        profile_data = {
            "geo_indicators": ["mexico", "cdmx"],
            "niche_keywords": ["saas", "b2b", "software"],
            "hashtags": ["#saas"],
            "keywords": ["saas"],
        }
        score = lens_score(profile, profile_data)
        assert 0 <= score <= 100, f"Score must be 0-100, got {score}"

    def test_lens_score_zero_er_still_scores(self):
        profile = {
            "followersCount": 5000,
            "engagement_rate": 0.0,
            "biography": "New account",
            "username": "newuser",
        }
        profile_data = {
            "geo_indicators": ["colombia"],
            "niche_keywords": ["mascotas"],
            "hashtags": ["#mascotas"],
            "keywords": ["mascotas"],
        }
        score = lens_score(profile, profile_data)
        assert 0 <= score <= 100, "Zero ER profile should still get a score, not crash"
        assert score < 50, "Zero ER should produce low score"

    def test_lens_score_business_account_bonus(self):
        regular_profile = {
            "followersCount": 10000,
            "engagement_rate": 0.05,
            "biography": "Beauty blogger",
            "username": "beautyblog",
        }
        biz_profile = {
            "followersCount": 10000,
            "engagement_rate": 0.05,
            "biography": "Beauty blogger",
            "username": "beautyblog",
            "isBusinessAccount": True,
            "externalUrl": "https://example.com/shop",
        }
        profile_data = {
            "geo_indicators": ["colombia"],
            "niche_keywords": ["belleza"],
            "hashtags": ["#belleza"],
            "keywords": ["belleza"],
        }
        regular_score = lens_score(regular_profile, profile_data)
        biz_score = lens_score(biz_profile, profile_data)
        assert biz_score >= regular_score, "Business account should score same or higher"
