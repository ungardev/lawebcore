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
    followers = profile.get("followersCount") or profile.get("follower_count") or 0
    is_business = profile.get("is_business") or profile.get("isBusinessAccount") or False
    er = profile.get("engagement_rate") or 0.0

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

    if is_business and followers > 5000 and er > 0.01:
        return 0.4
    if followers > 20000 and er > 0.02:
        return 0.3
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
