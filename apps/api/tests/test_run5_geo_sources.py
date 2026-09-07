"""Tests del batch 07-sep (tarde): topsearch plano, about date, prefilter v2.

- B1: /gql/topsearch con flat=true devuelve items PLANOS (sin wrapper .data)
  — el parser viejo buscaba row.data.__typename → todo descartado → la
  fuente topsearch devolvía 0 accounts en TODOS los runs.
- B3: /v1/user/about trae `date` (creación de cuenta), no account_age_days —
  parsearla activa el fraude por cuenta nueva (<90d → penalty 0.90).
- B4: prefilter v2 usa _post_likers_count (señal gratis de hashtags) vía
  _engagement_multiplier.
"""

from pathlib import Path

from discovery.tools.hikerapi_client import HikerAPIClient

from app.workers.worker import _engagement_multiplier

_WORKER_SRC = Path("apps/api/app/workers/worker.py").read_text(encoding="utf-8")


class TestTopsearchFlatShape:
    def _client(self):
        return HikerAPIClient(api_key="test-key")

    async def test_flat_items_shape(self, monkeypatch):
        """B1: items planos — __typename y username AL TOPE del item."""
        client = self._client()

        async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
            assert params["flat"] == "true"
            return {
                "items": [
                    {"__typename": "XDTUserDict", "username": "petlover_ve", "full_name": "Pet Lover VE", "pk": 123},
                    {"__typename": "XDTMediaDict", "username": "dogmom_ccs", "pk": 456},
                ]
            }

        monkeypatch.setattr(client, "_get", _fake_get)
        results = await client.search_top_accounts("veterinario")
        assert len(results) == 2
        assert results[0]["username"] == "petlover_ve"
        assert results[0]["_source_topsearch"] == "veterinario"

    async def test_stream_rows_shape_still_works(self, monkeypatch):
        """Retro-compat: envelope stream_rows con .data sigue soportado."""
        client = self._client()

        async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
            return {
                "stream_rows": [
                    {"data": {"__typename": "XDTUserDict", "user": {"username": "vet_ccs"}, "pk": 1}}
                ]
            }

        monkeypatch.setattr(client, "_get", _fake_get)
        results = await client.search_top_accounts("veterinario")
        assert len(results) == 1
        assert results[0]["username"] == "vet_ccs"

    async def test_empty_shape_returns_empty_not_crash(self, monkeypatch):
        client = self._client()

        async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
            return {"stream_rows": [{"data": {"__typename": "Query", "foo": "bar"}}]}

        monkeypatch.setattr(client, "_get", _fake_get)
        results = await client.search_top_accounts("x")
        assert results == []


class TestAboutDateToAccountAge:
    async def test_date_parsed_to_account_age_days(self, monkeypatch):
        """B3: el schema About trae `date` — parsearla activa el fraude
        por cuenta nueva (<90d) que hoy nunca aplicaba."""
        client = HikerAPIClient(api_key="test-key")

        async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
            return {
                "username": "cuenta_nueva_ve",
                "country": "VE",
                "date": "2026-06-15T00:00:00Z",
                "former_usernames": "viejo1,viejo2",
            }

        monkeypatch.setattr(client, "_get", _fake_get)
        about = await client.get_user_about(123)
        assert isinstance(about["account_age_days"], int)
        assert 70 <= about["account_age_days"] <= 100
        assert about["country"] == "VE"

    async def test_old_account_high_age(self, monkeypatch):
        client = HikerAPIClient(api_key="test-key")

        async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
            return {"username": "cuenta_vieja", "country": "VE", "date": "2018-01-01T00:00:00Z"}

        monkeypatch.setattr(client, "_get", _fake_get)
        about = await client.get_user_about(456)
        assert about["account_age_days"] > 2000


class TestEngagementMultiplier:
    """B4: señal gratis de likes del post que descubrió al perfil."""

    def test_viral_post_boosted(self):
        assert _engagement_multiplier(500) == 1.35

    def test_solid_post_boosted(self):
        assert _engagement_multiplier(150) == 1.15

    def test_mid_post_neutral(self):
        assert _engagement_multiplier(50) == 1.0

    def test_dead_post_penalized(self):
        assert _engagement_multiplier(10) == 0.8

    def test_none_signal_neutral(self):
        """None = fuente sin señal (keywords) — neutro, NO penaliza."""
        assert _engagement_multiplier(None) == 1.0

    def test_zero_signal_penalized(self):
        """0 = post de hashtag sin likes — señal presente y baja."""
        assert _engagement_multiplier(0) == 0.8


class TestPrefilterV2Wiring:
    def test_worker_preserves_post_likers_count(self):
        """El dict de hashtag/recent debe preservar _post_likers_count —
        antes se perdía al construir profiles y el prefilter era ciego."""
        assert _WORKER_SRC.count('"_post_likers_count": item.get("_post_likers_count", 0)') >= 2

    def test_prefilter_applies_engagement_multiplier(self):
        assert "_engagement_multiplier(p.get(" in _WORKER_SRC

    def test_multiplier_helper_defined(self):
        assert "def _engagement_multiplier(" in _WORKER_SRC


class TestKeywordIntelligenceV2Source:
    def test_prompt_v2_instructions_present(self):
        prompt_src = Path("packages/discovery/discovery/profile_generator.py").read_text(encoding="utf-8")
        assert "IDENTIDAD DE CREADOR" in prompt_src
        assert "PROHIBIDO" in prompt_src
        assert "CONTEXTO ADICIONAL DEL CLIENTE" in prompt_src

    def test_dead_hashtags_fixed(self):
        from discovery.query_builder import VE_NICHE_HASHTAGS

        food_tags = VE_NICHE_HASHTAGS.get("food", [])
        assert "cocinalatina" in food_tags, "hashtag con espacio 'cocina Latina' es muerto"
        hogar_tags = VE_NICHE_HASHTAGS.get("hogar", [])
        assert "hogarvzla" in hogar_tags, "typo 'hogartzla' es un hashtag muerto"
