"""Tests FIX fuga de brief (04-sep-2026).

`DiscoverySearchRequest` (frontera de entrada, extra='forbid') NO tenía
additional_context, competitor_brands ni influencer_preferences — la
construcción del run (discovery.py) solo copia campos que existen en ese
schema, así que el contexto del wizard ("Solo creadoras, NO tiendas...") y
las preferencias de tiers de los briefs PDF se evaporaban al crear el run:
el worker jamás los veía.
"""

from discovery.schemas import BriefStructured, DiscoverySearchRequest

_FULL_BRIEF = {
    "product_name": "Purina Dog Chow",
    "industry": "mascotas",
    "niches": ["veterinaria", "adiestramiento canino"],
    "hashtags": ["mascotasvzla"],
    "audience_gender": "all",
    "audience_countries": ["VE"],
    "audience_cities": ["Caracas"],
    "platforms": ["instagram"],
    "additional_context": "Solo creadoras individuales, NO tiendas.",
    "competitor_brands": ["Royal Canin"],
    "influencer_preferences": {"tiers": ["NANO", "MICRO"], "min_er": 0.04},
    "campaign_objective": "awareness",
    "campaign_name": "Lanzamiento VE",
    "budget_usd": 5000.0,
    "budget_currency": "USD",
    "kpis": ["reach", "engagement_rate"],
    "campaign_dates": {"start": "2026-09-10", "end": "2026-10-10"},
    "key_themes": ["adopcion", "cachorros"],
    "brief_source": "manual",
}


def test_discovery_request_accepts_brief_context_fields():
    req = DiscoverySearchRequest(**_FULL_BRIEF)
    assert req.additional_context == "Solo creadoras individuales, NO tiendas."
    assert req.competitor_brands == ["Royal Canin"]
    assert req.influencer_preferences == {"tiers": ["NANO", "MICRO"], "min_er": 0.04}
    assert req.budget_usd == 5000.0
    assert req.kpis == ["reach", "engagement_rate"]
    assert req.key_themes == ["adopcion", "cachorros"]


def test_run_roundtrip_preserves_previously_lost_fields():
    """Simula el viaje completo wizard→run→worker:

    BriefStructured → DiscoverySearchRequest (discovery.py) →
    brief_parsed en DB → BriefStructured (worker.py).
    """
    brief = BriefStructured(**_FULL_BRIEF)
    request = DiscoverySearchRequest(
        product_name=brief.product_name,
        industry=brief.industry,
        niches=brief.niches,
        hashtags=brief.hashtags,
        audience_gender=brief.audience_gender,
        audience_age_min=brief.audience_age_min,
        audience_age_max=brief.audience_age_max,
        audience_countries=brief.audience_countries,
        audience_cities=brief.audience_cities,
        audience_states=brief.audience_states,
        tone=brief.tone,
        platforms=brief.platforms,
        exclude_handles=brief.exclude_handles,
        discovery_mode="auto",
        handles_to_analyze=[],
        additional_context=brief.additional_context,
        competitor_brands=brief.competitor_brands,
        influencer_preferences=brief.influencer_preferences,
        campaign_objective=brief.campaign_objective,
        campaign_name=brief.campaign_name,
        budget_usd=brief.budget_usd,
        budget_currency=brief.budget_currency,
        kpis=brief.kpis,
        campaign_dates=brief.campaign_dates,
        key_themes=brief.key_themes,
        brief_source=brief.brief_source,
        source_document=brief.source_document,
    )
    worker_brief = BriefStructured(**request.model_dump())

    assert worker_brief.additional_context == "Solo creadoras individuales, NO tiendas."
    assert worker_brief.competitor_brands == ["Royal Canin"]
    assert worker_brief.influencer_preferences == {"tiers": ["NANO", "MICRO"], "min_er": 0.04}
    assert worker_brief.budget_usd == 5000.0
    assert worker_brief.campaign_objective == "awareness"
    assert worker_brief.key_themes == ["adopcion", "cachorros"]


def test_minimal_request_still_valid():
    """Backward compat: un request sin los campos nuevos sigue construyendo."""
    req = DiscoverySearchRequest(industry="mascotas")
    assert req.additional_context == ""
    assert req.competitor_brands == []
    assert req.influencer_preferences is None
