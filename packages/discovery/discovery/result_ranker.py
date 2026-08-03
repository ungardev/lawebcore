"""ResultRanker — universal scoring constants and helpers for discovery candidates."""

from discovery.schemas import Platform


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

IG_CONTENT_TYPES = ["clips", "reels", "carousel", "image", "video", "story"]


def calculate_engagement_velocity(
    total_likes: int,
    total_comments: int,
    posts_count: int,
    days_since_first_post: int = 30,
) -> float:
    """Engagement Velocity — interacciones promedio por post por día."""
    if posts_count == 0 or days_since_first_post == 0:
        return 0.0
    total_interactions = (total_likes or 0) + (total_comments or 0)
    return round(total_interactions / max(posts_count, 1) / max(days_since_first_post, 1), 4)


def calculate_business_intent(profile: dict) -> float:
    """Business Intent Score — 0-1 disposición comercial del perfil."""
    score = 0.0
    if profile.get("externalUrl"):
        score += 0.4
    about = profile.get("about") or {}
    if about.get("facebookPage"):
        score += 0.4
    if profile.get("isBusinessAccount") or profile.get("isBusiness"):
        score += 0.2
    if profile.get("isVerified"):
        score += 0.1
    return round(min(score, 1.0), 3)
