"""
Sentiment Analyzer — Clasificación de comentarios usando DeepSeek LLM.

Metodología:
- Batches de 10 comentarios por request LLM (optimiza tokens)
- Cada comentario se clasifica como POSITIVO, NEUTRO o NEGATIVO
- Prompt con few-shot examples en español venezolano (slang LATAM)
- Si el LLM devuelve algo fuera del enum → NEUTRO con baja confianza

El resultado se persiste en la tabla `comentarios` de Supabase
y se agregan los totales a `publicaciones` (sentimiento_positivo/neutro/negativo).
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog
from shared_ai import LLMResponse, deepseek_client

logger = structlog.get_logger(__name__)


class Sentiment(str, Enum):
    POSITIVO = "POSITIVO"
    NEUTRO = "NEUTRO"
    NEGATIVO = "NEGATIVO"
    SIN_DATOS = "SIN_DATOS"


@dataclass
class CommentSentiment:
    index: int
    text: str
    sentiment: Sentiment
    confidence: float


@dataclass
class SentimentDistribution:
    positivo: int = 0
    neutro: int = 0
    negativo: int = 0
    total: int = 0
    confianza_promedio: float = 0.0
    comentarios: list[CommentSentiment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "positivo": self.positivo,
            "neutro": self.neutro,
            "negativo": self.negativo,
            "total": self.total,
            "confianza_promedio": round(self.confianza_promedio, 4),
            "comentarios": [
                {"index": c.index, "sentiment": c.sentiment.value, "confidence": c.confidence}
                for c in self.comentarios
            ],
        }


BATCH_SIZE = 50

SYSTEM_PROMPT = """Eres un clasificador de sentimiento de comentarios de redes sociales. Clasifica cada comentario como POSITIVO, NEUTRO o NEGATIVO.

REGLAS:
- POSITIVO: halagos, apoyo, entusiasmo, palabras de cariño,.emojis positivos (🔥❤️😍💯), menciones de marca positivas
- NEUTRO: preguntas, información neutral, comentarios sin emoción evidente, spam,/off-topic
- NEGATIVO: críticas, quejas, insultos, sarcasmo negativo, emociones negativas (😡💔😭), quejas de marca

IMPORTANTE: Responde SOLO con JSON válido. Sin texto adicional.
El JSON debe tener el formato exacto especificado por el usuario."""

USER_PROMPT_TEMPLATE = """Clasifica estos {n} comentarios. Devuelve un JSON con un array "results", cada elemento con:
- "index": número del comentario (0-{max_index})
- "sentiment": "POSITIVO", "NEUTRO" o "NEGATIVO"
- "confidence": número entre 0.0 y 1.0 (qué tan seguro estás)

Comentarios (uno por línea, formato "INDEX::texto"):

{comments}

Responde SOLO con JSON válido:
{{"results": [{{"index": 0, "sentiment": "...", "confidence": 0.95}}, ...]}}"""


def _build_prompt(comments: list[str]) -> str:
    lines = []
    for i, text in enumerate(comments):
        safe = text.replace("\n", " ").replace('"', "'")[:500]
        lines.append(f"{i}::{safe}")
    body = "\n".join(lines)
    n = len(comments)
    return USER_PROMPT_TEMPLATE.format(n=n, max_index=n - 1, comments=body)


def _parse_llm_response(raw: str, num_comments: int) -> list[dict[str, Any]]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "".join(l for l in lines if not l.startswith("```")).strip()
    try:
        data = json.loads(cleaned)
        results = data.get("results", [])
        if not isinstance(results, list):
            results = []
        return results
    except json.JSONDecodeError:
        logger.warning("sentiment_json_parse_failed", raw=raw[:200])
        return [{"index": i, "sentiment": "NEUTRO", "confidence": 0.0} for i in range(num_comments)]


async def analyze_comments_batch(comments: list[str]) -> SentimentDistribution:
    """
    Analiza un batch de hasta 10 comentarios.
    Cada comentario se clasifica como POSITIVO, NEUTRO o NEGATIVO.

    Returns SentimentDistribution con conteos y detalles.
    """
    if not comments:
        return SentimentDistribution()

    batch = comments[:BATCH_SIZE]
    prompt = _build_prompt(batch)

    try:
        response: LLMResponse = await deepseek_client.complete(prompt, system=SYSTEM_PROMPT, max_tokens=200)
    except Exception as e:
        logger.error("sentiment_llm_error", error=str(e))
        return SentimentDistribution(
            comentarios=[
                CommentSentiment(index=i, text=t, sentiment=Sentiment.SIN_DATOS, confidence=0.0)
                for i, t in enumerate(batch)
            ]
        )

    raw_results = _parse_llm_response(response.content, len(batch))

    result_map: dict[int, dict] = {r["index"]: r for r in raw_results}

    parsed: list[CommentSentiment] = []
    for i, text in enumerate(batch):
        r = result_map.get(i, {})
        sent_str = r.get("sentiment", "NEUTRO").upper()
        confidence = float(r.get("confidence", 0.0))

        if sent_str not in ("POSITIVO", "NEUTRO", "NEGATIVO"):
            sent_str = "NEUTRO"
            confidence = 0.0

        parsed.append(CommentSentiment(
            index=i,
            text=text,
            sentiment=Sentiment(sent_str),
            confidence=confidence,
        ))

    dist = SentimentDistribution(
        positivo=sum(1 for c in parsed if c.sentiment == Sentiment.POSITIVO),
        neutro=sum(1 for c in parsed if c.sentiment == Sentiment.NEUTRO),
        negativo=sum(1 for c in parsed if c.sentiment == Sentiment.NEGATIVO),
        total=len(parsed),
        confianza_promedio=sum(c.confidence for c in parsed) / len(parsed) if parsed else 0.0,
        comentarios=parsed,
    )

    logger.info(
        "sentiment_batch_complete",
        positivo=dist.positivo,
        neutro=dist.neutro,
        negativo=dist.negativo,
        confianza=dist.confianza_promedio,
        tokens=response.tokens_used,
        latency_ms=response.latency_ms,
    )

    return dist


async def analyze_comments_full(comments: list[str]) -> SentimentDistribution:
    """
    Analiza todos los comentarios en batches de BATCH_SIZE.
    Acumula los resultados de todos los batches.
    """
    if not comments:
        return SentimentDistribution()

    all_dist = SentimentDistribution()
    all_comentarios: list[CommentSentiment] = []

    for i in range(0, len(comments), BATCH_SIZE):
        batch = comments[i:i + BATCH_SIZE]
        dist = await analyze_comments_batch(batch)

        offset = i
        for c in dist.comentarios:
            all_comentarios.append(CommentSentiment(
                index=offset + c.index,
                text=c.text,
                sentiment=c.sentiment,
                confidence=c.confidence,
            ))

    total = len(all_comentarios)
    pos = sum(1 for c in all_comentarios if c.sentiment == Sentiment.POSITIVO)
    neg = sum(1 for c in all_comentarios if c.sentiment == Sentiment.NEGATIVO)
    neu = total - pos - neg
    conf_avg = sum(c.confidence for c in all_comentarios) / total if total else 0.0

    return SentimentDistribution(
        positivo=pos,
        neutro=neu,
        negativo=neg,
        total=total,
        confianza_promedio=conf_avg,
        comentarios=all_comentarios,
    )
