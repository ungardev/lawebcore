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

# Status codes que SÍ vale la pena reintentar. Los 4xx determinísticos
# (401 auth, 400 bad request) fallan igual en el intento 2 y 3: fail-fast.
# FIX D-4 (04-sep-2026): antes se reintentaba CUALQUIER excepción 3 veces.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    finish_reason: str | None = None


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
        self._client: Any = None

    def _get_client(self) -> Any:
        # FIX D-3 (04-sep-2026): cliente cacheado — antes se construía un
        # ChatOpenAI nuevo (y un httpx client nuevo) EN CADA llamada, sin
        # reuso de conexiones. El singleton del módulo ahora comparte uno.
        if self._client is None:
            from langchain_openai import ChatOpenAI

            # HITO 36 — MODO THINKING EXPLÍCITAMENTE DESACTIVADO.
            #
            # `deepseek-v4-flash` trae el modo thinking ACTIVADO por defecto, con
            # effort=high (docs: api-docs.deepseek.com/guides/thinking_mode).
            # Eso cambia tres cosas respecto de `deepseek-chat`, y ninguna avisa:
            #
            #   1. `temperature` se ignora. La doc lo dice literal: "setting these
            #      parameters will not trigger an error but will also have no effect".
            #   2. El chain-of-thought se factura como tokens de salida
            #      ($0.66-1.32 / 1M) en CADA llamada.
            #   3. `max_tokens` tiene que cubrir razonamiento + respuesta. Con
            #      max_tokens=2500 y effort=high, el JSON puede truncarse.
            #
            # Para parseo de brief y scoring queremos salida estructurada, barata y
            # reproducible: no razonamiento. Si algún día una tarea se beneficia del
            # thinking, se activa en ESA llamada, no globalmente.
            self._client = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                api_key=self.api_key,
                base_url="https://api.deepseek.com",
                extra_body={
                    "cache": {"mode": "enabled"},
                    "thinking": {"type": "disabled"},
                },
            )
        return self._client

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        status_code = getattr(error, "status_code", None)
        if status_code is not None:
            return status_code in _RETRYABLE_STATUS_CODES
        # Sin status_code (conexión, timeout, parseo) → potencialmente
        # transitorio: reintentable.
        return True

    async def _call_with_retry(self, client: Any, messages: list[dict], **kwargs) -> LLMResponse:
        last_error: Exception | None = None
        attempts_made = 0
        for attempt in range(self.max_retries):
            attempts_made = attempt + 1
            try:
                start = time.perf_counter()
                # FIX D-3: ainvoke nativo — sin to_thread, sin bloquear un hilo
                # del pool por llamada.
                response = await client.ainvoke(messages, **kwargs)
                latency_ms = int((time.perf_counter() - start) * 1000)
                content = response.content if hasattr(response, "content") else str(response)
                usage_meta = getattr(response, "usage_metadata", {}) or {}
                tokens_input = usage_meta.get("input_tokens")
                tokens_output = usage_meta.get("output_tokens")
                tokens_used = usage_meta.get("total_tokens") or (
                    (tokens_input + tokens_output) if (tokens_input and tokens_output) else None
                )
                finish_reason = (getattr(response, "response_metadata", {}) or {}).get("finish_reason")
                cost_usd = None
                if tokens_input is not None and tokens_output is not None:
                    # DeepSeek-V4-Flash peak pricing (2026-08): $0.44/1M input, $1.32/1M output
                    cost_usd = (tokens_input * 0.44 / 1_000_000) + (tokens_output * 1.32 / 1_000_000)
                return LLMResponse(
                    content=content,
                    model=self.model,
                    tokens_used=tokens_used,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    finish_reason=finish_reason,
                )
            except Exception as e:
                last_error = e
                if not self._is_retryable(e):
                    logger.error(
                        "llm_call_not_retryable",
                        attempt=attempts_made,
                        error=str(e),
                        error_type=type(e).__name__,
                        status_code=getattr(e, "status_code", None),
                    )
                    break
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
        raise RuntimeError(f"LLM call failed after {attempts_made} attempt(s): {last_error}")

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        response_format: dict | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> LLMResponse:
        """Text completion via DeepSeek.

        history: turnos previos [{"role": "user"|"assistant", "content": ...}]
        insertados entre el system y el prompt (FIX R-1: el RAG necesita
        multi-turno coherente — antes el historial se construía y se tiraba).
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        for msg in history or []:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})

        client = self._get_client()
        kwargs: dict[str, Any] = {"temperature": temperature, "max_tokens": max_tokens}
        if response_format:
            kwargs["response_format"] = response_format
        result = await self._call_with_retry(client, messages, **kwargs)

        # FIX D-5 (04-sep-2026): salida truncada por max_tokens → un solo
        # reintento con el doble. Antes un JSON truncado moría en el parser
        # (y complete_json lo "arreglaba" appendeando '"}', lo que casi nunca
        # produce JSON válido).
        if result.finish_reason == "length":
            logger.warning(
                "llm_response_truncated_retrying",
                model=self.model,
                max_tokens=max_tokens,
                retry_max_tokens=max_tokens * 2,
            )
            kwargs["max_tokens"] = max_tokens * 2
            result = await self._call_with_retry(client, messages, **kwargs)

        logger.info(
            "llm_call",
            provider="deepseek",
            model=self.model,
            latency_ms=result.latency_ms,
            tokens=result.tokens_used,
            finish_reason=result.finish_reason,
        )
        return result

    async def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Completion parsed as JSON with markdown stripping."""
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

        result = await self.complete(
            prompt, system,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        cleaned = _strip_markdown(result.content)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        extracted = _extract_json(result.content)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass

        logger.error("llm_json_parse_error", content=result.content[:500], error="failed after retries")
        raise ValueError(f"LLM response is not valid JSON: {result.content[:200]}")


deepseek_client = DeepSeekClient()
