"""Tests FIX N-1 (04-sep-2026): get_balance alineado al OpenAPI spec de HikerAPI.

El método probaba /v1/account, /v1/user/balance y /account — paths que NO
existen en el spec (https://api.hikerapi.com/openapi.json). El único endpoint
real es GET /sys/balance → {requests, rate, currency, amount}. Al fallar los
3 paths, get_balance() siempre retornaba None y el pre-flight de saldo se
omitía silenciosamente: un run con saldo $0 quemaba el discovery completo
antes de morir con 402 en enrichment.
"""

from discovery.tools.hikerapi_client import HikerAPIClient


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload or {}


class _FakeHttpClient:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.requested_paths: list[str] = []

    async def get(self, path: str):
        self.requested_paths.append(path)
        return self._response


async def _patch_client(monkeypatch, response: _FakeResponse) -> tuple[HikerAPIClient, _FakeHttpClient]:
    client = HikerAPIClient(api_key="test-key")
    fake = _FakeHttpClient(response)

    async def _fake_get_client():
        return fake

    monkeypatch.setattr(client, "_get_client", _fake_get_client)
    return client, fake


async def test_get_balance_uses_sys_balance_path(monkeypatch):
    """Guard de regresión N-1: el path debe ser /sys/balance (el único real)."""
    client, fake = await _patch_client(
        monkeypatch,
        _FakeResponse(200, {"requests": 129627, "rate": 11, "currency": "USD", "amount": 25.5777}),
    )
    balance = await client.get_balance()
    assert balance == 25.5777
    assert fake.requested_paths == ["/sys/balance"]


async def test_get_balance_parses_amount_field(monkeypatch):
    """El campo del spec es `amount` (dinero restante en USD)."""
    client, _ = await _patch_client(
        monkeypatch,
        _FakeResponse(200, {"requests": 100, "rate": 11, "currency": "USD", "amount": 35.14}),
    )
    assert await client.get_balance() == 35.14


async def test_get_balance_zero_returns_zero_not_none(monkeypatch):
    """Saldo $0 debe retornar 0.0 (no None) para que el pre-flight aborte."""
    client, _ = await _patch_client(
        monkeypatch,
        _FakeResponse(200, {"requests": 0, "rate": 11, "currency": "USD", "amount": 0}),
    )
    assert await client.get_balance() == 0.0


async def test_get_balance_non_200_returns_none(monkeypatch):
    client, _ = await _patch_client(monkeypatch, _FakeResponse(503, {"error": "unavailable"}))
    assert await client.get_balance() is None


async def test_get_balance_missing_amount_returns_none(monkeypatch):
    """Respuesta 200 sin campo `amount` → None (pre-flight omitido, no crash)."""
    client, _ = await _patch_client(monkeypatch, _FakeResponse(200, {"status": "ok"}))
    assert await client.get_balance() is None


async def test_get_balance_never_raises(monkeypatch):
    """Si la red falla, get_balance retorna None — el pre-flight se omite,
    el run continúa y el 402 real lo aborta después (comportamiento hito 23)."""

    class _ExplodingClient:
        async def get(self, path: str):
            raise ConnectionError("network down")

    client = HikerAPIClient(api_key="test-key")

    async def _fake_get_client():
        return _ExplodingClient()

    monkeypatch.setattr(client, "_get_client", _fake_get_client)
    assert await client.get_balance() is None
