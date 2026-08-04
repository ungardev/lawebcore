"""QueryBuilder — transforms BriefStructured into DiscoveryPlan using DiscoveryProfile."""

from typing import Any

from discovery.schemas import BriefStructured, DiscoveryPlan
from discovery.profile_generator import get_or_create_profile


TIER_MIN_FOLLOWERS = {
    "nano": 500,
    "micro": 5_000,
    "micro_high": 20_000,
    "mid": 100_000,
}


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
        hashtag_queries = self._build_hashtag_queries(profile)

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
        queries.extend(profile.get("niche_keywords", []))

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

    def _build_hashtag_queries(self, profile: dict[str, Any]) -> list[str]:
        raw = profile.get("hashtags", [])
        hashtags = [f"#{tag.lstrip('#').strip()}" for tag in raw if tag and tag.strip()]
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
