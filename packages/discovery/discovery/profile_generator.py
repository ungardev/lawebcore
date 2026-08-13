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

ELITE TIER: This generator produces full-fidelity discovery intelligence including:
- Standard fields: hashtags, keywords, niche_keywords, geo_indicators, buy_intent_keywords
- Elite data: content_themes, audience_behavior, competitor_intel, local_slang,
  credibility_signals, niche_benchmarks, anti_bot_signals, geo_local_signals,
  query_variations
"""

import hashlib
import json
import logging
from typing import Any

import structlog

from discovery.schemas import BriefStructured
from shared_ai.deepseek_client import deepseek_client

logger = structlog.get_logger(__name__)

REDIS_TTL_SECONDS = 7 * 24 * 3600


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


_VE_MARKET_CONTEXT = """
CONTEXTO DE MERCADO VENEZUELA (Instagram):
- 4.5M usuarios Instagram activos
- 65% femenino, 25-44 años — el demographic más valioso para brands
- ER promedio: 4-7% (más alto que cualquier otro mercado latam por cultura de engagement orgánico)
- La gente en VE usa Instagram de forma más orgánica: hashtags locales, comentarios en español, menos corporate speak
- Formatos winners: Reels 15-30s (hook directo), Carousel 5-8 fotos, Stories diarias con polls/q&a
- Horarios peak: 19-21h (después del trabajo), 12-14h (pausa de almuerzo), fines de semana全天
- La gente busca productos en Instagram usando frases cortas en español, no hashtags gringos
- Moneda: bs (bolívares), $, a veces "pesos" — pero en VE es más común "$" o "bs"
- Slang local: "panas"=amigos, "peluche"=mascota querido, "jeva"=chica, "fulete"=aprovechado,
  "maras"=grupo de amigos, "chamo"=joven, "vex"=expresión de sorpresa
"""


_SYSTEM_PROMPT = f"""Eres el генератор de queries de descubrimiento ELITE de La Web Figital Agency.
Tu especialidad: el mercado de Instagram en Venezuela — el mercado más activo de Latam para influencer marketing.

{_VE_MARKET_CONTEXT}

REGLAS ESTRICTAS:
1. Devuelve SOLO JSON válido — ningún texto adicional, ningún comentario
2. hashtags: USA los que LA GENTE REAL USA en el país objetivo, no traducciones de hashtags gringos
3. keywords: piensa como la gente común — cómo buscan productos reales en Instagram, no como un marketeer
4. NO uses nombres de marcas específicas en los queries de búsqueda a menos que el brief las mencione explícitamente
5. competitor_intel: qué marcas ya tienen presencia fuerte en el país/ciudad para ese nicho (investiga desde el conocimiento general)
6. credibility_signals: qué hace que un perfil sea REAL y de CALIDAD en ese nicho específico (no señales genéricas)
7. anti_bot_signals: qué patrones son típicamente cuentas fake/bots/farm en ese nicho
8. content_themes: qué tipos de contenido funcionan mejor para este nicho en Instagram VE
9. Si no estás seguro de datos específicos, usa el contexto de arriba como fallback
10. TODO en español de Latam — hashtags en español, keywords en español

IDIOMA: Todo en español local. Moneda: usar la moneda del país (bs/$/pesos/etc)."""


def _build_generation_prompt(brief: BriefStructured, country: str, currency: str) -> str:
    country_geo = _country_code_to_geo_indicators().get(country.upper(), [])
    geo_str = ", ".join(f'"{g}"' for g in country_geo[:30])

    niches_str = ", ".join(brief.niches or ["general"])
    tone_str = ", ".join(brief.tone) if brief.tone else "casual, auténtico"
    competitor_str = ", ".join(brief.competitor_brands) if brief.competitor_brands else "no especificadas"
    cities_str = ", ".join(brief.audience_cities) if brief.audience_cities else "capital y principales ciudades"

    return f"""Genera queries de descubrimiento ELITE para esta campaña de Instagram:

PRODUCTO: {brief.product_name or "producto"}
INDUSTRIA: {brief.industry or "general"}
NICHOS: {niches_str}
TONO DE CAMPAÑA: {tone_str}
PAÍS OBJETIVO: {country.upper()}
CIUDADES: {cities_str}
MARCAS COMPETIDORAS: {competitor_str}

Genera el JSON completo con todos los campos abajo:

{{
  "hashtags": ["tag1", "tag2", ...],
  "keywords": ["keyword1", "keyword2", ...],
  "niche_keywords": ["término de nicho 1", "término de nicho 2", ...],
  "geo_indicators": [{geo_str}, "gentilicio local", "ciudad2"],
  "buy_intent_keywords": ["{currency}", "precio", "donde comprar", "tienda online", "oferta", "envio", "disponible"],
  "elite_data": {{
    "content_themes": ["tipo de contenido 1", "tipo de contenido 2", ...],
    "audience_behavior": {{
      "posting_hours": ["19-21h", "12-14h"],
      "best_days": ["sábado", "domingo", "miércoles"],
      "content_formats": ["Reels 15-30s", "Carousel 5-8 fotos", "Stories diarias"],
      "engagement_pattern": "patrón de engagement típico del país"
    }},
    "competitor_intel": {{
      "brands": ["marca1", "marca2"],
      "hashtags": ["#hashtag1", "#hashtag2"],
      "strategies": ["estrategia1", "estrategia2"]
    }},
    "local_slang": ["palabra1", "palabra2", "palabra3"],
    "credibility_signals": ["señal1", "señal2", "señal3"],
    "niche_benchmarks": {{
      "min_followers": 5000,
      "min_er": 0.035,
      "target_er": 0.055,
      "max_fake_ratio": 0.15,
      "min_posts": 30,
      "ideal_follower_range": "rango ideal en formato min-max"
    }},
    "anti_bot_signals": [
      "patrón 1 que indica bot o fake",
      "patrón 2 que indica bot o fake"
    ],
    "geo_local_signals": {{
      "city_neighborhoods": {{
        "caracas": ["la candelaria", "chacao", "baruta", "petare"],
        "maracaibo": ["costa ver", "sabaneta"]
      }},
      "wealth_areas": ["zona1", "zona2"],
      "trending_areas": ["zona1", "zona2"]
    }},
    "query_variations": {{
      "hashtag_stacking": ["combinación1", "combinación2"],
      "keyword_combinations": ["frase1", "frase2", "frase3"]
    }}
  }}
}}

hashtags: 20-30, SIN #, en español local, relevantes al nicho y país
keywords: 15-25, frases que la gente USA para buscar productos similares en Instagram
niche_keywords: 15-25 términos en español que describen el nicho (productos, actividades, estilos)
geo_indicators: capital, 5-8 ciudades, gentilicio, abreviaturas (vzla, co...), emoji bandera, variaciones
buy_intent_keywords: en el idioma del país, incluye la moneda local y sus variantes
elite_data.content_themes: 5-8 tipos de contenido que funcionan en este nicho en Instagram VE
elite_data.audience_behavior: posting_hours (horas pico), best_days (días winners), content_formats (formatos que más funcionan), engagement_pattern
elite_data.competitor_intel: brands que já tienen presencia fuerte en VE para este nicho, hashtags que usan, estrategias que emplean
elite_data.local_slang: 5-10 palabras de slang local que pueden aparecer en bios o posts
elite_data.credibility_signals: 5-8 señales específicas que demuestran que un perfil es real y de calidad (ej: "external_url", "publicaciones con location tag", "bio con email")
elite_data.niche_benchmarks: min_followers, min_er (mínimo engagement rate aceptable), target_er (el ER ideal para este nicho), max_fake_ratio, min_posts, ideal_follower_range
elite_data.anti_bot_signals: 5-8 patrones que indican cuenta fake/bot/farm (ej: "followers < 500 AND following > 2000")
elite_data.geo_local_signals: city_neighborhoods (barrios específicos por ciudad), wealth_areas (zonas de alto poder adquisitivo), trending_areas (zonas en crecimiento)
elite_data.query_variations: hashtag_stacking (combinaciones de hashtags efectivos), keyword_combinations (frases de búsqueda combinadas)"""


def _validate_and_fill(raw: dict[str, Any], brief: BriefStructured) -> dict[str, Any]:
    """Ensure all fields are non-empty. Fill with heuristic fallback if missing."""
    country_code = (brief.audience_countries or ["VE"])[0].upper()
    currency_hint = _country_code_to_currency().get(country_code, "pesos")
    geo_fallback = _country_code_to_geo_indicators().get(country_code, ["venezuela", "vzla", "caracas"])

    def _ensure_list(val: Any, fallback: list[str]) -> list[str]:
        if isinstance(val, list) and val:
            return [str(v).strip() for v in val if v]
        return fallback

    def _ensure_dict(val: Any, fallback: dict[str, Any]) -> dict[str, Any]:
        if isinstance(val, dict) and val:
            return val
        return fallback

    raw_elite = raw.get("elite_data", {}) or {}

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
        "elite_data": _validate_elite_data(raw_elite, brief, country_code),
    }


def _validate_elite_data(raw: dict[str, Any], brief: BriefStructured, country_code: str) -> dict[str, Any]:
    """Validate and fill elite_data with sensible fallbacks per country."""
    industry = (brief.industry or "general").lower()

    def _ensure_list(val: Any, fallback: list[str]) -> list[str]:
        if isinstance(val, list) and val:
            return [str(v).strip() for v in val if v]
        return fallback

    def _ensure_dict(val: Any, fallback: dict[str, Any]) -> dict[str, Any]:
        if isinstance(val, dict) and val:
            return val
        return fallback

    content_themes_fallback = [
        f"consejos sobre {industry}",
        f"productos {industry} review",
        f"día a día con mi {industry}",
        f"comparativas y opiniones",
        f"tips y recomendaciones",
    ]
    if country_code == "VE":
        content_themes_fallback = [
            "tips y consejos prácticos",
            "review y opiniones reales",
            "día a día / behind the scenes",
            "comparativas y rankings",
            "historias de vida relacionadas",
            "contenido educativo del nicho",
            "contenido entertainme también",
        ]

    audience_behavior_fallback = {
        "posting_hours": ["19:00-21:00", "12:00-14:00"],
        "best_days": ["sábado", "domingo", "miércoles"],
        "content_formats": ["Reels 15-30s", "Carousel 5-8 fotos", "Stories diarias"],
        "engagement_pattern": "alto engagement orgánico, 4-7% promedio",
    }
    if country_code == "VE":
        audience_behavior_fallback = {
            "posting_hours": ["19:00-21:00", "12:00-14:00", "22:00-23:00"],
            "best_days": ["sábado", "domingo", "miércoles", "viernes"],
            "content_formats": ["Reels 15-30s", "Carousel 5-8 fotos", "Stories con encuestas", "Posts con caption largo"],
            "engagement_pattern": "4-7% ER promedio — más alto que otros mercados latam por cultura de engagement",
        }

    credibility_signals_fallback = [
        "external_url en bio (web o linktree)",
        "publicaciones con location tag",
        "hashtags locales en posts",
        "bio con información de contacto",
        "cuenta verificada",
        "posts con múltiples fotos/videos",
    ]

    niche_benchmarks_fallback = {
        "min_followers": 5000,
        "min_er": 0.035,
        "target_er": 0.055,
        "max_fake_ratio": 0.15,
        "min_posts": 30,
        "ideal_follower_range": "5k-150k",
    }

    anti_bot_signals_fallback = [
        "followers_count < 500 AND following_count > 2000",
        "posts_count < 20 AND followers > 10000",
        "engagement_rate < 0.5% con > 50k followers",
        "comentarios casi todos en menos de 1 hora después de publicar",
        "bio solo con links externos y sin contenido real",
        "username con números aleatorios o patrones raros",
        "ninguna publicación con geolocalización",
    ]

    geo_local_signals_fallback = {
        "city_neighborhoods": {
            "caracas": ["la candelaria", "chacao", "baruta", "el hatillo", "petare", "catia"],
            "maracaibo": ["costa verde", "sabaneta", "el mills"],
            "valencia": ["las trincheras", "mañongo"],
        },
        "wealth_areas": ["chacao", "baruta", "el hatillo"],
        "trending_areas": ["petare", "catia", "23 de enero"],
    }

    if country_code == "VE":
        geo_local_signals_fallback = {
            "city_neighborhoods": {
                "caracas": ["la candelaria", "chacao", "baruta", "el hatillo", "petare", "catia", "san bernardino", "altamira", "las mercedes"],
                "maracaibo": ["costa verde", "sabaneta", "el mills", "ciudad industrial"],
                "valencia": ["las trincheras", "mañongo", "trigal"],
                "barquisimeto": ["catedral", "cuba", "el manjar"],
                "maracay": ["las delicias", "san jacinto", "elipse"],
            },
            "wealth_areas": ["chacao", "baruta", "el hatillo", "las mercedes", "altamira"],
            "trending_areas": ["petare", "catia", "23 de enero", "san martín"],
        }

    return {
        "content_themes": _ensure_list(raw.get("content_themes"), content_themes_fallback),
        "audience_behavior": _ensure_dict(raw.get("audience_behavior"), audience_behavior_fallback),
        "competitor_intel": _ensure_dict(raw.get("competitor_intel"), {"brands": [], "hashtags": [], "strategies": []}),
        "local_slang": _ensure_list(raw.get("local_slang"), ["panas", "jeva", "chamo", "peluche"]),
        "credibility_signals": _ensure_list(raw.get("credibility_signals"), credibility_signals_fallback),
        "niche_benchmarks": _validate_niche_benchmarks(raw.get("niche_benchmarks"), niche_benchmarks_fallback),
        "anti_bot_signals": _ensure_list(raw.get("anti_bot_signals"), anti_bot_signals_fallback),
        "geo_local_signals": _ensure_dict(raw.get("geo_local_signals"), geo_local_signals_fallback),
        "query_variations": _ensure_dict(raw.get("query_variations"), {"hashtag_stacking": [], "keyword_combinations": []}),
    }


def _validate_niche_benchmarks(raw: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or not raw:
        return fallback
    result = dict(fallback)
    for key in ["min_followers", "min_er", "target_er", "max_fake_ratio", "min_posts"]:
        if key in raw and raw[key] is not None:
            result[key] = raw[key]
    if "ideal_follower_range" in raw and raw["ideal_follower_range"]:
        result["ideal_follower_range"] = str(raw["ideal_follower_range"])
    return result


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

    try:
        from shared_core.db import db_session
        from shared_core.railway_pg import railway_pg
        async with db_session():
            rows = await railway_pg.select(
                table="discovery_profiles",
                filters=[f"fingerprint=eq.{fingerprint}"],
                limit=1,
            )
            if rows:
                profile = rows[0]
                logger.info("profile_db_hit", fingerprint=fingerprint, source=profile.get("source"))
                _inc_profile_metric(profile.get("source", "unknown"))
                await railway_pg.update(
                    table="discovery_profiles",
                    values={"times_used": (profile.get("times_used") or 0) + 1},
                    filters=[f"id=eq.{profile['id']}"],
                )
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

    country = (brief.audience_countries or ["VE"])[0].upper()
    currency = _country_code_to_currency().get(country, "pesos")
    prompt = _build_generation_prompt(brief, country, currency)

    raw_profile: dict[str, Any] = {}
    try:
        result = await deepseek_client.complete_json(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=6000,
        )
        raw_profile = _validate_and_fill(result, brief)
        logger.info("profile_llm_generated", fingerprint=fingerprint, fields=list(raw_profile.keys()), elite=bool(raw_profile.get("elite_data")))
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

    try:
        from shared_core.db import db_session
        from shared_core.railway_pg import railway_pg
        async with db_session():
            existing = await railway_pg.select(
                table="discovery_profiles",
                filters=[f"fingerprint=eq.{fingerprint}"],
                limit=1,
            )
            if not existing:
                saved = await railway_pg.insert(
                    table="discovery_profiles",
                    values=profile,
                    returning="representation",
                )
                if saved:
                    profile["id"] = saved.get("id")
                    logger.info("profile_persisted", fingerprint=fingerprint, source=profile["source"])
    except Exception as exc:
        logger.warning("profile_persist_error", error=str(exc))

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
