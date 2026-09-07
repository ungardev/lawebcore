"""Smoke: verifica la forma REAL de /gql/user/medias para el ER real.

El primer E2E mostró medias fetch OK pero posts_analyzed=0 en todos los
candidatos — la respuesta tiene una forma que el extractor no reconocía.
Este script imprime la estructura cruda + el resultado del extractor para
un handle real, sin quemar un run completo (~3 llamadas, $0.06).

Uso:
    HIKERAPI_API_KEY=... python -m scripts.test_user_medias [username]
"""

import asyncio
import json
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
    print(f"MEDIAS SHAPE TEST — @{handle}")
    print("=" * 60)

    profile = await client.enrich_profile(handle)
    if not profile or not profile.get("pk"):
        print(f"FAIL: no se pudo enriquecer @{handle}")
        return 1
    pk = profile["pk"]
    print(f"pk={pk} followers={profile.get('follower_count')}")

    resp = await client._get(
        "/gql/user/medias",
        params={"user_id": str(pk), "safe_int": client.SAFE_INT},
        cache_ttl=0,
    )
    if not resp:
        print("FAIL: respuesta vacía de /gql/user/medias")
        return 1

    print("\n[1/2] Estructura cruda (top-level keys + preview):")
    if isinstance(resp, dict):
        print(f"  top keys: {list(resp.keys())}")
        data = resp.get("data")
        if isinstance(data, dict):
            print(f"  data keys: {list(data.keys())}")
            user = data.get("user")
            if isinstance(user, dict):
                print(f"  data.user keys: {list(user.keys())[:15]}")
    print(f"  preview: {json.dumps(resp, default=str)[:600]}")

    print("\n[2/2] Extractor actual:")
    raw_posts = client._extract_posts(resp)
    print(f"  posts extraídos: {len(raw_posts)}")
    if raw_posts:
        likes, comments = client._post_engagement(raw_posts[0])
        print(f"  primer post: likes={likes} comments={comments}")
        print("  OK — el extractor reconoce esta forma")
        return 0
    print("  FAIL — forma NO reconocida: copiar las keys de arriba para el fix")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
