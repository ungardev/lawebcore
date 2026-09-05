"""QueryBuilder — transforms BriefStructured into DiscoveryPlan using DiscoveryProfile."""

from typing import Any

from discovery.profile_generator import get_or_create_profile
from discovery.schemas import BriefStructured, DiscoveryPlan

TIER_MIN_FOLLOWERS = {
    "nano": 500,
    "micro": 5_000,
    "micro_high": 20_000,
    "mid": 100_000,
}


VE_NICHE_HASHTAGS: dict[str, list[str]] = {
    "mascotas": [
        "mascotasvzla", "mascotasvenezuela", "perrosvzla", "gatosvzla",
        "petloversvzla", "adoptavzla", "rescatedemascotasvzla", "veterinariavzla",
        "mascotascaracas", "mascotasmaracaibo", "mascotasvalencia",
        "perroscaracas", "gatoscaracas", "petloverscaracas",
        "adopcionmascotas", "rescateanimalvzla", "amigospeludos",
        "cachorrosvzla", "mascotasalatinoamericana",
    ],
    "belleza": [
        "bellezavzla", "makeupvzla", "skincarevzla", "beautyve",
        "bellezacaracas", "makeupcaracas", "haircaracas",
        "uñasvzla", "nailsvzla", "cosmeticavzla",
        "bellezalatina", "makeuplatino", "skincarelatino",
    ],
    "food": [
        "comidavzla", "foodve", "comidavenezolana", "arepavzla",
        "foodcaracas", "comidacaracas", "gastronomiavzla",
        "foodiesvzla", "foodpornvzla", "cocinavzla",
        "recetasvzla", "cocinalatina", "comidastipicasvzla",
    ],
    "fitness": [
        "fitnessvzla", "gymvzla", "gymcaracas", "fitnesscaracas",
        "gimnasiovzla", "entrenadorvzla", "fitve",
        "fitnesslatino", "gymlifestyle", "workoutvzla",
        "healthyvzla", "deportevzla", "atletismovzla",
    ],
    "moda": [
        "modavzla", "fashionve", "modacaracas", "fashioncaracas",
        "outfitvzla", "modalatina", "fashionvzla",
        "ropavzla", "estilovzla", "tendenciasvzla",
    ],
    "tecnologia": [
        "techvzla", "tecnologiavzla", "techcaracas", "gadgetsvzla",
        "innovacionvzla", "digitalvzla", "tecnologialatina",
    ],
    "turismo": [
        "turismovzla", "viajesvzla", "turismocaracas", "viajescaracas",
        "viajesvenezuela", "turismolatino", "exploravzla",
        "viajeslatinos", "destinosvzla", "aventuravzla",
    ],
    "entretenimiento": [
        "entretenimientovzla", "musicavzla", "cinevzla",
        "entretenimientolatino", "culturavzla", "artistasvzla",
    ],
    "educacion": [
        "educacionvzla", "cursosvzla", "aprendizajevzla",
        "educacionlatina", "universidadvzla", "educacioncaracas",
    ],
    "finanzas": [
        "finanzasvzla", "negociosvzla", "emprendedurismovzla",
        "negocioslatinos", "finanzaslatinas", "inversionvzla",
    ],
    "hogar": [
        "hogarvzla", "decoracionvzla", "interiorismovzla",
        "casavzla", "hogarcaracas", "decoracioncaracas",
    ],
    "deportes": [
        "deportesvzla", "futbolvzla", "beisbolvzla",
        "deportistasvzla", "ligavzla", "seleccionvzla",
    ],
}


def auto_hashtags_for_brief(brief: BriefStructured) -> list[str]:
    """Returns VE-specific hashtags auto-generated for the brief's industry.

    These hashtags are prepended to the hashtag list to boost VE-native
    creator discovery. Falls back to generic VE hashtags if industry unknown.
    """
    industry = (brief.industry or "default").lower().strip()
    return VE_NICHE_HASHTAGS.get(industry, [
        "vzla", "venezuela", "caracas", "vzlatex",
        "vzlan", "venezolano", "mascotasvzla",
    ])


class QueryBuilder:
    async def build(self, brief: BriefStructured) -> DiscoveryPlan:
        profile = await get_or_create_profile(brief)

        tier = self._get_tier(brief)
        min_followers = self._tier_to_min_followers(tier)
        if brief.influencer_preferences:
            tier_pref = brief.influencer_preferences.get("tier")
            if tier_pref and tier_pref in TIER_MIN_FOLLOWERS:
                min_followers = TIER_MIN_FOLLOWERS[tier_pref]
            explicit_min = brief.influencer_preferences.get("min_followers")
            if explicit_min and isinstance(explicit_min, int) and explicit_min > 0:
                min_followers = explicit_min

        keyword_queries = self._build_keyword_queries(profile, brief)
        hashtag_queries = self._build_hashtag_queries(profile, brief)

        return DiscoveryPlan(
            keyword_queries=keyword_queries,
            hashtag_queries=hashtag_queries,
            enrichment_batch_size=10,
            analytics_top_n=20,
            min_followers=min_followers,
            max_followers=10_000_000,
            exclude_handles=brief.exclude_handles or [],
            profile=profile,
        )

    def _build_keyword_queries(self, profile: dict[str, Any], brief: BriefStructured) -> list[str]:
        queries: list[str] = []

        queries.extend(profile.get("keywords", []))

        if brief.competitor_brands:
            queries.extend(brief.competitor_brands)

        for niche in brief.niches:
            if niche.lower() not in " ".join(queries).lower():
                queries.append(niche)

        seen = set()
        deduped = []
        for q in queries:
            q = q.strip()
            if q and q.lower() not in seen:
                seen.add(q.lower())
                deduped.append(q)

        return deduped[:20]

    def _build_hashtag_queries(self, profile: dict[str, Any], brief: BriefStructured) -> list[str]:
        seen = set()
        hashtags = []
        for tag in (brief.hashtags or []):
            cleaned = f"#{tag.lstrip('#').strip()}"
            if cleaned not in seen:
                seen.add(cleaned)
                hashtags.append(cleaned)
        for tag in profile.get("hashtags", []):
            cleaned = f"#{tag.lstrip('#').strip()}"
            if cleaned not in seen:
                seen.add(cleaned)
                hashtags.append(cleaned)
        for tag in auto_hashtags_for_brief(brief):
            cleaned = f"#{tag.lstrip('#').strip()}"
            if cleaned not in seen:
                seen.add(cleaned)
                hashtags.append(cleaned)
        return hashtags[:30]

    def _get_tier(self, brief: BriefStructured) -> str:
        if brief.influencer_preferences:
            tier = brief.influencer_preferences.get("tier")
            if tier in TIER_MIN_FOLLOWERS:
                return tier
        return "micro"

    def _tier_to_min_followers(self, tier: str) -> int:
        return TIER_MIN_FOLLOWERS.get(tier, 5_000)


query_builder = QueryBuilder()
