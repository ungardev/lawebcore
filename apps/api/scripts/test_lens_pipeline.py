"""
Lens pipeline validation script — tests HikerAPI endpoints that power the discovery pipeline.

Run from Railway shell:
    cd /app/apps/api
    python -m scripts.test_lens_pipeline

Tests:
1. keyword search (fixed with search_surface param)
2. search_top_accounts (new /v3/fbsearch/topsearch endpoint)
3. suggested_profiles (new /v2/user/suggested/profiles endpoint)
4. hashtag search (baseline)

Cost: ~$0.50 total
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from discovery.tools.hikerapi_client import hikerapi_client


async def test_keyword_search() -> dict:
    print("\n" + "=" * 60)
    print("[TEST 1] Keyword Search — search_keyword()")
    print("=" * 60)

    tests = [
        ("mascotas venezuela", 20),
        ("purina dog chow", 15),
        ("perrosvzla", 15),
        ("comida para perros", 10),
    ]

    total_ok = 0
    for keyword, limit in tests:
        try:
            results = await hikerapi_client.search_keyword(keyword, limit=limit)
            ve_results = [r for r in results if r.get("country") == "VE" or r.get("follower_count", 0) > 0]
            print(f"  '{keyword}' -> {len(results)} users, {len(ve_results)} with data")
            for r in results[:2]:
                print(f"    @{r.get('username'):<25} followers={r.get('follower_count', 0):>10,} country={r.get('country','')}")
            total_ok += 1
        except Exception as e:
            print(f"  ERROR on '{keyword}': {e}")

    return {"ok": total_ok == len(tests), "tested": len(tests), "passed": total_ok}


async def test_top_accounts() -> dict:
    print("\n" + "=" * 60)
    print("[TEST 2] Top Accounts — search_top_accounts()")
    print("=" * 60)

    tests = [
        ("mascotas venezuela", 10),
        ("purina venezuela", 8),
        ("perrosvzla", 5),
    ]

    total_ok = 0
    for query, limit in tests:
        try:
            results = await hikerapi_client.search_top_accounts(query, limit=limit)
            print(f"  '{query}' -> {len(results)} top accounts")
            for r in results[:3]:
                print(f"    @{r.get('username'):<25} followers={r.get('follower_count', 0):>10,} country={r.get('country','')}")
            total_ok += 1
        except Exception as e:
            print(f"  ERROR on '{query}': {e}")

    return {"ok": total_ok == len(tests), "tested": len(tests), "passed": total_ok}


async def test_suggested_profiles() -> dict:
    print("\n" + "=" * 60)
    print("[TEST 3] Suggested Profiles — suggested_profiles()")
    print("=" * 60)

    seeds = ["mascotasvzla", "chefnestorsanchez", "meridaven"]
    total_ok = 0

    for seed in seeds:
        try:
            results = await hikerapi_client.suggested_profiles(seed, limit=10)
            print(f"  Seed @{seed} -> {len(results)} suggested profiles")
            for r in results[:3]:
                print(f"    @{r.get('username'):<25} followers={r.get('follower_count', 0):>10,} country={r.get('country','')}")
            total_ok += 1
        except Exception as e:
            print(f"  ERROR on @{seed}: {e}")

    return {"ok": total_ok == len(seeds), "tested": len(seeds), "passed": total_ok}


async def test_hashtag_baseline() -> dict:
    print("\n" + "=" * 60)
    print("[TEST 4] Hashtag Baseline — search_hashtag()")
    print("=" * 60)

    hashtags = ["mascotasvzla", "perrosvzla"]
    total_ok = 0

    for tag in hashtags:
        try:
            results = await hikerapi_client.search_hashtag(tag, limit=20)
            handles = set(r.get("username") for r in results if r.get("username"))
            print(f"  #{tag} -> {len(results)} posts, {len(handles)} unique handles")
            for r in list(results)[:2]:
                print(f"    @{r.get('username'):<25} followers={r.get('follower_count', 0):>10,} country={r.get('country','')}")
            total_ok += 1
        except Exception as e:
            print(f"  ERROR on #{tag}: {e}")

    return {"ok": total_ok == len(hashtags), "tested": len(hashtags), "passed": total_ok}


async def main() -> int:
    print("=" * 60)
    print("LENS PIPELINE VALIDATION — HikerAPI Endpoints")
    print("=" * 60)

    results = {}

    results["keyword_search"] = await test_keyword_search()
    results["top_accounts"] = await test_top_accounts()
    results["suggested_profiles"] = await test_suggested_profiles()
    results["hashtag_baseline"] = await test_hashtag_baseline()

    await hikerapi_client.close()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_ok = True
    for name, r in results.items():
        status = "PASS" if r["ok"] else "FAIL"
        if not r["ok"]:
            all_ok = False
        print(f"  [{status}] {name}: {r['passed']}/{r['tested']} passed")

    print()
    if all_ok:
        print("  ALL TESTS PASSED — pipeline is ready for full run")
    else:
        print("  SOME TESTS FAILED — review logs above")

    print("=" * 60)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
