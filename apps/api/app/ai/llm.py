"""LLM provider abstraction - OpenAI and Anthropic support."""

from langchain_core.language_models.chat_models import BaseChatModel

from shared_core import settings


def get_llm(provider: str | None = None, temperature: float = 0.7) -> BaseChatModel:
    """Returns a LangChain chat model for the configured provider."""
    provider = provider or settings.DEFAULT_LLM_PROVIDER

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.DEFAULT_LLM_MODEL,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=temperature,
            api_key=settings.ANTHROPIC_API_KEY,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")