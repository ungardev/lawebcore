"""QueryBuilder — transforms BriefStructured into DiscoveryPlan for Apify pipeline."""

from typing import Any

from discovery.schemas import BriefStructured, DiscoveryPlan, Platform


DEFAULT_VE_HASHTAGS = [
    "purinaVE", "dogchowVE", "amorporruno", "mascotasVE", "perrosVE",
    "mascotasVenezuela", "dogChow", "purina", "petlovers", "doglover",
    "vzla", "venezuela", "adopcionvzla", "rescateanimalvzla",
    "mascotasvzla", "perrosdevzla",
]

DEFAULT_VE_KEYWORDS = [
    "PurinaVE", "DogChowVE", "purina dog chow venezuela",
    "mascotasVE", "perrosVenezuela", "amantesdelosperros",
    "mascotas caracas", "perrosvzla",
]

DISCOVERY_KEYWORDS = {
    "brand_competition": [
        "DogChow",
        "Purina",
        "PurinaDogChow",
        "Pedigree Venezuela",
        "Ganador premium perros",
        "Dogui alimento perros",
        "RoyalCanin Venezuela",
        "ProPlan Venezuela",
    ],
    "lifecycle_health": [
        "cachorros",
        "cachorro perros",
        "nutricion canina",
        "veterinaria venezuela",
        "perro senior",
        "salud canina",
        "veterinario perros",
        "pelaje perro sano",
        "digestion perros",
        "alimento premium perros",
    ],
    "consumer_personas": [
        "dog mom",
        "dog dad",
        "amor perruno",
        "adopcion perros venezuela",
        "rescate animal venezuela",
        "adopta no compres",
        "vida con perros",
        "paseo canino",
        "perrosdevzla",
        "mascotasvzla",
    ],
    "market_trends": [
        "comida barf perros",
        "alimento natural perros",
        "sin grano perros",
        "grain free dogs",
        "dieta cruda perros",
        "alimento casero perros",
    ],
    "nicho_ve": [
        "mascotasvzla",
        "perrosdevzla",
        "vzla",
        "caracas",
        "maracaibo",
        "valencia venezuela",
        "perros caracas",
        "mascotas caracas",
    ],
}

VE_GEO_KEYWORDS = ["venezuela", "vzla", "caracas", "maracaibo", "valencia", "san cristobal"]


_MASCOTA_TRIGGERS = [
    "purina", "dog chow", "dogchow", "mascota", "mascotas",
    "perro", "perros", "dog", "dogs", "pet", "pets",
    "cachorro", "cachorros", "canino", "canina",
]


class QueryBuilder:
    def build(self, brief: BriefStructured) -> DiscoveryPlan:
        keywords = self._build_keywords(brief)
        hashtags = self._build_hashtags(brief)
        tier = self._get_tier(brief)
        min_followers = self._tier_to_min_followers(tier)

        return DiscoveryPlan(
            keyword_queries=keywords,
            hashtag_queries=hashtags,
            enrichment_batch_size=10,
            analytics_top_n=20,
            min_followers=min_followers,
            max_followers=10_000_000,
        )

    def _is_vertical_mascota(self, brief: BriefStructured) -> bool:
        """Detecta si el brief es de la vertical mascotas/perros."""
        product = (brief.product_name or "").lower()
        additional = (brief.additional_context or "").lower()
        niches_text = " ".join(brief.niches or []).lower()
        combined = f"{product} {additional} {niches_text}"
        return any(trigger in combined for trigger in _MASCOTA_TRIGGERS)

    def _build_keywords(self, brief: BriefStructured) -> list[str]:
        if self._is_vertical_mascota(brief):
            return DEFAULT_VE_KEYWORDS

        keywords: list[str] = []
        for niche in brief.niches:
            keywords.append(niche)
            for country in (brief.audience_countries or []):
                if country == "VE":
                    keywords.extend(VE_GEO_KEYWORDS)
        return list(set(keywords))[:40]

    def _build_hashtags(self, brief: BriefStructured) -> list[str]:
        if brief.hashtags:
            return [f"#{tag.lstrip('#')}" for tag in brief.hashtags]
        if self._is_vertical_mascota(brief):
            return [f"#{tag}" for tag in DEFAULT_VE_HASHTAGS]

        return [f"#{n.lower().replace(' ', '')}" for n in brief.niches[:15]]

    def _get_tier(self, brief: BriefStructured) -> str:
        budget = brief.budget_usd or 0
        if budget >= 10000:
            return "mid"
        elif budget >= 5000:
            return "micro_high"
        elif budget >= 2000:
            return "micro"
        elif budget >= 500:
            return "nano"
        return "micro"

    def _tier_to_min_followers(self, tier: str) -> int:
        tier_map = {
            "nano": 500,
            "micro": 5_000,
            "micro_high": 20_000,
            "mid": 100_000,
        }
        return tier_map.get(tier, 1_000)


query_builder = QueryBuilder()
