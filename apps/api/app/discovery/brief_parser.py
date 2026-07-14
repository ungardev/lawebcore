"""BriefParser agent — interpreta texto libre y lo convierte en BriefStructured."""

from app.ai.deepseek_client import deepseek_client
from app.discovery.schemas import BriefStructured


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


class BriefParserAgent:
    """Agent que parsea texto libre de brief a estructura."""

    async def parse(self, text: str) -> BriefStructured:
        """Parsea el texto libre del usuario y retorna un BriefStructured."""
        user_prompt = BRIEF_PARSER_USER_TEMPLATE.format(brief_text=text)

        response = await deepseek_client.complete(
            prompt=user_prompt,
            system=BRIEF_PARSER_SYSTEM_PROMPT,
            temperature=0.3,
        )

        return self._parse_response(response.content, text)

    def _parse_response(self, raw: str, original_text: str) -> BriefStructured:
        """Parsea el JSON crudo del LLM a BriefStructured."""
        import json

        try:
            data = json.loads(raw)
            brief = BriefStructured(**data)
            return brief
        except (json.JSONDecodeError, Exception) as e:
            return BriefStructured(
                additional_context=f"Error parsing: {e}. Original: {original_text[:200]}"
            )


brief_parser_agent = BriefParserAgent()
