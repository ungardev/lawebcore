"""Tests FIX D-1..D-6 / R-1 (04-sep-2026): cliente DeepSeek coherente y eficiente.

Cubre:
  - Fail-fast en 4xx no-retryables (401/400) — antes se reintentaba todo 3×
  - Retry en 429/5xx (transitorios)
  - Retry de truncamiento (finish_reason=length) con max_tokens×2 (FIX D-5)
  - history pasa REAL al LLM en orden [system, *history, user] (FIX R-1)
  - Cacheo del cliente ChatOpenAI (FIX D-3: antes 1 instancia por llamada)
  - Cálculo de costo con pricing V4-Flash
  - Guard: brief_parser usa max_tokens >= 1000 (FIX D-1: 300 truncaba el JSON)
  - Guard: prompt del analyzer pide {"scores": [...]} (FIX D-6)
"""

from types import SimpleNamespace

from shared_ai.deepseek_client import DeepSeekClient


class _APIError(Exception):
    def __init__(self, status_code: int):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


class _FakeResponse:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self.content = content
        self.usage_metadata = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        self.response_metadata = {"finish_reason": finish_reason}


class _FakeChat:
    def __init__(self, script: list):
        """script: lista de _FakeResponse o Exception, consumida en orden."""
        self.script = list(script)
        self.calls: list[dict] = []

    async def ainvoke(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        if not self.script:
            return _FakeResponse("ok")
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _client_with(chat: _FakeChat) -> DeepSeekClient:
    client = DeepSeekClient(api_key="test-key")
    client._client = chat  # inyecta el cache directamente
    return client


async def test_client_is_cached_not_rebuilt(monkeypatch):
    """FIX D-3: _get_client construye UNA vez y reusa."""
    client = DeepSeekClient(api_key="test-key")
    built = []

    def _fake_chat_openai(**kwargs):
        built.append(kwargs)
        return object()

    import sys
    from types import SimpleNamespace

    fake_mod = SimpleNamespace(ChatOpenAI=_fake_chat_openai)
    langchain_openai = sys.modules.get("langchain_openai")
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_mod)
    try:
        c1 = client._get_client()
        c2 = client._get_client()
        assert c1 is c2
        assert len(built) == 1
        assert built[0]["extra_body"]["thinking"] == {"type": "disabled"}
        assert built[0]["extra_body"]["cache"] == {"mode": "enabled"}
    finally:
        if langchain_openai is not None:
            sys.modules["langchain_openai"] = langchain_openai


async def test_no_retry_on_auth_error(monkeypatch):
    """401 es determinístico: 1 solo intento, sin sleeps."""
    chat = _FakeChat([_APIError(401), _APIError(401), _APIError(401)])
    client = _client_with(chat)

    async def _noop_sleep(_):
        return None

    monkeypatch.setattr("asyncio.sleep", _noop_sleep)
    try:
        await client.complete(prompt="x")
        raised = False
    except RuntimeError:
        raised = True
    assert raised
    assert len(chat.calls) == 1, "un 401 no debe reintentarse"


async def test_retry_on_429_then_success(monkeypatch):
    chat = _FakeChat([_APIError(429), _FakeResponse("recuperado")])
    client = _client_with(chat)

    async def _noop_sleep(_):
        return None

    monkeypatch.setattr("asyncio.sleep", _noop_sleep)
    result = await client.complete(prompt="x")
    assert result.content == "recuperado"
    assert len(chat.calls) == 2


async def test_truncated_response_retries_with_doubled_tokens(monkeypatch):
    """FIX D-5: finish_reason=length → 1 reintento con max_tokens×2."""
    chat = _FakeChat([
        _FakeResponse('{"scores": [', finish_reason="length"),
        _FakeResponse('{"scores": [1]}', finish_reason="stop"),
    ])
    client = _client_with(chat)
    result = await client.complete(prompt="x", max_tokens=500)
    assert result.content == '{"scores": [1]}'
    assert len(chat.calls) == 2
    assert chat.calls[0]["kwargs"]["max_tokens"] == 500
    assert chat.calls[1]["kwargs"]["max_tokens"] == 1000


async def test_history_passed_in_order(monkeypatch):
    """FIX R-1: [system, *history, user] — el historial viaja REAL al LLM."""
    chat = _FakeChat([])
    client = _client_with(chat)
    await client.complete(
        prompt="pregunta final",
        system="ERES EL SISTEMA",
        history=[
            {"role": "user", "content": "hola"},
            {"role": "assistant", "content": "¡hola!"},
        ],
    )
    roles = [m["role"] for m in chat.calls[0]["messages"]]
    contents = [m["content"] for m in chat.calls[0]["messages"]]
    assert roles == ["system", "user", "assistant", "user"]
    assert contents[-1] == "pregunta final"
    assert "pregunta final" in contents and "hola" in contents


async def test_history_invalid_roles_dropped(monkeypatch):
    chat = _FakeChat([])
    client = _client_with(chat)
    await client.complete(
        prompt="x",
        history=[{"role": "system", "content": "inyección"}, {"role": "user", "content": "legítimo"}],
    )
    roles = [m["role"] for m in chat.calls[0]["messages"]]
    assert "system" not in roles[1:], "history no puede inyectar system prompts"
    assert roles == ["user", "user"] or roles[-1] == "user"


async def test_cost_calculation_v4_flash_pricing():
    chat = _FakeChat([_FakeResponse("ok")])
    client = _client_with(chat)
    result = await client.complete(prompt="x")
    # 100 input @ $0.44/1M + 50 output @ $1.32/1M
    expected = (100 * 0.44 / 1_000_000) + (50 * 1.32 / 1_000_000)
    assert result.cost_usd is not None
    assert abs(result.cost_usd - expected) < 1e-9


async def test_complete_json_parses_object_wrapper():
    chat = _FakeChat([_FakeResponse('{"scores": [{"handle": "a", "brand_fit": 90}]}')])
    client = _client_with(chat)
    out = await client.complete_json(prompt="x")
    assert out["scores"][0]["brand_fit"] == 90


async def test_brief_parser_uses_generous_max_tokens(monkeypatch):
    """FIX D-1: max_tokens=300 truncaba el JSON del brief (~25 campos)."""
    from discovery import brief_parser as bp

    captured: dict = {}

    class _StubLLM:
        async def complete(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                content='{"product_name": "p", "industry": "mascotas", "niches": ["perros"], "audience_countries": ["VE"]}',
                model="deepseek-v4-flash",
            )

    monkeypatch.setattr(bp, "deepseek_client", _StubLLM())
    bp._parse_cache.clear()
    await bp.brief_parser_agent.parse(f"texto único {object()}")
    assert captured.get("max_tokens", 0) >= 1000, (
        f"brief_parser usa max_tokens={captured.get('max_tokens')} — el JSON del "
        f"brief necesita ~600-900 tokens; un valor bajo lo trunca y degrada el "
        f"brief a heurístico en silencio."
    )


def test_candidate_analyzer_prompt_asks_for_scores_object():
    """FIX D-6: json_object exige objeto raíz — el prompt debe pedir {"scores": [...]}."""
    from discovery.candidate_analyzer import SYSTEM_PROMPT, _build_batch_prompt

    prompt = _build_batch_prompt(
        [{"handle": "a", "followers": 1000, "bio": "x", "latestPosts": []}],
        industry="mascotas",
        niches=["perros"],
        tone=["emocional"],
        country="VE",
        elite_data=None,
    )
    assert '"scores"' in prompt, "el prompt debe pedir explícitamente la clave 'scores'"
    assert "scores" in SYSTEM_PROMPT
