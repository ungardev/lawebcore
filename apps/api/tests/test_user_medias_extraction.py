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
