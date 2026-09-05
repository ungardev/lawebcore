"""
Embeddings — fastembed (local, no API cost).

Uses sentence-transformers/all-MiniLM-L6-v2 (384 dimensions).
No OpenAI or external API required.
"""

from typing import Any

import structlog

from shared_core.config import settings

logger = structlog.get_logger(__name__)

_model: Any = None


def _get_model() -> Any:
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _model


async def embed_text(text: str) -> list[float]:
    """Embed a single string using fastembed (384-dim)."""
    try:
        model = _get_model()
        result = list(model.embed([text]))
        return result[0].tolist()
    except Exception as e:
        logger.error("embedding_failed", error=str(e))
        raise


async def embed_texts(texts: list[str]) -> list[list[float] | None]:
    """
    Embed multiple strings in a single batch request using fastembed.
    Returns list of 384-dim vectors, or None for strings that failed.

    FIX R-2 (04-sep-2026): antes el fallback producía [0.0]*384 — vectores
    cero insertados en document_chunks como filas muertas que contaban como
    embebidas pero jamás matcheaban. Ahora el fallo se propaga como None y
    el indexador salta ese chunk.
    """
    if not texts:
        return []

    try:
        model = _get_model()
        results = list(model.embed(texts))
        return [r.tolist() for r in results]
    except Exception as e:
        logger.warning("batch_embedding_failed", error=str(e))
        results: list[list[float] | None] = []
        for text in texts:
            try:
                vec = await embed_text(text)
                results.append(vec)
            except Exception:
                logger.warning("embedding_failed_skipping_chunk", text_preview=text[:80])
                results.append(None)
        return results


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks of approximately chunk_size chars."""
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", " "]:
                last = text[start:end].rfind(sep)
                if last > chunk_size // 2:
                    end = start + last + len(sep)
                    break
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]
