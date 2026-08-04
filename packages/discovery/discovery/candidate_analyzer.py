"""CandidateAnalyzer — DeepSeek-powered AI analysis of discovery candidates.

Adds three new scored fields per candidate:
  - content_quality: 0-100 (production quality, niche coherence)
  - audience_quality: 0-100 (authenticity signals, bot detection)
  - brand_fit: 0-100 (alignment with campaign brief)

Plus an AI-generated rationale replacing the regex-based build_rationale().

OPTIMIZATION: Batches up to BATCH_SIZE candidates per LLM call to reduce
DeepSeek API calls from ~50 to ~5 per discovery run.
"""

import asyncio
import json as _json
import re
import structlog
from typing import Any

from shared_ai.deepseek_client import deepseek_client

logger = structlog.get_logger(__name__)

MAX_CONCURRENT_BATCHES = 5
BATCH_SIZE = 10


SYSTEM_PROMPT = """Eres un analista senior de influencer marketing con 15 años de experiencia en Latam.
Tu tarea es analizar perfiles de Instagram y devolver puntuaciones objetivas de 0 a 100 para cada uno.

REGLAS POR CADA CAMPO:
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

Responde SOLO con un JSON array válido, sin texto adicional.
Cada elemento del array debe tener: handle, content_quality, audience_quality, brand_fit, summary."""


def _build_single_prompt(
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

    return f"""@{handle} | {followers:,} seguidores | {industry_str} en {country}
BIO: {bio_preview}
CAPTIONS: {caption_text}
NICHO: {niches_str}
TONO: {tone_str}"""


def _build_batch_prompt(
    candidates: list[dict[str, Any]],
    industry: str | None,
    niches: list[str],
    tone: list[str],
    country: str,
) -> str:
    blocks = []
    for i, c in enumerate(candidates):
        handle = c.get("handle", f"unknown_{i}")
        followers = c.get("followers") or 0
        bio = c.get("bio") or c.get("biography") or ""
        latest_posts = c.get("latestPosts") or c.get("raw_payload", {}).get("latestPosts") or []
        block = _build_single_prompt(handle, followers, bio, latest_posts, industry, niches, tone, country)
        blocks.append(f"[{i}] {block}")

    candidates_text = "\n\n".join(blocks)

    return f"""Analiza los siguientes {len(candidates)} influencers para campaña de {industry or 'productos de consumo'} en {country}.

PERFILES:
{candidates_text}

Responde con un JSON array, un objeto por cada handle en orden:
[
  {{"handle": "handle1", "content_quality": 0-100, "audience_quality": 0-100, "brand_fit": 0-100, "summary": "razonamiento"}},
  ...
]"""


def _parse_batch_response(content: str) -> list[dict[str, Any]]:
    content = content.strip()
    match = re.search(r"\[[\s\S]*\]", content, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array found in response: {content[:200]}")
    data = _json.loads(match.group())
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got: {type(data)}")
    return data


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
    niche_keywords = [
        "mascota", "pet", "dog", "perro", "belleza", "moda", "fitness",
        "tecnologia", "comida", "viajes", "lifestyle", "negocios",
        "moda", "ropa", "zapato", "cosmetico", "skincare", "makeup",
        "fitness", "gym", "ejercicio", "salud", "alimentacion",
        "tecnologia", "tech", "software", "app", "digital",
        "comida", "receta", "gastronomia", "chef", "restaurante",
        "viajes", "turismo", "hotel", "destino", "vuelo",
        "lifestyle", "familia", "hogar", "casa", "decoracion",
        "negocios", "emprendimiento", "empresa", "startup", "marketing",
    ]
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
        """Analyze candidates with DeepSeek using batching.

        Batches up to BATCH_SIZE candidates per LLM call to reduce
        API calls from N to N/BATCH_SIZE.
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

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

        batches: list[list[tuple[int, dict[str, Any]]]] = []
        for i in range(0, len(candidates), BATCH_SIZE):
            batch_candidates = candidates[i : i + BATCH_SIZE]
            indexed = [(i + j, c) for j, c in enumerate(batch_candidates)]
            batches.append(indexed)

        async def _process_batch(
            indexed_candidates: list[tuple[int, dict[str, Any]]],
        ) -> list[tuple[int, dict[str, Any]]]:
            async with semaphore:
                batch_candidates = [c for _, c in indexed_candidates]
                prompt = _build_batch_prompt(batch_candidates, industry, niches, tone, country)

                try:
                    result = await deepseek_client.complete(
                        prompt=prompt,
                        system=SYSTEM_PROMPT,
                        temperature=0.2,
                        max_tokens=2000,
                    )
                    parsed = _parse_batch_response(result.content)

                    handle_to_scores: dict[str, dict[str, Any]] = {}
                    for item in parsed:
                        h = item.get("handle", "")
                        if h:
                            handle_to_scores[h] = {
                                "content_quality": max(0, min(100, int(item.get("content_quality", 50)))),
                                "audience_quality": max(0, min(100, int(item.get("audience_quality", 50)))),
                                "brand_fit": max(0, min(100, int(item.get("brand_fit", 50)))),
                                "ai_summary": str(item.get("summary", ""))[:300],
                            }

                    for idx, candidate in indexed_candidates:
                        handle = candidate.get("handle", "")
                        scores = handle_to_scores.get(handle)
                        if scores:
                            yield idx, scores
                        else:
                            fb = _fallback_scores(candidate)
                            yield idx, fb

                except Exception as e:
                    logger.warning(
                        "ai_batch_analysis_failed_using_fallback",
                        batch_size=len(batch_candidates),
                        error=str(e),
                    )
                    for idx, candidate in indexed_candidates:
                        fb = _fallback_scores(candidate)
                        yield idx, fb

        results: list[tuple[int, dict[str, Any]]] = []
        for batch in batches:
            async for result in _process_batch(batch):
                results.append(result)

        results.sort(key=lambda x: x[0])

        enriched_by_index: dict[int, dict[str, Any]] = {idx: scores for idx, scores in results}

        for i, candidate in enumerate(candidates):
            analysis = enriched_by_index.get(i)
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

    prompt = _build_single_prompt(handle, followers, bio, latest_posts, industry, niches, tone, country)

    try:
        result = await deepseek_client.complete(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=300,
        )

        content = result.content.strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in response: {content[:200]}")

        data = _json.loads(match.group())

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
