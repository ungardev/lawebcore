"""Tests FIX 07-sep (Run 5, 4c3c6cc8): HTTP 403 = per-recurso, no fatal.

Un 403 de HikerAPI ("PrivateAccount") es una condición del RECURSO (ese
usuario es privado), no de la fuente completa. Antes se lanzaba
SourceUnavailable → TODO el run moría por UNA cuenta privada entre 25.
Ahora: log + None → el caller saltea y continúa. 401/402 siguen fatales.
"""

from pathlib import Path

from discovery.tools.hikerapi_client import HikerAPIClient

_WORKER_SRC = Path("packages/discovery/discovery/tools/hikerapi_client.py").read_text(encoding="utf-8")


class Test403PrivateAccount:
    def test_403_vs_401_semantics(self):
        """403 = per-recurso (skip); 401 = global (fatal). El código debe
        distinguirlos."""
        assert "hikerapi_forbidden_skipping" in _WORKER_SRC, (
            "403 debe loguearse como skip, no como auth_error fatal"
        )
        # 401/402 siguen agrupados juntos pero SIN 403:
        assert "in (401, 402):" in _WORKER_SRC, "401/402 deben seguir fatales"
        assert "(401, 402, 403)" not in _WORKER_SRC, "403 NO debe estar agrupado con 401/402"


class TestEnrichProfile403:
    async def test_enrich_profile_403_returns_none(self, monkeypatch):
        """enrich_profile de una cuenta privada → None (no crash, no raise)."""
        client = HikerAPIClient(api_key="test-key")

        async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
            return None  # 403 ahora retorna None desde _get

        monkeypatch.setattr(client, "_get", _fake_get)
        result = await client.enrich_profile("cuenta_privada")
        assert result is None

    async def test_get_user_medias_403_returns_empty(self, monkeypatch):
        """medias de una cuenta privada → [] (no crash)."""
        client = HikerAPIClient(api_key="test-key")

        async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
            return None  # 403 → None

        monkeypatch.setattr(client, "_get", _fake_get)
        posts = await client.get_user_medias("12345")
        assert posts == []

    async def test_get_user_about_403_returns_none(self, monkeypatch):
        """about de una cuenta privada → None (no crash)."""
        client = HikerAPIClient(api_key="test-key")

        async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
            return None

        monkeypatch.setattr(client, "_get", _fake_get)
        about = await client.get_user_about("12345")
        assert about is None
