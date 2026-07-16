"""QueryBuilder — transforma BriefStructured en queries por plataforma."""

from typing import Any

from app.discovery.schemas import BriefStructured, Platform


class SearchQuery:
    """Query individual para una plataforma específica."""

    def __init__(
        self,
        platform: Platform,
        query_type: str,
        params: dict[str, Any],
    ):
        self.platform = platform
        self.query_type = query_type
        self.params = params

    def __repr__(self) -> str:
        return f"SearchQuery({self.platform.value}/{self.query_type}, {self.params})"


class QueryBuilder:
    """Construye queries específicas por plataforma a partir de un BriefStructured."""

    def build(self, brief: BriefStructured) -> dict[Platform, list[SearchQuery]]:
        """Build queries para todas las plataformas especificadas en el brief."""
        queries: dict[Platform, list[SearchQuery]] = {}

        for platform in brief.platforms:
            if platform == Platform.INSTAGRAM:
                queries[platform] = self._build_instagram_queries(brief)
            elif platform == Platform.TIKTOK:
                queries[platform] = self._build_tiktok_queries(brief)
            elif platform == Platform.YOUTUBE:
                queries[platform] = self._build_youtube_queries(brief)
            elif platform == Platform.X:
                queries[platform] = self._build_x_queries(brief)

        return queries

    def _build_instagram_queries(self, brief: BriefStructured) -> list[SearchQuery]:
        """Construye queries para Instagram."""
        queries = []

        hashtags = self._niches_to_hashtags(brief.niches, brief.audience_countries)
        for hashtag in hashtags[:10]:
            queries.append(
                SearchQuery(
                    platform=Platform.INSTAGRAM,
                    query_type="hashtag_search",
                    params={
                        "hashtag": hashtag,
                        "country": brief.audience_countries[0] if brief.audience_countries else "VE",
                        "min_followers": self._tier_to_min_followers(brief),
                        "max_followers": self._tier_to_max_followers(brief),
                        "city": brief.audience_cities[0] if brief.audience_cities else None,
                    },
                )
            )

        return queries

    def _build_tiktok_queries(self, brief: BriefStructured) -> list[SearchQuery]:
        """Construye queries para TikTok."""
        queries = []

        keywords = [n.replace(" ", "") for n in brief.niches] + [
            n.replace(" ", "") for n in (brief.additional_context or "").split()[:5]
        ]
        for keyword in keywords[:10]:
            queries.append(
                SearchQuery(
                    platform=Platform.TIKTOK,
                    query_type="keyword_search",
                    params={
                        "keyword": keyword,
                        "country": brief.audience_countries[0] if brief.audience_countries else "VE",
                        "min_followers": self._tier_to_min_followers(brief),
                    },
                )
            )

        hashtags = self._niches_to_hashtags(brief.niches, brief.audience_countries)
        for hashtag in hashtags[:5]:
            queries.append(
                SearchQuery(
                    platform=Platform.TIKTOK,
                    query_type="hashtag_search",
                    params={
                        "hashtag": hashtag,
                        "country": brief.audience_countries[0] if brief.audience_countries else "VE",
                    },
                )
            )

        return queries

    def _build_youtube_queries(self, brief: BriefStructured) -> list[SearchQuery]:
        """Construye queries para YouTube."""
        queries = []

        for niche in brief.niches[:5]:
            queries.append(
                SearchQuery(
                    platform=Platform.YOUTUBE,
                    query_type="channel_search",
                    params={
                        "query": niche,
                        "region": brief.audience_countries[0] if brief.audience_countries else "VE",
                        "relevance_language": "es",
                    },
                )
            )

        return queries

    def _build_x_queries(self, brief: BriefStructured) -> list[SearchQuery]:
        """Construye queries para X/Twitter."""
        queries = []

        for niche in brief.niches[:5]:
            queries.append(
                SearchQuery(
                    platform=Platform.X,
                    query_type="user_search",
                    params={
                        "query": niche,
                        "country": brief.audience_countries[0] if brief.audience_countries else "VE",
                    },
                )
            )

        return queries

    _COUNTRY_MAP = {
        "VE": "venezuela",
        "CO": "colombia",
        "MX": "mexico",
        "AR": "argentina",
        "CL": "chile",
        "PE": "peru",
        "EC": "ecuador",
        "BO": "bolivia",
        "PA": "panama",
        "DO": "dominicana",
        "CR": "costarica",
        "UY": "uruguay",
        "PY": "paraguay",
        "GT": "guatemala",
        "HN": "honduras",
        "SV": "salvador",
        "NI": "nicaragua",
    }

    def _niches_to_hashtags(self, niches: list[str], countries: list[str]) -> list[str]:
        """Convierte niches a hashtags de Instagram/TikTok."""
        hashtags = []
        for niche in niches:
            clean = niche.lower().replace(" ", "").replace("-", "")
            hashtags.append(f"#{clean}")
            for country in countries[:2]:
                country_name = self._COUNTRY_MAP.get(country.upper(), country.lower())
                hashtags.append(f"#{clean}{country_name}")
        return hashtags[:15]

    def _tier_to_min_followers(self, brief: BriefStructured) -> int:
        """Infiere follower mínimo basado en el presupuesto."""
        budget = brief.budget_usd or 0
        if budget >= 10000:
            return 100_000
        elif budget >= 5000:
            return 50_000
        elif budget >= 2000:
            return 10_000
        elif budget >= 500:
            return 1_000
        return 500

    def _tier_to_max_followers(self, brief: BriefStructured) -> int:
        """Infiere follower máximo basado en el presupuesto."""
        budget = brief.budget_usd or 0
        if budget <= 500:
            return 50_000
        elif budget <= 2000:
            return 500_000
        elif budget <= 5000:
            return 1_000_000
        return 10_000_000


query_builder = QueryBuilder()
