"""Geographic & tier scoring for universal discovery.

All geo scoring is parameterized — pass geo_indicators from DiscoveryProfile
instead of hardcoding country-specific constants.
"""

import re

_COUNTRY_NAMES = {
    "VE": "Venezuela",
    "CO": "Colombia",
    "MX": "México",
    "AR": "Argentina",
    "CL": "Chile",
    "PA": "Panamá",
    "PE": "Perú",
    "EC": "Ecuador",
    "BR": "Brasil",
    "DO": "República Dominicana",
    "US": "Estados Unidos",
}

_LATAM_KEYWORDS = (
    "latinoamerica", "latam", "latino",
)

_ISO2_PATTERNS = {
    "VE": re.compile(r"\bve\b", re.IGNORECASE),
    "CO": re.compile(r"\bco\b", re.IGNORECASE),
    "MX": re.compile(r"\bmx\b", re.IGNORECASE),
    "AR": re.compile(r"\bar\b", re.IGNORECASE),
    "CL": re.compile(r"\bcl\b", re.IGNORECASE),
    "PA": re.compile(r"\bpa\b", re.IGNORECASE),
    "PE": re.compile(r"\bpe\b", re.IGNORECASE),
    "EC": re.compile(r"\bec\b", re.IGNORECASE),
    "BR": re.compile(r"\bbr\b", re.IGNORECASE),
    "DO": re.compile(r"\brd\b", re.IGNORECASE),
    "US": re.compile(r"\bus\b", re.IGNORECASE),
}


def geo_score(profile: dict, geo_indicators: list[str]) -> float:
    """Universal geographic relevance score (0.0 – 1.0).

    Tier 1.0: Ciudad específica o país (ISO) encontrado en geo_indicators
              + PRIMARY: country field matches target country
    Tier 0.85: Keyword de país (gentilicios, variantes) encontrado
    Tier 0.5:  Keyword LATAM genérico
    Tier 0.4:  Business account con engagement
    Tier 0.3:  High followers con engagement

    Word boundary matching prevents false positives like:
    - Mexican bio mentioning "Caracas" → won't match
    - Colombian username "vzla_fan" → won't match
    - Profile with country field explicit check first
    """
    bio = (profile.get("biography") or profile.get("bio") or "").lower()
    country = (profile.get("country") or "").strip().upper()
    username = (profile.get("username") or profile.get("handle") or "").lower()
    full_name = (profile.get("full_name") or profile.get("fullName") or "").lower()
    location = (profile.get("locationName") or profile.get("location") or "").lower()

    search_text = f"{bio} {full_name} {username} {location}"

    target_iso2 = None
    for iso2 in _ISO2_PATTERNS:
        if any(iso2.lower() == c.lower() for c in geo_indicators if len(c) == 2):
            target_iso2 = iso2
            break

    if target_iso2 and country == target_iso2:
        return 1.0

    if target_iso2 and country and country != target_iso2:
        return 0.0

    def _word_match(text: str, keywords: list[str]) -> int:
        count = 0
        for kw in keywords:
            pattern = re.compile(r"\b" + re.escape(kw.lower()) + r"\b", re.IGNORECASE)
            if pattern.search(text):
                count += 1
        return count

    city_keywords = [k for k in geo_indicators if len(k) > 3]
    city_matches = _word_match(search_text, city_keywords)

    country_keywords = _get_country_keywords(geo_indicators)
    country_kw_matches = _word_match(search_text, country_keywords)

    if city_matches >= 1:
        return 1.0

    if country_kw_matches >= 1:
        return 0.85

    if any(k.lower() in search_text for k in _LATAM_KEYWORDS):
        return 0.5

    return 0.0


def _get_country_keywords(geo_indicators: list[str]) -> list[str]:
    """Extrae keywords de país (gentilicios, variantes) de geo_indicators.

    These give a 0.85 score — confirms country without city specificity.
    """
    country_signal_keywords = {
        "ve": ["venezuela", "vzla", "vzlatex", "vzlan", "vzlano", "venezolano", "venezolana", "🇻🇪"],
        "co": ["colombia", "colombiano", "colombiana", "co", "🇨🇴"],
        "mx": ["mexico", "mexicano", "mexicana", "mx", "🇲🇽"],
        "ar": ["argentina", "argentino", "argentina", "ar", "🇦🇷"],
        "cl": ["chile", "chileno", "chilena", "cl", "🇨🇱"],
        "pa": ["panama", "panameño", "panameña", "pa", "🇵🇦"],
        "pe": ["peru", "peruano", "peruana", "pe", "🇵🇪"],
        "ec": ["ecuador", "ecuatoriano", "ecuatoriana", "ec", "🇪🇨"],
        "br": ["brasil", "brasileño", "brasileña", "br", "🇧🇷"],
        "do": ["dominicana", "dominicano", "rd", "do", "🇩🇴"],
        "us": ["usa", "united states", "eeuu", "us", "🇺🇸"],
    }
    found: list[str] = []
    for indicator in geo_indicators:
        il = indicator.lower()
        for code, keywords in country_signal_keywords.items():
            if il in keywords:
                found.append(indicator)
                break
    return found


def classify_tier(followers: int) -> str:
    """Returns tier label based on follower count."""
    if followers < 10_000:
        return "NANO"
    if followers < 100_000:
        return "MICRO"
    if followers < 500_000:
        return "MID"
    return "MACRO"


def build_rationale(
    profile: dict,
    tier: str,
    followers: int,
    er: float,
    target_country: str = "VE",
) -> str:
    """Build a human-readable rationale string for a candidate profile.

    Args:
        profile: candidate profile dict with bio, biography, etc.
        tier: follower tier label (NANO, MICRO, MID, MACRO)
        followers: follower count
        er: engagement rate (decimal)
        target_country: ISO 2-letter country code (default VE)
    """
    country_name = _COUNTRY_NAMES.get(target_country.upper(), target_country)
    niches = _detect_niches(profile)

    niche_str = ", ".join(niches[:2]) if niches else "niche general"
    er_pct = er * 100

    return (
        f"Perfil {tier} de {niche_str} en {country_name}. "
        f"ER {er_pct:.1f}%, {followers:,} seguidores. "
        f"Perfil relevante para campaña en {country_name}."
    )


def has_hard_geo_signal(profile: dict, target_iso: str = "VE") -> bool:
    """Hard geo filter fallback: checks hard-coded city/country signals when geo_indicators fail.

    This prevents profiles with explicit location mentions from being incorrectly filtered out
    when geo_indicators don't match (e.g., LLM-generated indicators miss common aliases).

    Returns True if profile contains unambiguous VE location signals.
    """
    bio = (profile.get("biography") or profile.get("bio") or "").lower()
    full_name = (profile.get("full_name") or profile.get("fullName") or "").lower()
    location = (profile.get("locationName") or profile.get("location") or "").lower()
    username = (profile.get("username") or "").lower()
    search_text = f"{bio} {full_name} {location} {username}"

    if target_iso == "VE":
        ve_signals = [
            "venezuela", "vzla", "vzlex", "vzlan", "vzlano", "vzlana",
            "venezolano", "venezolana",
            "caracas", "maracaibo", "valencia", "maracay", "barquisimeto",
            "maturin", "maturín", "puerto la cruz", "ciudad guayana",
            "cabimas", "barinas", "mérida", "merida", "anzoátegui",
            "sancristóbal", "san cristobal", "turmero", "petare",
            "los teques", "guaira", "guáira", "cumaná", "cabudare",
            "araure", "acarigua", "barcelona", "margarita", "nueva esparta",
            "táchira", "tachira", "lara", "zulia", "miranda", "distrito capital",
            "🇻🇪",
        ]
        return any(sig in search_text for sig in ve_signals)
    return False


def geo_pre_filter_keywords(
    niches: list[str],
    geo_terms: list[str] | None = None,
    max_per_niche: int = 3,
) -> list[tuple[str, str]]:
    """Generate (niche, geo_term) tuples for pre-filter geographic discovery.

    Instead of searching "fitness" globally and filtering post-hoc to VE,
    this generates query pairs that incorporate geo context from the start:
    - ("fitness", "caracas")
    - ("mascotas", "vzla")
    - ("belleza", "maracaibo")

    This dramatically improves recall for VE discovery because the search
    API biases toward the geo context in results.

    Args:
        niches: list of niche keywords (from brief.niches)
        geo_terms: optional geo terms to combine; if None, uses hard-coded VE cities
        max_per_niche: cap of geo terms per niche to avoid query explosion

    Returns:
        List of (niche, geo_term) tuples. Can be used to build discovery queries
        like "fitness caracas" or to tag profiles with geographic context.
    """
    if not niches:
        return []

    default_geo = [
        "caracas", "maracaibo", "valencia", "barquisimeto",
        "maracay", "mérida", "maturín", "vzla", "venezuela",
    ]
    geo_pool = geo_terms[:max_per_niche] if geo_terms else default_geo[:max_per_niche]
    results: list[tuple[str, str]] = []
    for niche in niches:
        for geo in geo_pool:
            results.append((niche, geo))
    return results


def _detect_niches(profile: dict) -> list[str]:
    """Detecta nichos del perfil basándose en la bio."""
    bio = (profile.get("biography") or profile.get("bio") or "").lower()
    niches: list[str] = []
    niche_signals = {
        "mascotas": ["perro", "dog", "mascota", "pet", "cachorro", "canino", "gato", "cat", "mascotas"],
        "belleza": ["belleza", "makeup", "skincare", "cosmetica", "beauty", "cosmetic"],
        "fitness": ["fitness", "gym", "ejercicio", "muscle", "workout", "salud", "deporte"],
        "moda": ["moda", "fashion", "outfit", "style", "ropa", "vestuario"],
        "comida": ["comida", "recetas", "cocina", "food", "gastronomia", "chef", "eating"],
        "tecnologia": ["tecnologia", "tech", "gadget", "digital", "innovacion"],
        "viajes": ["viajes", "travel", "turismo", "vacaciones", "destino"],
        "negocios": ["negocios", "business", "emprendimiento", "startup", "empresa"],
        "entretenimiento": ["entretenimiento", "musica", "peliculas", "series", "cultura"],
        "cafe": ["cafe", "café", "coffee", "barista"],
        "deportes": ["deportes", "sports", "futbol", "atletismo"],
        "arte": ["arte", "art", "pintura", "diseno", "creatividad"],
        "gaming": ["gaming", "videojuegos", "games", "playstation", "xbox"],
        "lifestyle": ["lifestyle", "vida", "routine", "habitos"],
    }
    for niche, keywords in niche_signals.items():
        if any(k in bio for k in keywords):
            niches.append(niche)
    return niches
