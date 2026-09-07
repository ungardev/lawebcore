"""Tests FIX N-3 (04-sep-2026): extracción de posts para ER real.

/v2/user/by/username NO devuelve posts (latestPosts: 0 ocurrencias en el
OpenAPI spec). get_user_medias() via /gql/user/medias trae los posts con su
engagement; los extractores son type-agnostic porque el payload GraphQL puede
venir en varias formas. Sin estos posts, el 38.9% del Lens Score
(tier_normalized_er) queda en 0 para todos los candidatos.
"""

from discovery.tools.hikerapi_client import HikerAPIClient

_CLIENT = HikerAPIClient(api_key="test-key")


class TestExtractPosts:
    def test_edges_shape_data_user(self):
        resp = {
            "data": {
                "user": {
                    "edge_owner_to_timeline_media": {
                        "edges": [
                            {"node": {"pk": 1, "like_count": 10}},
                            {"node": {"pk": 2, "like_count": 20}},
                        ]
                    }
                }
            }
        }
        posts = _CLIENT._extract_posts(resp)
        assert [p["pk"] for p in posts] == [1, 2]

    def test_edges_shape_without_data_wrapper(self):
        resp = {
            "user": {
                "edge_owner_to_timeline_media": {
                    "edges": [{"node": {"pk": 7, "like_count": 1}}]
                }
            }
        }
        posts = _CLIENT._extract_posts(resp)
        assert len(posts) == 1
        assert posts[0]["pk"] == 7

    def test_flat_items_shape(self):
        resp = {"items": [{"pk": 1}, {"pk": 2}, "no-dict"]}
        posts = _CLIENT._extract_posts(resp)
        assert [p["pk"] for p in posts] == [1, 2]

    def test_garbage_returns_empty_not_crash(self):
        for garbage in ({}, {"data": None}, {"data": {"user": None}}, "not-a-dict", None):
            assert _CLIENT._extract_posts(garbage) == []

    def test_unknown_structure_returns_empty(self):
        resp = {"data": {"user": {"edge_owner_to_timeline_media": "corrupt"}}}
        assert _CLIENT._extract_posts(resp) == []

    def test_stream_rows_shape_observed_in_production(self):
        """Forma EXACTA observada en Railway 07-sep (script test_user_medias):
        /gql/user/medias responde {stream_rows: [{data: {clave-variable}}]}.
        La clave del timeline es VARIABLE (variables embebidas en el nombre)."""
        resp = {
            "stream_rows": [
                {
                    "data": {
                        "__typename": "Query",
                        "1$xdt_api__v1__profile_timeline(_request_data:{\"count\":12})": {
                            "xdt_api__v1__feed__user_timeline_graphql_connection": {
                                "edges": [
                                    {"node": {"pk": 101, "like_count": 200, "comment_count": 15}},
                                    {"node": {"pk": 102, "like_count": 180, "comment_count": 12}},
                                ]
                            }
                        },
                    }
                }
            ]
        }
        posts = _CLIENT._extract_posts(resp)
        assert [p["pk"] for p in posts] == [101, 102]

    def test_stream_rows_connection_nested_deeper(self):
        """La conexión anidada más adentro de la clave variable también se encuentra."""
        resp = {
            "stream_rows": [
                {
                    "data": {
                        "1$xdt_api__v1__profile_timeline(...)": {
                            "nested_wrapper": {
                                "xdt_api__v1__feed__user_timeline_graphql_connection": {
                                    "edges": [{"node": {"pk": 5, "like_count": 9}}]
                                }
                            }
                        }
                    }
                }
            ]
        }
        posts = _CLIENT._extract_posts(resp)
        assert [p["pk"] for p in posts] == [5]

    async def test_get_user_medias_with_stream_rows_end_to_end(self, monkeypatch):
        """End-to-end con la forma real: likes/comments normalizados para el ER."""
        client = HikerAPIClient(api_key="test-key")

        async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
            return {
                "stream_rows": [
                    {
                        "data": {
                            "1$xdt_api__v1__profile_timeline(...)": {
                                "xdt_api__v1__feed__user_timeline_graphql_connection": {
                                    "edges": [
                                        {"node": {"pk": 1, "like_count": 300, "comment_count": 20}},
                                    ]
                                }
                            }
                        }
                    }
                ]
            }

        monkeypatch.setattr(client, "_get", _fake_get)
        posts = await client.get_user_medias("555")
        assert posts[0]["likesCount"] == 300
        assert posts[0]["commentsCount"] == 20


class TestPostEngagement:
    def test_rest_style_counts(self):
        likes, comments = _CLIENT._post_engagement({"like_count": 120, "comment_count": 8})
        assert (likes, comments) == (120, 8)

    def test_graphql_edge_fallback(self):
        likes, comments = _CLIENT._post_engagement(
            {
                "edge_liked_by": {"count": 55},
                "edge_media_to_comment": {"count": 4},
            }
        )
        assert (likes, comments) == (55, 4)

    def test_preview_like_fallback(self):
        likes, _ = _CLIENT._post_engagement({"edge_media_preview_like": {"count": 33}})
        assert likes == 33

    def test_garbage_returns_zeros(self):
        likes, comments = _CLIENT._post_engagement(
            {"like_count": "many", "edge_liked_by": "corrupt"}
        )
        assert (likes, comments) == (0, 0)


async def test_get_user_medias_normalizes_posts(monkeypatch):
    """get_user_medias normaliza a {pk, likesCount, commentsCount, taken_at} —
    el contrato que worker.py consume para calcular ER real."""
    client = HikerAPIClient(api_key="test-key")
    payload = {
        "data": {
            "user": {
                "edge_owner_to_timeline_media": {
                    "edges": [
                        {"node": {"pk": 1, "like_count": 100, "comment_count": 10}},
                        {"node": {"pk": 2, "like_count": 50, "comment_count": 5}},
                        {"node": {"pk": 3}},
                    ]
                }
            }
        }
    }

    async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
        assert path == "/gql/user/medias"
        assert params["user_id"] == "12345"
        return payload

    monkeypatch.setattr(client, "_get", _fake_get)
    posts = await client.get_user_medias("12345")

    assert len(posts) == 3
    assert posts[0] == {"pk": 1, "likesCount": 100, "commentsCount": 10, "taken_at": None}
    assert posts[1]["likesCount"] == 50
    assert posts[2]["likesCount"] == 0  # post sin engagement → 0, no crash


async def test_get_user_medias_caps_by_count(monkeypatch):
    client = HikerAPIClient(api_key="test-key")
    payload = {"items": [{"pk": i, "like_count": 1} for i in range(30)]}

    async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
        return payload

    monkeypatch.setattr(client, "_get", _fake_get)
    posts = await client.get_user_medias("99", count=12)
    assert len(posts) == 12


async def test_get_user_medias_empty_response(monkeypatch):
    client = HikerAPIClient(api_key="test-key")

    async def _fake_get(path, params=None, cache_ttl=0, run_id=None, budget_fuse=None):
        return None

    monkeypatch.setattr(client, "_get", _fake_get)
    assert await client.get_user_medias("1") == []
