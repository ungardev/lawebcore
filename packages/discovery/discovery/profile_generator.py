"""DiscoveryProfile generator — creates/fetches profiles per brief fingerprint.

Architecture:
    BriefStructured
        │
        ▼ compute_fingerprint()
    fingerprint (sha256 of industry + sorted niches + sorted countries)
        │
        ├─── redis cache (lens:profile:{fingerprint}) ──→ DiscoveryProfile
        │
        ├─── DB lookup (discovery_profiles table) ──→ DiscoveryProfile
        │
        └─── DeepSeek generation ──→ DiscoveryProfile ──→ DB persist
                                       │
                                       └── fallback if LLM fails
"""

import asyncio
import hashlib
import json
import logging
import re
from typing import Any

import structlog

from discovery.schemas import BriefStructured
from shared_ai.deepseek_client import deepseek_client

logger = structlog.get_logger(__name__)

REDIS_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _normalize_for_fingerprint(text: str) -> str:
    """Remove accents and lowercase for consistent fingerprinting."""
    import unicodedata
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def compute_fingerprint(brief: BriefStructured) -> str:
    """Deterministic fingerprint: sha256 of normalized industry + sorted niches + sorted countries + sorted states + sorted cities.

    Same brief concept always produces the same fingerprint regardless of input phrasing.
    """
    industry = _normalize_for_fingerprint(brief.industry or "")
    niches = "|".join(sorted(_normalize_for_fingerprint(n) for n in (brief.niches or [])))
    countries = "|".join(sorted((c.upper() for c in (brief.audience_countries or [])), key=lambda x: (x, x)))
    states = "|".join(sorted(_normalize_for_fingerprint(s) for s in (brief.audience_states or [])))
    cities = "|".join(sorted(_normalize_for_fingerprint(c) for c in (brief.audience_cities or [])))
    raw = f"{industry}|{niches}|{countries}|{states}|{cities}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _country_code_to_currency() -> dict[str, str]:
    return {
        "VE": "bolivares",
        "CO": "pesos colombianos",
        "MX": "pesos mexicanos",
        "AR": "pesos argentinos",
        "CL": "pesos chilenos",
        "EC": "dólares",
        "PA": "dólares",
        "PE": "soles",
        "BR": "reales",
    }


_VE_STATE_CITIES: dict[str, list[str]] = {
    "Distrito Capital": ["caracas", "catia", "petare", "guarenas", "guatire"],
    "Miranda": ["los teques", "baruta", "chacao", "el hatillo", "guarenas", "guatire"],
    "Carabobo": ["valencia", "naguanagua", "puerto cabello"],
    "Aragua": ["maracay", "turmero", "el limon", "cagua"],
    "Lara": ["barquisimeto", "carora", "el tocuyo", "cabudare"],
    "Tachira": ["san cristobal", "rubio", "san antonio del tachira", "la grita"],
    "Zulia": ["maracaibo", "cabimas", "ciudad ojeda", "sinamaica"],
    "Anzoategui": ["barcelona", "puerto la cruz", "anaco", "porto franco"],
    "Bolivar": ["ciudad bolivar", "ciudad guayana", "puerto ordaz", "san felix"],
    "Monagas": ["maturin", "carupano"],
    "Sucre": ["cumana", "carupano", "cumanacoa"],
    "Merida": ["merida", "ejido", "tovar", "tabay"],
    "Barinas": ["barinas", "sabaneta de tovar"],
    "Portuguesa": ["guanare", "acarigua", "araure", "biscucuy"],
    "Guárico": ["san juan de los morros", "calabozo", "valle de la pascua", "tucupido"],
    "Cojedes": ["san carlos", "tinaco", "la apartada"],
    "Trujillo": ["trujillo", "valera", "bocono", "betijoque"],
    "Yaracuy": ["san felipe", "chivacoa", "yaritagua", "neiva"],
    "Falcón": ["coro", "punto fijo", "la vela de coro", "pueblo nuevo"],
    "Vargas": ["la guaira", "carayaca", "catia la mar"],
    "Amazonas": ["puerto ayacucho", "san fernando de apure"],
    "Apure": ["san fernando", "achaguas", "guasdualito", "elorza"],
    "Delta Amacuro": ["tucupita", "curiapo", "piacoa"],
}


def _country_code_to_geo_indicators() -> dict[str, list[str]]:
    return {
        "VE": [
            "venezuela", "vzla", "caracas", "maracaibo", "valencia",
            "san cristobal", "maturin", "barquisimeto", "puerto la cruz",
            "maracay", "merida", "ciudad guayana", "ciudad bolivar",
            "vzlatex", "vzlan", "venezolano", "venezolana", "🇻🇪",
            "anzoategui", "zulia", "lara", "yaracuy", "carabobo",
            "aragua", "portuguesa", "trujillo", "cojedes", "monagas",
            "sucre", "nueva esparta", "guarico", "apure", "barinas",
            "falcon", "amazonas", "bolivariano", "vzlano", "guatire",
            "los teques", "baruta", "chacao", "el hatillo", "petare",
            "catia", "cabudare", "villa de cura",
        ],
        "CO": [
            "colombia", "bogota", "medellin", "cali", "barranquilla",
            "cartagena", " cucuta", "pereira", "manizales", "ibague",
            "colombiano", "colombiana", "co", "🇨🇴",
        ],
        "MX": [
            "mexico", "cdmx", "guadalajara", "monterrey", "puebla",
            "tijuana", "leon", "juarez", "zapopan", "merida",
            "mexicano", "mexicana", "mx", "🇲🇽",
        ],
        "AR": [
            "argentina", "buenos aires", "cordoba", "rosario", "mendoza",
            "tucuman", "la plata", "mar del plata", "salta", "santa fe",
            "argentino", "argentina", "ar", "🇦🇷",
        ],
        "CL": [
            "chile", "santiago", "valparaiso", "concepcion", "la serena",
            "chileno", "chilena", "cl", "🇨🇱",
        ],
        "PA": [
            "panama", "ciudad de panama", "colon", "David", "chitré",
            "panameño", "panameña", "pa", "🇵🇦",
        ],
        "PE": [
            "peru", "lima", "arequipa", "trujillo", "chiclayo",
            "piura", "iquitos", "cusco", "peruano", "peruana", "pe", "🇵🇪",
        ],
        "EC": [
            "ecuador", "quito", "guayaquil", "cuenca", "manta",
            "ecuatoriano", "ecuatoriana", "ec", "🇪🇨",
        ],
        "BR": [
            "brasil", "brazil", "sao paulo", "rio de janeiro", "brasilia",
            "salvador", "fortaleza", "curitiba", "porto alegre",
            "brasileño", "brasileña", "br", "🇧🇷",
        ],
    }


_SYSTEM_PROMPT = """Eres el generador de queries de descubrimiento de La Web Figital Agency.
Tu trabajo es recibir un brief de campaña y devolver queries de búsqueda óptimas para Instagram.

Reglas estrictas:
- Devuelve SOLO JSON válido, sin texto adicional
- Los hashtags deben ser los que LA GENTE USA REALMENTE en el país objetivo, no traducciones literales
- Los keywords deben mezclar marca + categoría + hábito de consumo + competencia
- Los geo_indicators deben incluir: capitales, ciudades principales, gentilicios, abreviaturas coloquiales, bandera emoji
- Los buy_intent_keywords deben estar en el IDIOMA LOCAL y con la MONEDA LOCAL
- Inclúyete a ti mismo como generador; si no estás seguro de algo, usa el fallback del ejemplo
"""


def _build_generation_prompt(brief: BriefStructured, country: str, currency: str) -> str:
    country_geo = _country_code_to_geo_indicators().get(country.upper(), [])
    geo_str = ", ".join(f'"{g}"' for g in country_geo[:30])

    return f"""Genera queries de descubrimiento para esta campaña:

Brief: {brief.product_name or "producto"}
Industria: {brief.industry or "general"}
Nichos: {", ".join(brief.niches or ["general"])}
País objetivo: {country.upper()}
Ciudades: {", ".join(brief.audience_cities or ["capital y principales"])}

Devuelve este JSON exacto:
{{
  "hashtags": ["tag1", "tag2", ...],
  "keywords": ["keyword1", "keyword2", ...],
  "niche_keywords": ["término de nicho 1", "término de nicho 2", ...],
  "geo_indicators": [{geo_str}, "gentilicio local", "ciudad2"],
  "buy_intent_keywords": ["{currency}", "precio", "donde comprar", "tienda online", "oferta", "envio", "disponible"]
}}

hashtags: 20-30, SIN #, en español si el país es hispanohablante, relevantes al nicho y país
keywords: 15-25, frases de búsqueda que la gente usa en Instagram (nombre de marca, categoría, hábito)
niche_keywords: 40-80 términos en español que describen el nicho (productos, actividades, estilos de vida relacionados)
geo_indicators: capital, 5-8 ciudades principales, gentilicio, abreviaturas (vzla, co, mx...), emoji de bandera, variaciones de escritura
buy_intent_keywords: en el idioma del país, incluye la moneda local y sus variantes (pesos, $, bs, etc.)"""


def _validate_and_fill(raw: dict[str, Any], brief: BriefStructured) -> dict[str, Any]:
    """Ensure all fields are non-empty. Fill with heuristic fallback if missing."""
    country_code = (brief.audience_countries or ["VE"])[0].upper()
    currency_hint = _country_code_to_currency().get(country_code, "pesos")
    geo_fallback = _country_code_to_geo_indicators().get(country_code, ["venezuela", "vzla", "caracas"])

    def _ensure_list(val: Any, fallback: list[str]) -> list[str]:
        if isinstance(val, list) and val:
            return [str(v).strip() for v in val if v]
        return fallback

    return {
        "hashtags": _ensure_list(raw.get("hashtags"), [f"{brief.industry or 'mascotas'}{country_code}"]),
        "keywords": _ensure_list(raw.get("keywords"), [brief.product_name or brief.industry or "producto"]),
        "niche_keywords": _ensure_list(
            raw.get("niche_keywords"),
            brief.niches[:5] if brief.niches else ["mascotas", "perros"],
        ),
        "geo_indicators": _ensure_list(raw.get("geo_indicators"), geo_fallback),
        "buy_intent_keywords": _ensure_list(
            raw.get("buy_intent_keywords"),
            ["precio", "donde", "link", "comprar", "tienda", "oferta", "envio", currency_hint],
        ),
    }


async def _get_redis():
    """Lazy redis import to avoid hard dependency when cache is disabled."""
    try:
        import redis.asyncio as redis_async
        from shared_core.config import settings
        return redis_async.from_url(settings.ARQ_REDIS_URL, decode_responses=False)
    except Exception:
        return None


async def get_or_create_profile(brief: BriefStructured) -> dict[str, Any]:
    """Get or create a DiscoveryProfile for the given brief.

    Resolution order:
        1. Redis cache (lens:profile:{fingerprint})
        2. DB lookup by fingerprint
        3. DeepSeek generation (if new fingerprint)
        4. Fallback heuristic (if LLM fails)
    """
    fingerprint = compute_fingerprint(brief)
    logger.info("profile_generator_resolve", fingerprint=fingerprint, brief=str(brief)[:80])

    # 1. Redis cache
    redis_client = await _get_redis()
    if redis_client:
        try:
            cached = await redis_client.get(f"lens:profile:{fingerprint}")
            if cached:
                logger.info("profile_cache_hit", fingerprint=fingerprint)
                _inc_profile_metric("cache")
                return json.loads(cached)
        except Exception as exc:
            logger.warning("profile_cache_read_error", error=str(exc))

    # 2. DB lookup
    try:
        from shared_core.db import db_session
        from shared_core.supabase_rest import supabase_rest
        async with db_session():
            rows = await supabase_rest.select(
                table="discovery_profiles",
                where=[("fingerprint", "eq", fingerprint)],
                limit=1,
            )
            if rows:
                profile = rows[0]
                logger.info("profile_db_hit", fingerprint=fingerprint, source=profile.get("source"))
                _inc_profile_metric(profile.get("source", "unknown"))
                # Update times_used
                await supabase_rest.update(
                    table="discovery_profiles",
                    values={"times_used": (profile.get("times_used") or 0) + 1},
                    where=[("id", "eq", profile["id"])],
                )
                # Cache in Redis
                if redis_client:
                    try:
                        await redis_client.setex(
                            f"lens:profile:{fingerprint}",
                            REDIS_TTL_SECONDS,
                            json.dumps(profile),
                        )
                    except Exception:
                        pass
                return profile
    except Exception as exc:
        logger.warning("profile_db_error", error=str(exc))

    # 3. Generate with DeepSeek
    country = (brief.audience_countries or ["VE"])[0].upper()
    currency = _country_code_to_currency().get(country, "pesos")
    prompt = _build_generation_prompt(brief, country, currency)

    raw_profile: dict[str, Any] = {}
    try:
        result = await deepseek_client.complete_json(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=2000,
        )
        raw_profile = _validate_and_fill(result, brief)
        logger.info("profile_llm_generated", fingerprint=fingerprint, fields=list(raw_profile.keys()))
    except Exception as exc:
        logger.warning("profile_llm_failed_using_fallback", fingerprint=fingerprint, error=str(exc))
        raw_profile = _validate_and_fill({}, brief)

    profile = {
        "fingerprint": fingerprint,
        "vertical_slug": (brief.industry or "general").lower().replace(" ", "_"),
        "languages": ["es"],
        "countries": brief.audience_countries or [],
        "source": "fallback" if not raw_profile.get("hashtags") else "llm",
        **raw_profile,
    }

    if brief.audience_states and country == "VE":
        for state in brief.audience_states:
            state_key = state.title() if isinstance(state, str) else str(state)
            if state_key in _VE_STATE_CITIES:
                cities = _VE_STATE_CITIES[state_key]
                existing = set(g.lower() for g in profile.get("geo_indicators", []))
                for city in cities:
                    if city.lower() not in existing:
                        profile["geo_indicators"].append(city)

    # 4. Persist to DB
    try:
        from shared_core.db import db_session
        from shared_core.supabase_rest import supabase_rest
        async with db_session():
            existing = await supabase_rest.select(
                table="discovery_profiles",
                where=[("fingerprint", "eq", fingerprint)],
                limit=1,
            )
            if not existing:
                saved = await supabase_rest.insert(
                    table="discovery_profiles",
                    values=profile,
                    returning="representation",
                )
                if saved:
                    profile["id"] = saved.get("id")
                    logger.info("profile_persisted", fingerprint=fingerprint, source=profile["source"])
    except Exception as exc:
        logger.warning("profile_persist_error", error=str(exc))

    # Cache in Redis
    if redis_client:
        try:
            await redis_client.setex(f"lens:profile:{fingerprint}", REDIS_TTL_SECONDS, json.dumps(profile))
        except Exception:
            pass

    _inc_profile_metric(profile.get("source", "unknown"))
    return profile


def _inc_profile_metric(source: str) -> None:
    try:
        from app.core.metrics import lens_profile_generation_total
        lens_profile_generation_total.labels(source=source).inc()
    except Exception:
        pass
