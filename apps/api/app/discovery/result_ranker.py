"""ResultRanker — scoring y matemáticas para candidatos de discovery."""

from app.discovery.schemas import (
    AudienceGender,
    BriefStructured,
    CandidateMetrics,
    MatchScoreResult,
    Platform,
)


TIER_BENCHMARKS = {
    "NANO_BAJO": {"followers_min": 500, "followers_max": 2_000, "er_min": 0.08, "er_max": 0.15},
    "NANO_ALTO": {"followers_min": 2_000, "followers_max": 10_000, "er_min": 0.06, "er_max": 0.12},
    "MICRO_BAJO": {"followers_min": 10_000, "followers_max": 30_000, "er_min": 0.04, "er_max": 0.10},
    "MICRO_MEDIO": {"followers_min": 30_000, "followers_max": 100_000, "er_min": 0.03, "er_max": 0.08},
    "MICRO_ALTO": {"followers_min": 100_000, "followers_max": 500_000, "er_min": 0.02, "er_max": 0.06},
    "MID_BAJO": {"followers_min": 500_000, "followers_max": 1_000_000, "er_min": 0.015, "er_max": 0.05},
    "MID_ALTO": {"followers_min": 1_000_000, "followers_max": 5_000_000, "er_min": 0.01, "er_max": 0.04},
    "MACRO_BAJO": {"followers_min": 5_000_000, "followers_max": 10_000_000, "er_min": 0.005, "er_max": 0.02},
    "MACRO_ALTO": {"followers_min": 10_000_000, "followers_max": 100_000_000, "er_min": 0.003, "er_max": 0.01},
}

PLATFORM_ENGAGEMENT_WEIGHTS = {
    Platform.INSTAGRAM: {"likes": 1.0, "comments": 2.0, "saves": 1.5},
    Platform.TIKTOK: {"likes": 0.5, "comments": 1.5, "views": 0.001},
    Platform.YOUTUBE: {"likes": 1.0, "comments": 3.0, "views": 0.0001},
    Platform.X: {"likes": 1.0, "comments": 2.0, "retweets": 2.5},
}

NICHE_KEYWORDS = {
    "moda": ["moda", "outfit", "style", "fashion", "vestuario", "look", "tendencias"],
    "belleza": ["belleza", "makeup", "skincare", "cosmetica", "beauty", "routine"],
    "fitness": ["fitness", "gym", "ejercicio", "trabajo", "muscle", "workout", "salud"],
    "tecnologia": ["tecnologia", "tech", "gadget", "celular", "innovacion", "digital"],
    "comida": ["comida", "recetas", "cocina", "food", "gastronomia", "chef", "eating"],
    "viajes": ["viajes", "travel", "turismo", "vacaciones", "destino", "viajar"],
    "lifestyle": ["lifestyle", "vida", "dia", "routine", "habitos", "cotidiano"],
    "mama": ["mama", "mamá", "maternity", "bebe", "niños", "familia", "hijos"],
    "negocios": ["negocios", "business", "emprendimiento", "startup", "empresa", "finanzas"],
    "entretenimiento": ["entretenimiento", "musica", "peliculas", "series", "cultura", "pop"],
    "cafe": ["cafe", "café", "coffee", "barista", "desayuno", "mañana"],
    "deportes": ["deportes", "sports", "futbol", "beisbol", "atletismo", "entrenamiento"],
    "arte": ["arte", "art", "pintura", "diseno", "creatividad", "ilustracion"],
    "gaming": ["gaming", "videojuegos", "games", "playstation", "xbox", "twitch"],
}


class ResultRanker:
    """Puntúa candidatos con un match_score de 0-100."""

    def rank(
        self,
        candidate: CandidateMetrics,
        brief: BriefStructured,
        brand_historical_er: float | None = None,
    ) -> MatchScoreResult:
        """Calcula el match_score para un candidato."""
        niche_score = self._niche_relevance(candidate, brief)
        geo_score = self._geo_relevance(candidate, brief)
        audience_score = self._audience_relevance(candidate, brief)
        quality_score = self._content_quality(candidate)

        match_score = (
            niche_score * 0.30
            + geo_score * 0.25
            + audience_score * 0.25
            + quality_score * 0.20
        )

        estimated_cost = self._estimate_cost(candidate)
        expected_reach = self._expected_reach(candidate)
        expected_engagement = self._expected_engagement(candidate, expected_reach)
        roi_estimate = self._roi_estimate(
            expected_engagement, brand_historical_er, estimated_cost
        )

        return MatchScoreResult(
            match_score=round(match_score, 2),
            niche_relevance=round(niche_score * 100, 1),
            geo_relevance=round(geo_score * 100, 1),
            audience_relevance=round(audience_score * 100, 1),
            content_quality=round(quality_score * 100, 1),
            estimated_cost=estimated_cost,
            expected_reach=expected_reach,
            expected_engagement=round(expected_engagement, 2),
            roi_estimate=round(roi_estimate, 2) if roi_estimate else None,
            rationale=self._generate_rationale(candidate, brief, match_score),
        )

    def _niche_relevance(self, candidate: CandidateMetrics, brief: BriefStructured) -> float:
        """Calcula qué tan relevante es el nicho del candidato para el brief."""
        if not candidate.audience_interests and not candidate.bio:
            return 0.5

        interest_text = " ".join(candidate.audience_interests or []).lower()
        bio_text = (candidate.bio or "").lower()

        candidate_text = f"{interest_text} {bio_text}"

        niche_matches = 0
        for niche in brief.niches:
            niche_lower = niche.lower()
            niche_keywords = NICHE_KEYWORDS.get(niche_lower, [niche_lower])
            for keyword in niche_keywords:
                if keyword in candidate_text:
                    niche_matches += 1
                    break

        if not brief.niches:
            return 0.5

        return min(niche_matches / len(brief.niches), 1.0)

    def _geo_relevance(self, candidate: CandidateMetrics, brief: BriefStructured) -> float:
        """Calcula relevancia geográfica."""
        if not brief.audience_countries:
            return 1.0

        candidate_country = (candidate.country or "").upper()
        if candidate_country in [c.upper() for c in brief.audience_countries]:
            country_score = 1.0
        else:
            country_score = 0.2

        if not brief.audience_cities:
            return country_score

        candidate_city = (candidate.city or "").lower()
        city_matches = sum(
            1 for city in brief.audience_cities if city.lower() in candidate_city
        )
        city_score = city_matches / len(brief.audience_cities) if brief.audience_cities else 0

        return country_score * 0.6 + city_score * 0.4

    def _audience_relevance(
        self, candidate: CandidateMetrics, brief: BriefStructured
    ) -> float:
        """Calcula relevancia de la audiencia."""
        score = 0.0
        factors = 0

        gender_score = self._gender_match(candidate, brief)
        score += gender_score
        factors += 1

        age_score = self._age_match(candidate, brief)
        score += age_score
        factors += 1

        if candidate.audience_gender_split:
            audience_diversity = min(
                max(
                    candidate.audience_gender_split.get("female", 0.5),
                    candidate.audience_gender_split.get("male", 0.5),
                ),
                0.7,
            )
            score += audience_diversity
            factors += 1

        return score / factors if factors > 0 else 0.5

    def _gender_match(self, candidate: CandidateMetrics, brief: BriefStructured) -> float:
        """Evalúa match de género."""
        if brief.audience_gender == AudienceGender.ALL:
            return 1.0

        if not candidate.audience_gender_split:
            return 0.5

        if brief.audience_gender == AudienceGender.FEMALE:
            return candidate.audience_gender_split.get("female", 0.5)
        elif brief.audience_gender == AudienceGender.MALE:
            return candidate.audience_gender_split.get("male", 0.5)
        return 0.5

    def _age_match(self, candidate: CandidateMetrics, brief: BriefStructured) -> float:
        """Evalúa match de rango etario."""
        if not candidate.audience_age_buckets:
            return 0.5

        buckets = candidate.audience_age_buckets
        target_min = brief.audience_age_min
        target_max = brief.audience_age_max

        relevant_share = 0.0
        for bucket_label, share in buckets.items():
            bucket_min, bucket_max = self._parse_age_bucket(bucket_label)
            overlap = min(target_max, bucket_max) - max(target_min, bucket_min)
            if overlap > 0:
                relevant_share += share * (overlap / (bucket_max - bucket_min + 1))

        return min(relevant_share, 1.0)

    def _parse_age_bucket(self, label: str) -> tuple[int, int]:
        """Parsea un bucket etario (ej. '18-24' → (18, 24))."""
        if "-" in label:
            parts = label.split("-")
            return int(parts[0]), int(parts[1])
        if "+" in label:
            base = int(label.replace("+", ""))
            return base, 65
        return 18, 65

    def _content_quality(self, candidate: CandidateMetrics) -> float:
        """Evalúa calidad de contenido del candidato."""
        if not candidate.engagement_rate and not candidate.audience_quality:
            return 0.5

        er_score = 0.0
        if candidate.engagement_rate:
            tier = self._get_tier(candidate.followers or 0)
            if tier:
                bench = TIER_BENCHMARKS.get(tier, {})
                er_min = bench.get("er_min", 0.02)
                er_max = bench.get("er_max", 0.05)
                er = candidate.engagement_rate
                er_score = min(max((er - er_min) / (er_max - er_min + 0.001), 0), 1)

        quality_score = (candidate.audience_quality or 50) / 100

        return er_score * 0.6 + quality_score * 0.4

    def _get_tier(self, followers: int) -> str | None:
        """Infiere el tier basado en followers."""
        for tier, bench in TIER_BENCHMARKS.items():
            if bench["followers_min"] <= followers < bench["followers_max"]:
                return tier
        return None

    def _estimate_cost(self, candidate: CandidateMetrics) -> float:
        """Estima el costo por post del candidato en USD."""
        followers = candidate.followers or 0
        tier = self._get_tier(followers)

        base_rates = {
            "NANO_BAJO": 50,
            "NANO_ALTO": 150,
            "MICRO_BAJO": 300,
            "MICRO_MEDIO": 500,
            "MICRO_ALTO": 1000,
            "MID_BAJO": 2000,
            "MID_ALTO": 4000,
            "MACRO_BAJO": 8000,
            "MACRO_ALTO": 15000,
        }

        base = base_rates.get(tier, 200)

        if candidate.engagement_rate and candidate.engagement_rate > 0.08:
            base *= 1.3
        elif candidate.engagement_rate and candidate.engagement_rate < 0.02:
            base *= 0.7

        return round(base, 2)

    def _expected_reach(self, candidate: CandidateMetrics) -> int:
        """Estima reach proyectado (followers × factor de penetración)."""
        followers = candidate.followers or 0
        platform_factor = {
            Platform.INSTAGRAM: 0.70,
            Platform.TIKTOK: 0.85,
            Platform.YOUTUBE: 0.40,
            Platform.X: 0.30,
        }.get(candidate.platform, 0.50)

        return int(followers * platform_factor)

    def _expected_engagement(
        self, candidate: CandidateMetrics, expected_reach: int
    ) -> float:
        """Estima engagement proyectado (reach × ER)."""
        er = candidate.engagement_rate or 0.03
        return expected_reach * er

    def _roi_estimate(
        self,
        expected_engagement: float,
        brand_er: float | None,
        estimated_cost: float,
    ) -> float | None:
        """Estima ROI: (engagement_value × engagement) / cost."""
        if not estimated_cost or estimated_cost == 0:
            return None

        engagement_value = brand_er or 0.05
        return (expected_engagement * engagement_value) / estimated_cost

    def _generate_rationale(
        self, candidate: CandidateMetrics, brief: BriefStructured, score: float
    ) -> str:
        """Genera una justificación textual del match score."""
        parts = []

        if candidate.engagement_rate:
            parts.append(f"ER {candidate.engagement_rate:.2%}")

        if candidate.followers:
            parts.append(f"{candidate.followers:,} followers")

        if candidate.country:
            parts.append(f"ubicado en {candidate.country}")

        if candidate.bio:
            parts.append(f"bio relevante: '{candidate.bio[:60]}...'")

        return f"Match score {score:.0f}/100 para {candidate.handle}: {', '.join(parts)}"


result_ranker = ResultRanker()
