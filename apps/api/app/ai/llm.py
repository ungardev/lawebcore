"""DeepSeek LLM via OpenAI-compatible API."""

from langchain_openai import ChatOpenAI
from shared_core import settings


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """Returns a DeepSeek chat model via OpenAI-compatible API."""
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        temperature=temperature,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )
