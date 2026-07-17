"""BriefParser agent — interprets free text into BriefStructured."""

import re
from typing import Any

import structlog

from shared_ai.deepseek_client import deepseek_client
from discovery.schemas import BriefStructured

logger = structlog.get_logger(__name__)

BRIEF_PARSER_SYSTEM_PROMPT = """Eres un planner de influencer marketing con 10 años de experiencia en Venezuela y LATAM.

El usuario te describe un brief de campaña en lenguaje natural. Tu trabajo es extraer TODA la información relevante y estructurarla en el formato JSON que se indica.

REGLAS:
1. Si el usuario menciona un país, ciudad o región, siempre incluye Venezuela como país por defecto si no dice otro.
2. Si menciona un rango etario (ej. "mujeres de 25 a 35"), extrae audience_age_min y audience_age_max.
3. Si menciona plataformas (Instagram, TikTok, YouTube, Twitter/X, Facebook), incluye todas las mencionadas.
4. Si menciona un nicho (moda, belleza, fitness, tecnología, etc.), extrae las palabras clave como niches.
5. Si menciona un presupuesto, extrae budget_usd en dólares USD.
6. Si menciona un tono (aspiracional, casual, educativo, humorístico, etc.), agrégalo a tone.
7. Si menciona una marca específica, intenta inferir industry del contexto.
8. Si algo es ambiguo o falta información crítica (ej. país, plataforma), PREGUNTA al usuario antes de asumir un valor por defecto.
9. audience_gender: "female" si se refiere a mujeres, "male" si a hombres, "all" si no especifica.
10. audience_countries: usa códigos ISO 3166-1 alpha-2 en mayúsculas (VE, CO, MX, AR, CL, PE, EC, BO).
11. audience_cities: ciudades específicas dentro del país (Caracas, Valencia, Maracaibo, etc.).
12. additional_context: cualquier cosa que no encaje en los campos estructurados pero sea relevante.

Responde SOLO con el JSON estructurado. No incluyas explicaciones ni texto adicional."""

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
  "audience_countries": ["VE"],
  "audience_cities": ["ciudad1"],
  "budget_usd": número o null,
  "tone": ["tono1"],
  "platforms": ["instagram"],
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


class BriefParserAgent:
    async def parse(self, text: str) -> BriefStructured:
        user_prompt = BRIEF_PARSER_USER_TEMPLATE.format(brief_text=text)

        response = await deepseek_client.complete(
            prompt=user_prompt,
            system=BRIEF_PARSER_SYSTEM_PROMPT,
            temperature=0.3,
        )

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

        if "niches" in sanitized and not isinstance(sanitized["niches"], list):
            sanitized["niches"] = []

        if "tone" in sanitized and not isinstance(sanitized["tone"], list):
            sanitized["tone"] = []

        if "budget_usd" in sanitized and sanitized["budget_usd"] is not None:
            try:
                sanitized["budget_usd"] = float(sanitized["budget_usd"])
            except (ValueError, TypeError):
                sanitized["budget_usd"] = None

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


brief_parser_agent = BriefParserAgent()
