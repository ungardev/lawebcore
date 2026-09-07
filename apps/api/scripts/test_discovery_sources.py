"""Smoke: verifica topsearch / reels / suggested contra la API REAL.

Las tres fuentes devolvían 0 en todos los runs (formas no reconocidas —
misma clase de bug que /gql/user/medias). Este script llama los 3 endpoints
con un seed/keyword real e imprime la estructura cruda para diagnosticar
(~8 llamadas, $0.16).

Uso:
    HIKERAPI_API_KEY=... python -m scripts.test_discovery_sources [seed] [keyword]
"""

import asyncio
import json
import os
import sys

from discovery.tools.hikerapi_client import HikerAPIClient


def _tree(obj, depth=0):
    if depth > 5:
        return
    pad = "  " * depth
    if isinstance(obj, dict):
        for k, v in obj.items():
            extra = f" (len={len(v)})" if isinstance(v, (list, dict)) else f" = {str(v)[:40]}"
            print(f"{pad}- {str(k)[:80]} : {type(v).__name__}{extra}")
            if isinstance(v, (dict, list)) and depth < 4:
                _tree(v, depth + 1)
    elif isinstance(obj, list) and obj:
        print(f"{pad}[list len={len(obj)}] primer item:")
        _tree(obj[0], depth + 1)


async def main() -> int:
    api_key = os.getenv("HIKERAPI_API_KEY", "")
    if not api_key:
        print("ERROR: HIKERAPI_API_KEY not set.")
        return 1
    seed = sys.argv[1] if len(sys.argv) > 1 else "ecoanimalistadevenezuela"
    keyword = sys.argv[2] if len(sys.argv) > 2 else "veterinario"

    client = HikerAPIClient(api_key=api_key)
    print("=" * 60)
    print(f"DISCOVERY SOURCES TEST — seed=@{seed} kw='{keyword}'")
    print("=" * 60)

    print("\n[A] topsearch (flat=true) — antes devolvía 0 accounts")
    top = await client.search_top_accounts(keyword, limit=10)
    print(f"  search_top_accounts -> {len(top)} resultados")
    if not top:
        raw = await client.gql_topsearch(keyword, flat=True)
        print("  raw keys:", list(raw.keys()) if isinstance(raw, dict) else type(raw))
        print("  preview:", json.dumps(raw, default=str)[:1200])

    print("\n[B] reels (v2/fbsearch/reels) — antes devolvía 0 creators")
    reels = await client.search_reels_by_keyword(keyword)
    modules = reels.get("reels_serp_modules", []) if isinstance(reels, dict) else []
    print(f"  reels_serp_modules: {len(modules)} módulos")
    if modules:
        _tree(modules[0], 2)
    else:
        print("  raw keys:", list(reels.keys()) if isinstance(reels, dict) else type(reels))
        print("  preview:", json.dumps(reels, default=str)[:800])

    print("\n[C] suggested profiles (de un seed VE) — antes devolvía 0")
    profile = await client.enrich_profile(seed)
    if not profile or not profile.get("pk"):
        print(f"  FAIL: no se pudo enriquecer @{seed}")
        return 1
    suggested = await client.suggested_profiles(seed, limit=10)
    print(f"  suggested_profiles -> {len(suggested)} resultados")
    for s in suggested[:5]:
        print(f"    - @{s.get('username')} ({s.get('follower_count')} followers)")

    ok = len(top) > 0 and len(suggested) > 0
    print("\n" + ("OK — fuentes activas" if ok else "REVISAR: pegar los previews de arriba"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
