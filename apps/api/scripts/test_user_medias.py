"""Smoke: verifica el ER real end-to-end vía /v2/user/medias.

Historia (07-sep-2026): /gql/user/medias (recomendado por la spec) responde
un stream_rows NO FULFILLIDO sin posts; /v2/user/medias (REST) entrega 12
posts directos con like_count/comment_count. get_user_medias usa v2.

Este script verifica contra la API REAL que el flujo completo funciona:
enrich → get_user_medias → posts con likes reales (~2 llamadas, $0.04).

Uso:
    HIKERAPI_API_KEY=... python -m scripts.test_user_medias [username]
"""

import asyncio
import os
import sys

from discovery.tools.hikerapi_client import HikerAPIClient


async def main() -> int:
    api_key = os.getenv("HIKERAPI_API_KEY", "")
    if not api_key:
        print("ERROR: HIKERAPI_API_KEY not set.")
        return 1
    handle = sys.argv[1] if len(sys.argv) > 1 else "ecoanimalistadevenezuela"

    client = HikerAPIClient(api_key=api_key)
    print("=" * 60)
    print(f"MEDIAS END-TO-END TEST — @{handle} (vía /v2/user/medias)")
    print("=" * 60)

    profile = await client.enrich_profile(handle)
    if not profile or not profile.get("pk"):
        print(f"FAIL: no se pudo enriquecer @{handle}")
        return 1
    print(f"pk={profile['pk']} followers={profile.get('follower_count')}")

    posts = await client.get_user_medias(profile["pk"])
    if not posts:
        print("FAIL: 0 posts — pegar el log hikerapi_user_medias_unknown_shape")
        return 1

    with_likes = [p for p in posts if p["likesCount"] > 0]
    print(f"\nposts: {len(posts)} | con likes > 0: {len(with_likes)}")
    for p in posts[:5]:
        print(f"  pk={str(p['pk'])[:20]:<22} likes={p['likesCount']:<6} comments={p['commentsCount']}")

    if not with_likes:
        print("\nWARN: posts extraídos pero todos con 0 likes — revisar _post_engagement")
        return 1

    avg_likes = sum(p["likesCount"] for p in posts) / len(posts)
    followers = profile.get("follower_count") or 0
    if followers > 0:
        print(f"\nER estimado con estos posts: {(avg_likes / followers) * 100:.2f}%")
    print("\nOK — ER real aterrizado end-to-end")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
