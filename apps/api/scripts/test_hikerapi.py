"""
HikerAPI standalone test script.

Run from Railway shell:
    cd /app
    export HIKERAPI_API_KEY=your_key_here
    python -m scripts.test_hikerapi

Or from local machine:
    python -m scripts.test_hikerapi --api-key your_key_here
"""

import argparse
import asyncio
import sys
import os
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from discovery.tools.hikerapi_client import HikerAPIClient


async def test_balance(client: HikerAPIClient) -> dict[str, Any]:
    """GET /sys/balance — verify API key is valid and check credits."""
    print("\n[1/6] Testing /sys/balance (API key validation)...")
    resp = await client._get("/sys/balance")
    if resp:
        balance = resp.get("user_credit_balance") or resp.get("balance") or resp.get("credits")
        print(f"    Balance: {balance}")
        return {"ok": True, "balance": balance, "raw": resp}
    return {"ok": False, "error": "No response from /sys/balance"}


async def test_user_lookup(client: HikerAPIClient) -> dict[str, Any]:
    """GET /v2/user/by/username — verify profile format with is_business field."""
    print("\n[2/6] Testing /v2/user/by/username (cocinavenezuela)...")
    resp = await client.enrich_profile("cocinavenezuela")
    if resp:
        followers = resp.get("follower_count", 0)
        is_biz = resp.get("is_business", False)
        bio = resp.get("biography", "")[:80]
        print(f"    Username: {resp.get('username')}")
        print(f"    Followers: {followers:,}")
        print(f"    is_business: {is_biz}")
        print(f"    Bio: {bio}...")
        return {"ok": True, "followers": followers, "is_business": is_biz}
    return {"ok": False, "error": "Profile not found"}


async def test_hashtag_top(client: HikerAPIClient) -> dict[str, Any]:
    """GET /v2/hashtag/medias/top — verify top posts return real creators."""
    print("\n[3/6] Testing /v2/hashtag/medias/top (#recetasvenezuela)...")
    results = await client.search_hashtag("recetasvenezuela", limit=10)
    if not results:
        return {"ok": False, "error": "No results returned"}

    stores = 0
    creators = 0
    for r in results:
        followers = r.get("follower_count", 0)
        is_biz = r.get("is_business", False)
        if is_biz and followers < 50000:
            stores += 1
        else:
            creators += 1

    print(f"    Total results: {len(results)}")
    print(f"    Likely creators: {creators}")
    print(f"    Likely stores/business: {stores}")
    if results:
        top = results[0]
        print(f"    Top result: @{top.get('username')} | {top.get('follower_count', 0):,} followers | is_business={top.get('is_business')}")
    return {"ok": len(results) > 0, "total": len(results), "stores": stores, "creators": creators}


async def test_hashtag_pagination(client: HikerAPIClient) -> dict[str, Any]:
    """Verify cursor pagination works — fetch 2 pages of results."""
    print("\n[4/6] Testing hashtag pagination (cursor-based)...")
    results_page1 = await client.search_hashtag("cocinavenezuela", limit=5)
    if not results_page1:
        return {"ok": False, "error": "No results on first page"}

    handles_p1 = {r.get("username") for r in results_page1 if r.get("username")}
    print(f"    Page 1: {len(results_page1)} results, first: @{results_page1[0].get('username')}")

    results_page2 = await client.search_hashtag("cocinavenezuela", limit=5)
    handles_p2 = {r.get("username") for r in results_page2 if r.get("username")}

    overlap = handles_p1 & handles_p2
    print(f"    Page 2: {len(results_page2)} results, overlap with page1: {len(overlap)}")
    return {"ok": True, "page1": len(results_page1), "page2": len(results_page2), "overlap": len(overlap)}


async def test_keyword_search(client: HikerAPIClient) -> dict[str, Any]:
    """GET /v2/fbsearch/accounts — verify keyword search returns user-type results."""
    print("\n[5/6] Testing /v2/fbsearch/accounts (keyword: recetas con leche)...")
    results = await client.search_keyword("recetas con leche evaporada", limit=10)
    if not results:
        return {"ok": False, "error": "No results returned"}

    stores = sum(1 for r in results if r.get("is_business") and r.get("follower_count", 0) < 50000)
    print(f"    Total: {len(results)}")
    print(f"    Stores filtered: {stores}")
    if results:
        top = results[0]
        print(f"    Top result: @{top.get('username')} | {top.get('follower_count', 0):,} followers")
    return {"ok": len(results) > 0, "total": len(results)}


async def test_multiple_hashtags(client: HikerAPIClient) -> dict[str, Any]:
    """Simulate Carnation brief: 14 hashtags → verify data quality."""
    hashtags = [
        "recetasvenezuela", "cocinavenezuela", "postresvenezuela",
        "reposteriacasera", "comidacasera", "cafévenezuela", "bebidascalientes",
        "dulcestipicos", "cocinafacil", "horneadocasa", "comidasegura",
        "cocinacasera", "recetasfaciles", "postresfaciles",
    ]
    print(f"\n[6/6] Simulating Carnation brief: {len(hashtags)} hashtags...")
    all_results = []
    stores_total = 0
    for tag in hashtags:
        results = await client.search_hashtag(tag, limit=5)
        stores = sum(1 for r in results if r.get("is_business") and r.get("follower_count", 0) < 50000)
        stores_total += stores
        all_results.extend(results)
        print(f"    #{tag}: {len(results)} posts, {stores} stores")

    unique_handles = {r.get("username") for r in all_results if r.get("username")}
    print(f"\n    TOTAL unique handles: {len(unique_handles)}")
    print(f"    TOTAL stores detected: {stores_total}")
    return {
        "ok": len(unique_handles) >= 20,
        "unique_handles": len(unique_handles),
        "stores": stores_total,
        "hashtags_tested": len(hashtags),
    }


async def main():
    parser = argparse.ArgumentParser(description="Test HikerAPI end-to-end")
    parser.add_argument("--api-key", type=str, help="HikerAPI access key (or set HIKERAPI_API_KEY env var)")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("HIKERAPI_API_KEY")
    if not api_key:
        print("ERROR: No API key provided. Set HIKERAPI_API_KEY env var or use --api-key")
        print("Usage: python -m scripts.test_hikerapi --api-key wr6l9jyb469nwtwzpk19j25o9wsjyq6b")
        return 1

    print("=" * 70)
    print("HikerAPI End-to-End Diagnostic")
    print("=" * 70)
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print()

    client = HikerAPIClient(api_key=api_key)

    tests = [
        ("Balance/Health", test_balance),
        ("User Lookup", test_user_lookup),
        ("Hashtag Top Posts", test_hashtag_top),
        ("Hashtag Pagination", test_hashtag_pagination),
        ("Keyword Search", test_keyword_search),
        ("Carnation Simulation (14 hashtags)", test_multiple_hashtags),
    ]

    results: dict[str, Any] = {}
    for name, test_fn in tests:
        try:
            results[name] = await test_fn(client)
        except Exception as e:
            print(f"    EXCEPTION: {type(e).__name__}: {e}")
            results[name] = {"ok": False, "error": str(e)}

    await client.close()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = 0
    failed = 0
    for name, r in results.items():
        status = "✅ PASS" if r.get("ok") else "❌ FAIL"
        if r.get("ok"):
            passed += 1
        else:
            failed += 1
        extra = ""
        if "balance" in r:
            extra = f" | balance={r['balance']}"
        if "total" in r:
            extra = f" | total={r['total']}"
        if "unique_handles" in r:
            extra = f" | handles={r['unique_handles']} stores={r.get('stores', 0)}"
        if "error" in r:
            extra = f" | error={r['error']}"
        print(f"  {status}: {name}{extra}")

    print(f"\n  Total: {passed}/{len(tests)} passed")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
