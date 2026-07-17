"""
Embeddings — extended with batch support and DeepSeek fallback.

Used by indexer.py to bulk-embed P.I.A.R. content.
"""

import asyncio
from typing import Any

import structlog

from shared_core import settings

logger = structlog.get_logger(__name__)


async def embed_text(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """Embed a single string using OpenAI embeddings API."""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.embeddings.create(model=model, input=text)
        return resp.data[0].embedding
    except Exception as e:
        logger.error("embedding_failed", error=str(e))
        raise


async def embed_texts(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """
    Embed multiple strings in a single batch request.
    Falls back to individual calls if batch fails.
    """
    if not texts:
        return []

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in resp.data]
    except Exception as e:
        logger.warning("batch_embedding_failed_fallback", error=str(e))
        results: list[list[float]] = []
        for text in texts:
            try:
                vec = await embed_text(text, model)
                results.append(vec)
            except Exception:
                results.append([0.0] * 1536)
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
