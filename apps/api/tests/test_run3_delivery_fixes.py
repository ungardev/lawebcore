"""Tests del batch RUN 3 (07-sep-2026): entrega + ER real + keywords inteligentes.

Incidente: run 75855ad1 llegó al ÚLTIMO paso (3 candidatos calificados con
brand_fit del análisis IA) y murió en el INSERT — la columna discovery_query
no existía en producción (migración 111 jamás aplicada manualmente). Además:
ER persistido como 0.0 en vez de NULL, following/posts_count enriquecidos
tapados por zeros camelCase, y la cuenta de la PROPIA marca entregada como
"creador".
"""

from pathlib import Path

_REPO = Path("apps/api/app/workers/worker.py")
_CLIENT = Path("packages/discovery/discovery/tools/hikerapi_client.py")
_MEMORY = Path("packages/discovery/discovery/memory.py")
_PROMPT = Path("packages/discovery/discovery/profile_generator.py")


class TestExtractorXdtShape:
    def _client(self):
        from discovery.tools.hikerapi_client import HikerAPIClient

        return HikerAPIClient(api_key="test-key")

    def test_xdt_modern_shape(self):
        """La forma MODERNA del GraphQL de IG: data.xdt_api__v1__feed__user_timeline_graphql_connection."""
        resp = {
            "data": {
                "xdt_api__v1__feed__user_timeline_graphql_connection": {
                    "edges": [
                        {"node": {"pk": 1, "like_count": 50, "comment_count": 3}},
                        {"node": {"pk": 2, "like_count": 60, "comment_count": 4}},
                    ]
                }
            }
        }
        posts = self._client()._extract_posts(resp)
        assert [p["pk"] for p in posts] == [1, 2]

    def test_xdt_shape_under_user(self):
        resp = {
            "data": {
                "user": {
                    "xdt_api__v1__feed__user_timeline_graphql_connection": {
                        "edges": [{"node": {"pk": 9, "like_count": 5}}]
                    }
                }
            }
        }
        posts = self._client()._extract_posts(resp)
        assert len(posts) == 1

    async def test_get_user_medias_handles_xdt(self, monkeypatch):
        client = self._client()

        async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
            return {
                "data": {
                    "xdt_api__v1__feed__user_timeline_graphql_connection": {
                        "edges": [{"node": {"pk": 77, "like_count": 120, "comment_count": 8}}]
                    }
                }
            }

        monkeypatch.setattr(client, "_get", _fake_get)
        posts = await client.get_user_medias("123")
        assert posts[0]["likesCount"] == 120


class TestBrandOwnExclusion:
    def test_purina_dog_chow_tokens(self):
        from app.workers.worker import _brand_tokens

        tokens = _brand_tokens("Purina Dog Chow", None)
        assert "purina" in tokens
        assert "dogchow" in tokens, "bigram consecutivo — matchea @dogchowve"
        assert "purinadog" in tokens

    def test_chow_breed_creator_not_excluded(self):
        """'chow' solo NO es token (falso positivo: razas Chow Chow reales)."""
        from app.workers.worker import _brand_tokens

        tokens = _brand_tokens("Purina Dog Chow", None)
        assert "chow" not in tokens
        assert "dog" not in tokens
        handle = "chowchowlover_ve"
        assert not any(tok in handle for tok in tokens)

    def test_brand_own_handle_matches(self):
        from app.workers.worker import _brand_tokens

        tokens = _brand_tokens("Purina Dog Chow", None)
        assert any(tok in "dogchowve" for tok in tokens)
        assert any(tok in "purina.venezuela.oficial" for tok in tokens)

    def test_empty_sources(self):
        from app.workers.worker import _brand_tokens

        assert _brand_tokens(None, None) == set()


class TestNullNotZeroInCandidates:
    def test_engagement_rate_none_without_posts(self):
        """Guard NULL≠0: sin posts el ER persistido debe ser None, no 0.0."""
        src = _REPO.read_text(encoding="utf-8")
        assert '"engagement_rate": round(er, 6) if has_engagement_data else None' in src, (
            "el dict de candidatos persiste ER=0.0 cuando no hay posts — "
            "el analista lee 'sin engagement' como dato medido (NULL≠0)."
        )

    def test_enriched_following_not_shadowed_by_camelcase_zero(self):
        src = _REPO.read_text(encoding="utf-8")
        assert 'p.get("following_count") if p.get("following_count") is not None else p.get("followsCount")' in src
        assert 'p.get("posts_count") if p.get("posts_count") is not None else p.get("postsCount")' in src

    def test_rationale_handles_none_er(self):
        from discovery.tools.geo_boost import build_rationale

        out = build_rationale({"biography": "dog mom caracas"}, "MICRO", 12000, None)
        assert "sin datos" in out
        assert "ER 0.0%" not in out
        out2 = build_rationale({"biography": "dog mom"}, "MICRO", 12000, 0.045)
        assert "ER 4.5%" in out2


class TestTruthfulInsertFailureMessage:
    def test_worker_has_insert_failure_branch(self):
        src = _REPO.read_text(encoding="utf-8")
        assert "total == 0 and qualified_count > 0" in src, (
            "cuando hay candidatos calificados pero el INSERT falla, el chat "
            "debe decir 'falló el guardado' — no 'ninguno califica' (run "
            "75855ad1 mostró ambos mensajes en contradicción)."
        )


class TestKeywordIntelligenceV2:
    def test_prompt_generates_creator_identity_keywords(self):
        prompt = _PROMPT.read_text(encoding="utf-8")
        assert "IDENTIDAD DE CREADOR" in prompt
        assert "PROHIBIDO" in prompt
        assert "frases de compra de producto" in prompt
        assert "NUNCA incluyas el país ni ciudades dentro de las keywords" in prompt

    def test_prompt_includes_additional_context(self):
        prompt = _PROMPT.read_text(encoding="utf-8")
        assert "CONTEXTO ADICIONAL DEL CLIENTE" in prompt
        assert "additional_context" in prompt

    def test_migration_ensures_discovery_query_column(self):
        """F1: la migración auto-aplicada debe garantizar la columna que el
        worker emite — sin ella TODO insert de candidatos falla."""
        memory_src = _MEMORY.read_text(encoding="utf-8")
        assert "discovery_candidates ADD COLUMN IF NOT EXISTS" in memory_src
        assert '("discovery_query", "TEXT DEFAULT \'\'")' in memory_src
        assert '("brand_fit", "INTEGER")' in memory_src
        main_src = Path("apps/api/app/main.py").read_text(encoding="utf-8")
        assert "migrate_discovery_conversations_schema" in main_src, (
            "la migración debe correr en el lifespan de la API (auto-aplicada)"
        )
