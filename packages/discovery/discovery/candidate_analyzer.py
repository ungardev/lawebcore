"""CandidateAnalyzer — DeepSeek-powered AI analysis of discovery candidates.

Replaces hardcoded placeholder values (content_quality=80, audience_quality=50)
and rule-based rationale generation with real AI analysis.

Adds three new scored fields per candidate:
  - content_quality: 0-100 (production quality, niche coherence)
  - audience_quality: 0-100 (authenticity signals, bot detection)
  - brand_fit: 0-100 (alignment with campaign brief)

Plus an AI-generated rationale replacing the regex-based build_rationale().
"""

import asyncio
import structlog
from typing import Any

from shared_ai.deepseek_client import deepseek_client

logger = structlog.get_logger(__name__)

MAX_CONCURRENT_ANALYSIS = 10
BATCH_SIZE = 10


SYSTEM_PROMPT = """Eres un analista senior de influencer marketing con 15 años de experiencia en Latam.
Tu tarea es analizar perfiles de Instagram y devolver puntuaciones objetivas de 0 a 100.

REGLAS:
- content_quality: Evalúa producción visual, variedad de contenido, coherencia de nicho.
  90-100 = alta producción, nicho claro, contenido diverso.
  70-89 = buena producción, nicho presente.
  50-69 = producción media, nicho vago.
  30-49 = baja producción, contenido genérico.
  0-29 = cuenta casi vacía o sin nicho.

- audience_quality: Evalúa señales de audiencia real vs bots/farm.
  90-100 = engagement orgánico consistente, comentarios genuinos, cuenta activa real.
  70-89 = cuenta real con engagement normal.
  50-69 = señales mixtas, posible uso de engagement groups.
  30-49 = engagement suspecto, patrones de bots.
  0-29 = alta probabilidad de bots/farm.

- brand_fit: Alineación con la campaña objetivo.
  90-100 = perfíl totalmente alineado: nicho + tono + audiencia perfecta.
  70-89 = buena alineación con la campaña.
  50-69 = alineación parcial, algunos elementos fuera de foco.
  30-49 = alineación débil.
  0-29 = perfíl no relevante para esta campaña.

- summary: Frase breve en español explicando el reasoning (2-3 oraciones).

Responde SOLO con JSON válido, sin texto adicional."""


def _build_analysis_prompt(
    handle: str,
    followers: int,
    biography: str,
    latest_posts: list[dict[str, Any]],
    industry: str | None,
    niches: list[str],
    tone: list[str],
    country: str,
) -> str:
    bio = biography or "(sin bio)"
    bio_preview = bio[:300]

    captions: list[str] = []
    for post in (latest_posts or [])[:6]:
        caption = (post.get("caption") or "")[:200]
        if caption:
            captions.append(f"- \"{caption}\"")

    caption_text = "\n".join(captions) if captions else "(sin posts recientes)"

    niches_str = ", ".join(niches) if niches else "general"
    tone_str = ", ".join(tone) if tone else "casual"
    industry_str = industry or "productos de consumo"

    return f"""Analiza este influencer para campaña de {industry_str} en {country}.

@ {handle} — {followers:,} seguidores

BIO:
{bio_preview}

CAPTIONS RECIENTES:
{caption_text}

Contexto de campaña:
- Nichos: {niches_str}
- Tono: {tone_str}
- País objetivo: {country}

Responde en JSON:
{{
  "content_quality": 0-100,
  "audience_quality": 0-100,
  "brand_fit": 0-100,
  "summary": "razonamiento breve en español"
}}"""


def _fallback_scores(candidate: dict[str, Any]) -> dict[str, Any]:
    followers = candidate.get("followers", 0) or 0
    er = candidate.get("engagement_rate") or 0

    if followers >= 100_000:
        content_quality = 75
    elif followers >= 20_000:
        content_quality = 68
    elif followers >= 5_000:
        content_quality = 60
    else:
        content_quality = 50

    if er > 0.10:
        audience_quality = 80
    elif er > 0.04:
        audience_quality = 65
    elif er > 0.01:
        audience_quality = 50
    else:
        audience_quality = 30

    bio = (candidate.get("bio") or candidate.get("biography") or "").lower()
    niche_keywords = ["mascota", "pet", "dog", "perro", "belleza", "moda", "fitness",
                      "tecnologia", "comida", "viajes", "lifestyle", "negocios"]
    has_niche = any(k in bio for k in niche_keywords)
    brand_fit = 75 if has_niche else 55

    return {
        "content_quality": content_quality,
        "audience_quality": audience_quality,
        "brand_fit": brand_fit,
        "ai_summary": None,
    }


class CandidateAnalyzer:
    def __init__(self):
        self._client = None

    async def analyze_candidates_batch(
        self,
        candidates: list[dict[str, Any]],
        brief: Any,
        profile_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Analyze a batch of candidates with DeepSeek.

        Returns the same list with enriched AI fields added to each candidate dict.
        Uses asyncio.Semaphore to limit concurrent DeepSeek calls.
        Falls back to heuristic scores on any error.
        """
        if not candidates:
            return candidates

        from shared_core.config import settings
        if not settings.ENABLE_AI_ANALYZER:
            logger.info("ai_analyzer_disabled_skipping")
            return candidates

        industry = getattr(brief, "industry", None)
        niches = getattr(brief, "niches", []) or []
        tone = getattr(brief, "tone", []) or []
        countries = getattr(brief, "audience_countries", []) or []
        country = countries[0] if countries else "Venezuela"

        enriched_by_handle: dict[str, dict[str, Any]] = {}
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_ANALYSIS)

        async def _analyze_one(candidate: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            handle = candidate.get("handle", "")
            async with semaphore:
                result = await _analyze_single_candidate(
                    candidate=candidate,
                    industry=industry,
                    niches=niches,
                    tone=tone,
                    country=country,
                )
                return handle, result

        tasks = [_analyze_one(c) for c in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning("candidate_analysis_exception", error=str(result))
                continue
            handle, analysis = result
            enriched_by_handle[handle] = analysis

        for candidate in candidates:
            handle = candidate.get("handle", "")
            analysis = enriched_by_handle.get(handle)
            if analysis:
                candidate["content_quality"] = analysis["content_quality"]
                candidate["audience_quality"] = analysis["audience_quality"]
                candidate["brand_fit"] = analysis["brand_fit"]
                if analysis.get("ai_summary"):
                    candidate["ai_rationale"] = analysis["ai_summary"]
            else:
                fb = _fallback_scores(candidate)
                candidate["content_quality"] = fb["content_quality"]
                candidate["audience_quality"] = fb["audience_quality"]
                candidate["brand_fit"] = fb["brand_fit"]

        return candidates


async def _analyze_single_candidate(
    candidate: dict[str, Any],
    industry: str | None,
    niches: list[str],
    tone: list[str],
    country: str,
) -> dict[str, Any]:
    handle = candidate.get("handle", "unknown")
    followers = candidate.get("followers") or 0
    bio = candidate.get("bio") or candidate.get("biography") or ""
    latest_posts = candidate.get("latestPosts") or candidate.get("raw_payload", {}).get("latestPosts") or []

    prompt = _build_analysis_prompt(
        handle=handle,
        followers=followers,
        biography=bio,
        latest_posts=latest_posts,
        industry=industry,
        niches=niches,
        tone=tone,
        country=country,
    )

    try:
        result = await deepseek_client.complete(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=300,
        )

        content = result.content.strip()

        import json, re
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in response: {content[:200]}")

        data = json.loads(match.group())

        return {
            "content_quality": max(0, min(100, int(data.get("content_quality", 50)))),
            "audience_quality": max(0, min(100, int(data.get("audience_quality", 50)))),
            "brand_fit": max(0, min(100, int(data.get("brand_fit", 50)))),
            "ai_summary": str(data.get("summary", ""))[:300],
        }

    except Exception as e:
        logger.warning(
            "ai_analysis_failed_using_fallback",
            handle=handle,
            error=str(e),
        )
        fb = _fallback_scores(candidate)
        return {
            "content_quality": fb["content_quality"],
            "audience_quality": fb["audience_quality"],
            "brand_fit": fb["brand_fit"],
            "ai_summary": None,
        }


candidate_analyzer = CandidateAnalyzer()
