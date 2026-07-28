"""Geographic & tier filtering for Venezuela-priority discovery.

Replicates the geo-boost logic from extract_purina_real_apify.py v4.
Used to rank and filter Instagram profiles for VE campaigns.
"""

VE_KEYWORDS = (
    "venezuela", "vzla", "caracas", "maracaibo", "valencia",
    "san cristobal", "maturin", "barquisimeto", "puerto la cruz",
    "maracay", "merida", "ciudad guayana", "ciudad bolivar",
    "vzlatex", "venezolano", "venezolana",
)

LATAM_KEYWORDS = (
    "colombia", "medellin", "bogota", "panama", "ecuador",
    "latinoamerica", "latam", "peru", "chile", "argentina",
    "costarica", "guatemala", "mexico", "mx",
)


def country_boost(profile: dict) -> float:
    """Returns 1.0 for VE, 0.5 for Latam, 0.0 for rest.

    Checks ALL text fields from every Apify actor variant:
    - instagram-search-scraper: username, fullName, biography, profilePicUrl
    - instagram-hashtag-scraper: ownerUsername, ownerFullName, caption, locationName
    - instagram-profile-scraper: username, fullName, biography, country, about (dict)
    - instagram-scraper: various combinations of the above

    Pure function — no side effects.
    """
    sources: list[str] = []

    for field in [
        "biography",
        "bio",
        "caption",
        "about",
        "locationName",
        "location",
        "fullName",
        "full_name",
        "username",
        "handle",
        "ownerUsername",
        "ownerFullName",
        "ownerFullname",
    ]:
        val = profile.get(field)
        if val is None:
            continue
        if isinstance(val, str):
            sources.append(val.lower())
        elif isinstance(val, dict):
            for dict_val in val.values():
                if isinstance(dict_val, str):
                    sources.append(dict_val.lower())

    about = profile.get("about")
    if isinstance(about, dict):
        for val in about.values():
            if isinstance(val, str):
                sources.append(val.lower())

    haystack = " ".join(sources)

    if any(k in haystack for k in VE_KEYWORDS):
        return 1.0
    country_field = (profile.get("country") or "").lower()
    if country_field in ("ve", "venezuela"):
        return 1.0
    if any(k in haystack for k in LATAM_KEYWORDS):
        return 0.5
    return 0.0


def classify_tier(followers: int) -> str:
    """Returns tier label based on follower count."""
    if followers < 10_000:
        return "NANO"
    if followers < 100_000:
        return "MICRO"
    if followers < 500_000:
        return "MID"
    return "MACRO"


def composite_score(profile: dict) -> float:
    """v4 formula: engagement*100 + geo*30 + business*20 + verified*10.

    Used as the primary ranking metric for candidate selection.
    """
    followers = profile.get("followersCount") or profile.get("follower_count") or 0
    er = profile.get("engagement_rate") or 0.0
    geo = country_boost(profile)
    is_business = profile.get("isBusinessAccount") or profile.get("is_business") or False
    is_verified = profile.get("verified") or profile.get("is_verified") or False
    return (er * 100) + (geo * 30) + (20 if is_business else 0) + (10 if is_verified else 0)


def is_venezuelan(profile: dict) -> bool:
    """Hard filter: ONLY Venezuela (geo_boost == 1.0).

    Used as the mandatory post-enrichment gate before inserting a candidate.
    """
    return country_boost(profile) >= 1.0


def build_rationale(profile: dict, tier: str, followers: int, er: float) -> str:
    """Build a human-readable rationale string for a candidate profile.

    Mirrors _build_rationale from extract_purina_real_apify.py v4.
    """
    niches = []
    bio = (profile.get("biography") or profile.get("bio") or "").lower()

    if any(k in bio for k in ["perro", "dog", "mascota", "pet", "cachorro", "canino"]):
        niches.append("mascotas")
    if any(k in bio for k in ["adopta", "rescate", "coach", "adopcion", "refugio", "animal"]):
        niches.append("activismo animal")
    if any(k in bio for k in ["caracas", "maracaibo", "valencia", "vzla", "venezuela", "vzlatex"]):
        niches.append("VE local")
    if not niches:
        niches.append("general")
    return (
        f"Perfil {tier} de {', '.join(niches[:2])} en VE. "
        f"ER {er:.1f}%, {followers:,} seguidores. "
        f"Perfil relevante para campaña en Venezuela."
    )
