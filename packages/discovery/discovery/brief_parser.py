"""BriefParser agent — interprets free text into BriefStructured."""

import hashlib
import re
from typing import Any

import structlog

from shared_ai.deepseek_client import deepseek_client
from discovery.schemas import BriefStructured

logger = structlog.get_logger(__name__)

BRIEF_PARSER_SYSTEM_PROMPT = """Eres el planner estratégico de La Web Figital Agency. Extrae información de campañas en lenguaje natural y devuélvela en JSON. Si algo falta, pregunta antes de asumir."""

_parse_cache: dict[str, str] = {}


def _get_cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

BRIEF_PARSER_USER_TEMPLATE = """Extrae el brief de la siguiente descripción de campaña:

---

{brief_text}

---

Responde en JSON con este formato exacto:
{{
  "product_name": "nombre del producto o null",
  "brand_id": null,
  "industry": "industria inferida o null",
  "niches": ["nicho1", "nicho2"],
  "audience_gender": "female|male|all",
  "audience_age_min": número,
  "audience_age_max": número,
  "audience_countries": ["código ISO del país o países objetivo"],
  "audience_cities": ["ciudad1"],
  "audience_states": ["estado1", "estado2"],
  "tone": ["tono1"],
  "platforms": ["instagram"],
  "hashtags": ["#hashtag1", "#hashtag2"],
  "additional_context": "contexto adicional o vacío"
}}"""

_PLATFORM_MAP = {
    "instagram": "instagram",
    "tiktok": "tiktok",
    "youtube": "youtube",
    "twitter": "x",
    "x": "x",
    "facebook": "facebook",
    "fb": "facebook",
}

_COUNTRY_NAME_TO_ISO = {
    "venezuela": "VE",
    "colombia": "CO",
    "mexico": "MX",
    "argentina": "AR",
    "chile": "CL",
    "peru": "PE",
    "ecuador": "EC",
    "bolivia": "BO",
    "uruguay": "UY",
    "paraguay": "PY",
    "panama": "PA",
    "dominicana": "DO",
    "puertorico": "PR",
    "costarica": "CR",
    "guatemala": "GT",
}

_TONE_NORMALIZATION_MAP = {
    "emocional": "emocional",
    "emocio": "emocional",
    "emociona": "emocional",
    "emocive": "emocional",
    "emocion": "emocional",
    "emocionale": "emocional",
    "divertido": "divertido",
    "divert": "divertido",
    "diverti": "divertido",
    "formal": "formal",
    "casual": "casual",
    "humoristico": "humorístico",
    "humorist": "humorístico",
    "humoristica": "humorístico",
    "inspirador": "inspirador",
    "inspiradora": "inspirador",
    "educativo": "educativo",
    "educativa": "educativo",
    "lujoso": "lujoso",
    "luxury": "lujoso",
    "premium": "premium",
    "autentico": "auténtico",
    "autentica": "auténtico",
    "real": "real",
    "competitivo": "competitivo",
    "ambicioso": "ambicioso",
    "corporativo": "corporativo",
    "corporativa": "corporativo",
    "infantil": "infantil",
    "juvenil": "juvenil",
    "maternal": "maternal",
    "femenino": "femenino",
    "masculino": "masculino",
    "neutro": "neutro",
    "mincioso": "mincioso",
    "mincio": "mincioso",
}

_DOCUMENT_PARSER_SYSTEM_PROMPT = """Eres un estratega senior de influencer marketing en Latam con 15 años de experiencia. Recibirás un brief de campaña (puede ser PDF, TXT, CSV o texto libre). Extrae TODA la información relevante y devuélvela como JSON estructurado.

REGLAS ABSOLUTAS:
- Si el documento NO contiene un campo específico, usa null o [] (NUNCA inventes datos)
- Si el documento es ambiguo, incluye la info textual en `additional_context`
- `audience_countries` SIEMPRE en códigos ISO-2 (VE, CO, MX, AR, CL, PE, EC, BO, UY, PY, PA, DO, PR, CR, GT)
- `platforms` SIEMPRE minúsculas (instagram, tiktok, youtube, x, facebook)
- `tone` en español, minúsculas, sin acentos en valores enum
- `niches`: máximo 5, los más específicos al producto
- `hashtags`: máximo 10, los más relevantes para el nicho
- `kpis`: máximo 5 KPIs específicos (reach, engagement_rate, conversions, impressions, ctr, etc.)
- `campaign_objective`: solo uno de: awareness, consideration, conversion, retention, advocacy
- `budget_currency`: código ISO 4217 (USD, EUR, COP, MXN, etc.)
- `competitor_brands`: máximo 5 competidores mencionados
- `influencer_preferences.tiers`: array de [NANO, MICRO, MID, MACRO, MEGA]
- `campaign_dates`: objeto con start/end en formato YYYY-MM-DD o null si no se especifica
- `brief_source`: siempre "file_upload"
- `source_document`: incluye solo {file_name, file_size_bytes, mime_type, pages} si disponibles"""

_DOCUMENT_PARSER_USER_TEMPLATE = """Analiza el siguiente brief de campaña y extrae TODOS los campos posibles:

---

{document_text}

---

Responde SOLO con JSON válido, sin texto adicional:

{{
  "product_name": "nombre del producto o null",
  "brand_id": null,
  "brand_name": "nombre de marca o null",
  "industry": "industria inferida o null",
  "niches": ["nicho1", "nicho2"],
  "hashtags": ["#hashtag1", "#hashtag2"],
  "audience_gender": "female|male|all",
  "audience_age_min": número,
  "audience_age_max": número,
  "audience_countries": ["código ISO del país o países objetivo"],
  "audience_cities": ["ciudad1"],
  "tone": ["tono1"],
  "platforms": ["instagram", "tiktok"],
  "campaign_objective": "awareness|consideration|conversion|retention|advocacy|null",
  "campaign_name": "nombre de campaña o null",
  "budget_usd": número o null,
  "budget_currency": "USD|EUR|COP|MXN|null",
  "kpis": ["kpi1", "kpi2"],
  "campaign_dates": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}},
  "key_themes": ["tema1", "tema2"],
  "competitor_brands": ["competidor1"],
  "influencer_preferences": {{"tiers": ["MICRO", "MID"], "min_er": 0.04}},
  "additional_context": "resumen del documento o vacío",
  "brief_source": "file_upload",
  "source_document": {{"file_name": "nombre.pdf", "file_size_bytes": 0, "mime_type": "application/pdf", "pages": 1}}
}}"""





class BriefParserAgent:
    async def parse(self, text: str) -> BriefStructured:
        cache_key = _get_cache_key(text)
        if cache_key in _parse_cache:
            cached = _parse_cache[cache_key]
            logger.info("brief_parser_cache_hit", cache_key=cache_key[:8])
            return self._parse_response(cached, text)

        user_prompt = BRIEF_PARSER_USER_TEMPLATE.format(brief_text=text)

        response = await deepseek_client.complete(
            prompt=user_prompt,
            system=BRIEF_PARSER_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        _parse_cache[cache_key] = response.content

        logger.info(
            "deepseek_brief_response",
            content_preview=response.content[:500],
            content_length=len(response.content),
            model=response.model,
        )

        return self._parse_response(response.content, text)

    def _extract_json(self, raw: str) -> str | None:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return match.group()
        return None

    def _coerce_to_int(self, value: Any, default: int) -> int:
        if value is None:
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            match = re.search(r'\d+', value.strip())
            if match:
                return int(match.group())
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _normalize_enum_value(self, value: str, allowed_values: set[str], default: str) -> str:
        if not value:
            return default
        normalized = str(value).strip().lower()
        if normalized in allowed_values:
            return normalized
        if normalized in {"all", "todo", "todos", "cualquier"}:
            return "all"
        if normalized in {"female", "mujer", "women", "femenino"}:
            return "female"
        if normalized in {"male", "hombre", "men", "masculino"}:
            return "male"
        return default

    def _sanitize_brief_data(self, data: dict[str, Any]) -> dict[str, Any]:
        sanitized = dict(data)

        for age_field in ["audience_age_min", "audience_age_max"]:
            if age_field in sanitized:
                default = 18 if "min" in age_field else 65
                sanitized[age_field] = self._coerce_to_int(sanitized[age_field], default)

        if "audience_gender" in sanitized:
            sanitized["audience_gender"] = self._normalize_enum_value(
                sanitized["audience_gender"],
                {"female", "male", "all"},
                "all",
            )

        if "platforms" in sanitized and isinstance(sanitized["platforms"], list):
            normalized_platforms = []
            for p in sanitized["platforms"]:
                p_lower = str(p).strip().lower()
                if p_lower in _PLATFORM_MAP:
                    normalized_platforms.append(_PLATFORM_MAP[p_lower])
                elif p_lower.replace(" ", "") in _PLATFORM_MAP:
                    normalized_platforms.append(_PLATFORM_MAP[p_lower.replace(" ", "")])
            sanitized["platforms"] = normalized_platforms if normalized_platforms else ["instagram"]

        if "audience_countries" in sanitized and isinstance(sanitized["audience_countries"], list):
            normalized_countries = []
            for c in sanitized["audience_countries"]:
                c_str = str(c).strip()
                c_upper = c_str.upper()
                c_lower = c_str.lower()
                if c_upper in _COUNTRY_NAME_TO_ISO.values():
                    normalized_countries.append(c_upper)
                elif c_lower in _COUNTRY_NAME_TO_ISO:
                    normalized_countries.append(_COUNTRY_NAME_TO_ISO[c_lower])
                else:
                    normalized_countries.append(c_upper)
            sanitized["audience_countries"] = normalized_countries if normalized_countries else ["VE"]

        if "audience_cities" in sanitized and not isinstance(sanitized["audience_cities"], list):
            sanitized["audience_cities"] = []

        if "audience_states" in sanitized and not isinstance(sanitized["audience_states"], list):
            sanitized["audience_states"] = []

        if "niches" in sanitized and not isinstance(sanitized["niches"], list):
            sanitized["niches"] = []

        if "tone" in sanitized and isinstance(sanitized["tone"], list):
            normalized_tones = []
            for t in sanitized["tone"]:
                t_lower = str(t).strip().lower()
                normalized_tones.append(_TONE_NORMALIZATION_MAP.get(t_lower, t_lower))
            sanitized["tone"] = normalized_tones
        else:
            sanitized["tone"] = []

        if "hashtags" in sanitized and isinstance(sanitized["hashtags"], list):
            sanitized["hashtags"] = [str(h).strip() for h in sanitized["hashtags"] if h]
        else:
            sanitized["hashtags"] = []

        return sanitized

    def _parse_response(self, raw: str, original_text: str) -> BriefStructured:
        import json

        try:
            json_str = self._extract_json(raw)
            if not json_str:
                raise ValueError(f"No JSON found in response: {raw[:200]}")

            data = json.loads(json_str)
            sanitized = self._sanitize_brief_data(data)

            logger.info(
                "brief_parsed_successfully",
                niches=sanitized.get("niches", []),
                platforms=sanitized.get("platforms", []),
                countries=sanitized.get("audience_countries", []),
                gender=sanitized.get("audience_gender"),
            )

            brief = BriefStructured(**sanitized)
            return brief

        except json.JSONDecodeError as e:
            logger.error(
                "brief_parser_json_decode_failed",
                error=str(e),
                raw_content=raw[:500],
                original_text=original_text[:200],
                exc_info=True,
            )
            return BriefStructured(
                additional_context=f"Error parsing JSON: {str(e)[:200]}. Original: {original_text[:200]}"
            )
        except Exception as e:
            logger.error(
                "brief_parser_validation_failed",
                error=str(e),
                error_type=type(e).__name__,
                raw_content=raw[:500],
                original_text=original_text[:200],
                exc_info=True,
            )
            return BriefStructured(
                additional_context=f"Error parsing: {str(e)[:200]}. Original: {original_text[:200]}"
            )

    async def parse_from_document(self, text: str, file_meta: dict[str, Any]) -> BriefStructured:
        logger.info("document_brief_parser_started", file_meta=file_meta, text_length=len(text))

        user_prompt = _DOCUMENT_PARSER_USER_TEMPLATE.format(document_text=text)

        response = await deepseek_client.complete(
            prompt=user_prompt,
            system=_DOCUMENT_PARSER_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        logger.info(
            "document_brief_deepseek_response",
            content_preview=response.content[:500],
            content_length=len(response.content),
            model=response.model,
        )

        brief = self._parse_response(response.content, text)
        if file_meta:
            brief.source_document = file_meta
        brief.brief_source = "file_upload"
        return brief


brief_parser_agent = BriefParserAgent()
