"""
DeepSeek client wrapper with retry, fallback to OpenAI, and structured output.

Used by sentiment_analyzer.py for batch comment classification.
"""

import time
from dataclasses import dataclass
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int | None = None
    latency_ms: int | None = None


class DeepSeekClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float = 0.1,
        max_retries: int = 3,
    ):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.model = model or settings.DEEPSEEK_MODEL
        self.temperature = temperature
        self.max_retries = max_retries
        self._active_provider: str | None = None

    def _build_openai_client(self) -> Any:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
        )

    def _build_deepseek_client(self) -> Any:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
            base_url="https://api.deepseek.com",
        )

    def _call_with_retry(self, client: Any, messages: list[dict], **kwargs) -> LLMResponse:
        import time
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                start = time.perf_counter()
                response = client.invoke(messages)
                latency_ms = int((time.perf_counter() - start) * 1000)
                content = response.content if hasattr(response, "content") else str(response)
                tokens = getattr(response, "usage_metadata", {}).get("total_tokens", None) if hasattr(response, "usage_metadata") else None
                return LLMResponse(
                    content=content,
                    model=self.model,
                    tokens_used=tokens,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning(
                    "llm_retry",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                    wait_s=wait,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(wait)
        raise RuntimeError(f"LLM call failed after {self.max_retries} attempts: {last_error}")

    def complete(self, prompt: str, system: str | None = None) -> LLMResponse:
        """
        Simple text completion. Falls back to OpenAI if DeepSeek is unavailable.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        if self.api_key and settings.DEFAULT_LLM_PROVIDER == "deepseek":
            try:
                client = self._build_deepseek_client()
                self._active_provider = "deepseek"
                result = self._call_with_retry(client, messages)
                logger.info(
                    "llm_call",
                    provider="deepseek",
                    model=self.model,
                    latency_ms=result.latency_ms,
                    tokens=result.tokens_used,
                )
                return result
            except Exception as e:
                logger.warning("deepseek_unavailable_fallback", error=str(e))

        if settings.OPENAI_API_KEY:
            client = self._build_openai_client()
            self._active_provider = "openai"
            result = self._call_with_retry(client, messages)
            logger.info(
                "llm_call",
                provider="openai",
                model=self.model,
                latency_ms=result.latency_ms,
                tokens=result.tokens_used,
            )
            return result

        raise RuntimeError("No LLM provider available (DeepSeek and OpenAI keys missing)")

    def complete_json(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        """
        Completion parsed as JSON. Useful for structured sentiment responses.
        """
        result = self.complete(prompt, system)
        import json
        try:
            return json.loads(result.content)
        except json.JSONDecodeError as e:
            logger.error("llm_json_parse_error", content=result.content[:200], error=str(e))
            raise ValueError(f"LLM response is not valid JSON: {result.content[:200]}")


deepseek_client = DeepSeekClient()
