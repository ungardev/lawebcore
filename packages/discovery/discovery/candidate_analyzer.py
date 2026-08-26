"""CandidateAnalyzer — DeepSeek-powered AI analysis of discovery candidates.

Adds three new scored fields per candidate:
  - content_quality: 0-100 (production quality, niche coherence)
  - audience_quality: 0-100 (authenticity signals, bot detection)
  - brand_fit: 0-100 (alignment with campaign brief)

Plus an AI-generated rationale replacing the regex-based build_rationale().

OPTIMIZATION: Batches up to BATCH_SIZE candidates per LLM call to reduce
DeepSeek API calls from ~50 to ~5 per discovery run.

ELITE INTEGRATION: Uses profile_data.elite_data to provide:
  - content_themes: para evaluar si el contenido del candidato es relevante
  - credibility_signals: para scoring de audience_quality
  - niche_benchmarks: para ajustar umbrales de scoring
  - local_slang y competitor_intel: para brand_fit scoring
"""

import asyncio
import json as _json
import structlog
from typing import Any

from shared_ai.deepseek_client import deepseek_client

logger = structlog.get_logger(__name__)

MAX_CONCURRENT_BATCHES = 5
BATCH_SIZE = 10


SYSTEM_PROMPT = """Eres un analista senior de influencer marketing con 15 años de experiencia en Latam.
Tu tarea es analizar perfiles de Instagram y devolver puntuaciones objetivas de 0 a 100 para cada uno.

REGLAS POR CADA CAMPO:
- content_quality: Evalúa producción visual, variedad de contenido, coherencia con los content_themes de la campaña.
  90-100 = alta producción, contenido alineado con el nicho, formato diverso (Reels + Posts + Stories).
  70-89 = buena producción, contenido presente y coherente.
  50-69 = producción media, contenido genérico o inconsistente.
  30-49 = baja producción, contenido repetitivo o sin nicho claro.
  0-29 = cuenta casi vacía o sin contenido relevante.

- audience_quality: Evalúa señales de audiencia real vs bots/farm usando credibility_signals.
  90-100 = múltiples señales de credibilidad, engagement orgánico consistente, comentarios genuinos.
  70-89 = cuenta real con engagement normal, algunas señales de credibilidad.
  50-69 = señales mixtas, posible uso de grupos de engagement.
  30-49 = patrones sospechosos de bots o engagement farm.
  0-29 = alta probabilidad de bots/farm — cuenta inauténtica.

- brand_fit: Alineación total con la campaña — evalúa nicho, tono, audiencia y señales de competencia.
  90-100 = perfil totalmente alineado: contenido + tono + audiencia perfectos para la campaña.
  70-89 = buena alineación con la campaña, la mayoría de elementos en foco.
  50-69 = alineación parcial, algunos elementos fuera de foco.
  30-49 = alineación débil, contenido o audiencia no ideal.
  0-29 = perfil no relevante para esta campaña.

- summary: Frase breve en español explicando el reasoning (2-3 oraciones). Explica por qué scoring así.

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
    elite_data: dict[str, Any] | None = None,
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

    elite_context = ""
    if elite_data:
        content_themes = elite_data.get("content_themes", [])
        credibility_signals = elite_data.get("credibility_signals", [])
        local_slang = elite_data.get("local_slang", [])
        competitor_brands = elite_data.get("competitor_intel", {}).get("brands", [])
        benchmarks = elite_data.get("niche_benchmarks", {})

        content_themes_str = ", ".join(content_themes[:6]) if content_themes else "no especificados"
        credibility_str = ", ".join(credibility_signals[:5]) if credibility_signals else "no especificados"
        local_slang_str = ", ".join(local_slang[:5]) if local_slang else "ninguno"
        competitor_str = ", ".join(competitor_brands[:5]) if competitor_brands else "ninguna"
        min_er = benchmarks.get("min_er", 0.035)
        target_er = benchmarks.get("target_er", 0.055)
        min_followers = benchmarks.get("min_followers", 5000)

        elite_context = f"""
CONTEXTO ELITE DE LA CAMPAÑA:
- Content themes winners: {content_themes_str}
- Señales de credibilidad a buscar: {credibility_str}
- Slang local a identificar: {local_slang_str}
- Competidores en el nicho: {competitor_str}
- Benchmarks: min_followers={min_followers:,}, min_er={min_er:.1%}, target_er={target_er:.1%}"""

    return f"""@{handle} | {followers:,} seguidores | {industry_str} en {country}
BIO: {bio_preview}
CAPTIONS: {caption_text}
NICHO: {niches_str}
TONO: {tone_str}{elite_context}"""


def _build_batch_prompt(
    candidates: list[dict[str, Any]],
    industry: str | None,
    niches: list[str],
    tone: list[str],
    country: str,
    elite_data: dict[str, Any] | None = None,
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

    elite_section = ""
    if elite_data:
        content_themes = elite_data.get("content_themes", [])
        credibility_signals = elite_data.get("credibility_signals", [])
        competitor_intel = elite_data.get("competitor_intel", {})
        benchmarks = elite_data.get("niche_benchmarks", {})
        local_slang = elite_data.get("local_slang", [])

        content_themes_str = ", ".join(content_themes[:8]) if content_themes else "no especificados"
        credibility_str = "\n  - ".join(credibility_signals[:8]) if credibility_signals else "no especificados"
        competitor_str = ", ".join(competitor_intel.get("brands", [])[:6]) if competitor_intel.get("brands") else "ninguna"
        competitor_hashtags = ", ".join(competitor_intel.get("hashtags", [])[:6]) if competitor_intel.get("hashtags") else "ninguno"
        slang_str = ", ".join(local_slang[:8]) if local_slang else "ninguno"
        min_er = benchmarks.get("min_er", 0.035)
        target_er = benchmarks.get("target_er", 0.055)
        min_followers = benchmarks.get("min_followers", 5000)
        ideal_range = benchmarks.get("ideal_follower_range", "5k-150k")

        elite_section = f"""

CONTEXTO ELITE DE LA CAMPAÑA (usa esto para evaluar content_quality, audience_quality y brand_fit):
  Content themes winners: {content_themes_str}
  Benchmarks del nicho: min_followers={min_followers:,}, ideal_range={ideal_range}, min_er={min_er:.1%}, target_er={target_er:.1%}
  Señales de credibilidad (busca estas en bio/posts): {credibility_str}
  Slang local (identifica si lo usa): {slang_str}
  Competidores en el nicho: {competitor_str}
  Hashtags de competidores: {competitor_hashtags}"""

    return f"""Analiza los siguientes {len(candidates)} influencers para campaña de {industry or 'productos de consumo'} en {country}.
Evalúa usando el contexto elite de abajo si está disponible.{elite_section}

PERFILES:
{candidates_text}

Responde con un JSON array, un objeto por cada handle en orden:
[
  {{"handle": "handle1", "content_quality": 0-100, "audience_quality": 0-100, "brand_fit": 0-100, "summary": "razonamiento en español"}},
  ...
]"""


def _parse_batch_response(content: str) -> list[dict[str, Any]]:
    """Parse LLM response as JSON. Uses response_format=json_object from the caller."""
    import re
    content = content.strip()
    try:
        data = _json.loads(content)
    except _json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in response: {content[:200]}")
    if "scores" in data and isinstance(data["scores"], list):
        return data["scores"]
    if isinstance(data, list):
        return data
    raise ValueError(f"Expected scores array in response, got: {type(data)}")


def _fallback_scores(candidate: dict[str, Any], elite_data: dict[str, Any] | None = None) -> dict[str, Any]:
    followers = candidate.get("followers", 0) or 0
    er = candidate.get("engagement_rate") or 0

    benchmarks = {}
    if elite_data and isinstance(elite_data, dict):
        benchmarks = elite_data.get("niche_benchmarks", {})

    min_followers = benchmarks.get("min_followers", 5000) if benchmarks else 5000
    min_er = benchmarks.get("min_er", 0.035) if benchmarks else 0.035

    if followers >= 100_000:
        content_quality = 78
    elif followers >= 20_000:
        content_quality = 68
    elif followers >= min_followers:
        content_quality = 60
    else:
        content_quality = 45

    if er > 0.10:
        audience_quality = 82
    elif er > min_er:
        audience_quality = 68
    elif er > 0.01:
        audience_quality = 50
    else:
        audience_quality = 30

    bio = (candidate.get("bio") or candidate.get("biography") or "").lower()

    niche_keywords = [
        "mascota", "pet", "dog", "perro", "gato", "cat", "belleza", "moda", "fitness",
        "tecnologia", "comida", "viajes", "lifestyle", "negocios",
        "moda", "ropa", "zapato", "cosmetico", "skincare", "makeup",
        "fitness", "gym", "ejercicio", "salud", "alimentacion",
        "tecnologia", "tech", "software", "app", "digital",
        "comida", "receta", "gastronomia", "chef", "restaurante",
        "viajes", "turismo", "hotel", "destino", "vuelo",
        "lifestyle", "familia", "hogar", "casa", "decoracion",
        "negocios", "emprendimiento", "empresa", "startup", "marketing",
    ]

    if elite_data and isinstance(elite_data, dict):
        extra_niches = elite_data.get("niche_keywords", [])
        if extra_niches:
            niche_keywords.extend([str(n).lower() for n in extra_niches[:20]])

    has_niche = any(k in bio for k in niche_keywords)
    brand_fit = 78 if has_niche else 52

    return {
        "content_quality": content_quality,
        "audience_quality": audience_quality,
        "brand_fit": brand_fit,
        "ai_summary": "",
        "is_fallback": True,
    }


class CandidateAnalyzer:
    def __init__(self):
        self._client = None

    async def analyze_candidates_batch(
        self,
        candidates: list[dict[str, Any]],
        brief: Any,
        profile_data: dict[str, Any],
        cost_callback: Any = None,
    ) -> list[dict[str, Any]]:
        """Analyze candidates with DeepSeek using batching.

        Batches up to BATCH_SIZE candidates per LLM call to reduce
        API calls from N to N/BATCH_SIZE.

        Uses profile_data.elite_data to provide campaign-specific context
        for scoring (content_themes, credibility_signals, niche_benchmarks, etc).

        Args:
            cost_callback: if provided, called with (cost_usd, tokens_input, tokens_output)
                           after each successful LLM call.
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

        elite_data = None
        if profile_data and isinstance(profile_data, dict):
            elite_data = profile_data.get("elite_data")

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
                prompt = _build_batch_prompt(
                    batch_candidates,
                    industry,
                    niches,
                    tone,
                    country,
                    elite_data,
                )

                batch_results: list[tuple[int, dict[str, Any]]] = []
                try:
                    result = await deepseek_client.complete(
                        prompt=prompt,
                        system=SYSTEM_PROMPT,
                        temperature=0.2,
                        max_tokens=2500,
                        response_format={"type": "json_object"},
                    )
                    if cost_callback and result.cost_usd is not None:
                        cost_callback(
                            result.cost_usd,
                            result.tokens_input or 0,
                            result.tokens_output or 0,
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
                            batch_results.append((idx, scores))
                        else:
                            fb = _fallback_scores(candidate, elite_data)
                            batch_results.append((idx, fb))

                except Exception as e:
                    logger.warning(
                        "ai_batch_analysis_failed_using_fallback",
                        batch_size=len(batch_candidates),
                        error=str(e),
                    )
                    for idx, candidate in indexed_candidates:
                        fb = _fallback_scores(candidate, elite_data)
                        batch_results.append((idx, fb))

                return batch_results

        tasks = [_process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks)
        results: list[tuple[int, dict[str, Any]]] = []
        for batch_result in batch_results:
            results.extend(batch_result)

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
                fb = _fallback_scores(candidate, elite_data)
                candidate["content_quality"] = fb["content_quality"]
                candidate["audience_quality"] = fb["audience_quality"]
                candidate["brand_fit"] = fb["brand_fit"]

        return candidates


candidate_analyzer = CandidateAnalyzer()
