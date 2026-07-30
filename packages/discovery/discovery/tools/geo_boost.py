"""Geographic & tier filtering for Venezuela-priority discovery.

Replicates the geo-boost logic from extract_purina_real_apify.py v4.
Used to rank and filter Instagram profiles for VE campaigns.
"""

VE_KEYWORDS = (
    "venezuela", "vzla", "caracas", "maracaibo", "valencia",
    "san cristobal", "maturin", "barquisimeto", "puerto la cruz",
    "maracay", "merida", "ciudad guayana", "ciudad bolivar",
    "vzlatex", "vzlan", "venezolano", "venezolana",
    "🇻🇪", "anzoategui", "zulia", "lara", "yaracuy",
    "carabobo", "aragua", "portuguesa", "trujillo", "cojedes",
    "monagas", "sucre", "nueva esparta", "guarico", "apure", "barinas", "falcon",
    "amazonas", "bolivariano", "vzlano",
    "anzoátegui", "guatire", "los teques", "baruta", "chacao", "el hatillo",
    "petare", "catia", "cabudare",
    "villa de cura",
)

LATAM_KEYWORDS = (
    "colombia", "medellin", "bogota", "panama", "ecuador",
    "latinoamerica", "latam", "peru", "chile", "argentina",
    "costarica", "guatemala", "mexico", "mx",
)


def country_boost(profile: dict) -> float:
    """Returns 1.0 for VE, 0.5 for Latam, 0.0 for rest.

    Matches _country_boost from extract_purina_real_apify.py v4.
    Checks: biography, country, username, full_name, locationName.
    """
    bio = (profile.get("biography") or profile.get("bio") or "").lower()
    country = (profile.get("country") or "").lower()
    username = (profile.get("username") or profile.get("handle") or "").lower()
    full_name = (profile.get("full_name") or profile.get("fullName") or "").lower()
    location = (profile.get("locationName") or profile.get("location") or "").lower()
    followers = profile.get("followersCount") or profile.get("follower_count") or 0
    is_business = profile.get("is_business") or profile.get("isBusinessAccount") or False
    er = profile.get("engagement_rate") or 0.0

    if any(k in bio + full_name + username + location for k in VE_KEYWORDS):
        return 1.0
    if country in ("ve", "venezuela"):
        return 1.0
    if any(k in bio + full_name + username + location for k in LATAM_KEYWORDS):
        return 0.5
    if is_business and followers > 5000 and er > 0.01:
        return 0.4
    if followers > 20000 and er > 0.02:
        return 0.3
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
    """v5 formula: engagement*200 + geo*50 + business*25 + verified*15.

    Used as the primary ranking metric for candidate selection.
    Higher weight on engagement and geo to prioritize real VE influencers.
    """
    followers = profile.get("followersCount") or profile.get("follower_count") or 0
    er = profile.get("engagement_rate") or 0.0
    geo = country_boost(profile)
    is_business = profile.get("isBusinessAccount") or profile.get("is_business") or False
    is_verified = profile.get("verified") or profile.get("is_verified") or False
    return (er * 200) + (geo * 50) + (25 if is_business else 0) + (15 if is_verified else 0)


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
        f"ER {er * 100:.1f}%, {followers:,} seguidores. "
        f"Perfil relevante para campaña en Venezuela."
    )
