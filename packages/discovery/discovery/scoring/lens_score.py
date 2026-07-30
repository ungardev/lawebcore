"""Unified Lens Score — single scoring formula for all verticals.

Replaces:
  - composite_score() from geo_boost.py
  - calculate_lwfa_composite() from result_ranker.py (dead)
  - ResultRanker.rank() from result_ranker.py (dead)

Score: 0-100 with tier-normalized ER, niche relevance, geo score,
business intent, and cross-reference bonus.
"""

from typing import Any

from discovery.result_ranker import TIER_BENCHMARKS, calculate_business_intent


def lens_score(
    profile: dict[str, Any],
    profile_data: dict[str, Any],
    *,
    cross_referenced: bool = False,
) -> float:
    """Compute unified Lens score (0-100) for a discovery candidate.

    Components:
      - tier_normalized_er (35%): ER relative to tier benchmark
      - niche_relevance (20%): keyword + hashtag overlap with campaign niche
      - geo_score (25%): geographic relevance to target country/cities
      - business_intent (10%): external URL, business account, verified
      - cross_ref_bonus (10%): found in both STEP1 and STEP2
    """
    from discovery.scoring.niche import niche_relevance
    from discovery.tools.geo_boost import geo_score

    followers = profile.get("followersCount") or profile.get("follower_count") or 0
    er = profile.get("engagement_rate") or 0.0

    tier_key = _find_tier(followers)
    tier_er_norm = _tier_normalized_er(er, tier_key)

    geo_indicators = profile_data.get("geo_indicators", [])
    geo = geo_score(profile, geo_indicators) if geo_indicators else 0.5

    niche = niche_relevance(profile, profile_data)

    biz = calculate_business_intent(profile)

    raw = (
        0.35 * tier_er_norm
        + 0.25 * geo
        + 0.20 * niche
        + 0.10 * biz
    )

    if cross_referenced:
        raw *= 1.15

    return round(min(raw * 100, 100.0), 1)


def _find_tier(followers: int) -> str | None:
    for tier, bench in TIER_BENCHMARKS.items():
        if bench["followers_min"] <= followers < bench["followers_max"]:
            return tier
    return None


def _tier_normalized_er(er: float, tier_key: str | None) -> float:
    if tier_key and tier_key in TIER_BENCHMARKS:
        bench = TIER_BENCHMARKS[tier_key]
        er_min = bench.get("er_min", 0.02)
        er_max = bench.get("er_max", 0.05)
        if er_max > er_min:
            normalized = (er - er_min) / (er_max - er_min)
            return max(0.0, min(normalized, 1.0))
    if er > 0.02:
        return 1.0
    if er > 0.005:
        return 0.5
    return 0.0
