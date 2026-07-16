#!/usr/bin/env python3
"""Local test script to verify Apify client works directly.

Usage:
    APIFY_API_KEY=your_key python3 test_apify_local.py

This bypasses Railway entirely to isolate whether the issue is:
1. The Apify token (wrong/invalid)
2. The hashtag query (no results for #fitnessvenezuela)
3. The Apify actor (not accessible)
"""
import asyncio
import os
import sys

sys.path.insert(0, "apps/api")

from app.discovery.tools.apify_client import ApifyClient


async def test_apify():
    token = os.environ.get("APIFY_API_KEY", "")
    print(f"Token: {token[:12]}..." if token else "NO TOKEN PROVIDED")

    if not token:
        print("ERROR: Set APIFY_API_KEY env var")
        sys.exit(1)

    client = ApifyClient(token=token)

    print("\n=== Test 1: Instagram hashtag search ===")
    print("Hashtag: #fitnessvenezuela, country: VE, min_followers: 1000")

    try:
        results = await client.search_instagram_by_hashtag(
            hashtag="#fitnessvenezuela",
            country="VE",
            min_followers=1000,
            max_followers=10_000_000,
        )
        print(f"Results count: {len(results)}")
        if results:
            print(f"First result keys: {list(results[0].keys())}")
            print(f"First result username: {results[0].get('username', 'N/A')}")
            print(f"First result followers: {results[0].get('followersCount', 'N/A')}")
        else:
            print("WARNING: 0 results returned")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== Test 2: Instagram hashtag search (#fitness) ===")
    try:
        results = await client.search_instagram_by_hashtag(
            hashtag="#fitness",
            country="VE",
            min_followers=1000,
            max_followers=10_000_000,
        )
        print(f"Results count: {len(results)}")
        if results:
            print(f"First result username: {results[0].get('username', 'N/A')}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(test_apify())
