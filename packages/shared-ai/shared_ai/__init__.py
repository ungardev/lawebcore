"""Shared AI clients: DeepSeek client, OpenAI wrappers, embeddings."""

from shared_ai.deepseek_client import DeepSeekClient, LLMResponse, deepseek_client
from shared_ai.embeddings import chunk_text, embed_text, embed_texts

__all__ = [
    "DeepSeekClient",
    "LLMResponse",
    "deepseek_client",
    "embed_text",
    "embed_texts",
    "chunk_text",
]
