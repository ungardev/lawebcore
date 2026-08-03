"""
DeepSeek client — chat completions via OpenAI-compatible API.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import structlog

from shared_core.config import settings

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

    def _build_client(self) -> Any:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
            base_url="https://api.deepseek.com",
            extra_body={"cache": {"mode": "enabled"}},
        )

    async def _call_with_retry(self, client: Any, messages: list[dict], **kwargs) -> LLMResponse:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                start = time.perf_counter()
                response = await asyncio.to_thread(client.invoke, messages, **kwargs)
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
                    await asyncio.sleep(wait)
        raise RuntimeError(f"LLM call failed after {self.max_retries} attempts: {last_error}")

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Text completion via DeepSeek."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        client = self._build_client()
        result = await self._call_with_retry(client, messages, temperature=temperature, max_tokens=max_tokens)
        logger.info(
            "llm_call",
            provider="deepseek",
            model=self.model,
            latency_ms=result.latency_ms,
            tokens=result.tokens_used,
        )
        return result

    async def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Completion parsed as JSON with markdown stripping and retry."""
        import json
        import re

        def _strip_markdown(text: str) -> str:
            text = text.strip()
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            return text.strip()

        def _extract_json(text: str) -> str | None:
            match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
            if match:
                return match.group(1)
            return None

        result = await self.complete(prompt, system, temperature=temperature, max_tokens=max_tokens)
        content = result.content

        for attempt in range(3):
            try:
                cleaned = _strip_markdown(content)
                return json.loads(cleaned)
            except json.JSONDecodeError:
                if attempt == 0:
                    extracted = _extract_json(content)
                    if extracted:
                        try:
                            return json.loads(extracted)
                        except json.JSONDecodeError:
                            pass
                logger.warning(
                    "llm_json_parse_retry",
                    attempt=attempt + 1,
                    content_preview=content[:200],
                )
                if attempt < 2:
                    content = content + '"}'
        logger.error("llm_json_parse_error", content=result.content[:500], error="failed after retries")
        raise ValueError(f"LLM response is not valid JSON: {result.content[:200]}")


deepseek_client = DeepSeekClient()
