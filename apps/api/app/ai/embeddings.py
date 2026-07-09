"""Embeddings: chunk text, embed with OpenAI, store in pgvector."""

from typing import Any

import structlog

from app.core.config import settings

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


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks of approximately chunk_size chars."""
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to break on a paragraph or sentence boundary
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", " "]:
                last = text[start:end].rfind(sep)
                if last > chunk_size // 2:
                    end = start + last + len(sep)
                    break
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]