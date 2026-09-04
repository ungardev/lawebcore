"""
HikerAPI standalone test script.

Run from Railway shell:
    cd /app
    export HIKERAPI_API_KEY=your_key_here
    python -m scripts.test_hikerapi

Or from local machine:
    python -m scripts.test_hikerapi --api-key your_key_here

With raw mode (print full JSON responses before field extraction):
    python -m scripts.test_hikerapi --api-key your_key_here --raw
"""

import argparse
import asyncio
import json
import sys
import os
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from discovery.tools.hikerapi_client import HikerAPIClient


async def test_balance(client: HikerAPIClient, raw: bool = False) -> dict[str, Any]:
    print("\n[1/6] Testing /sys/balance (API key validation)...")
    resp, status = await client._get_debug("/sys/balance")
    if raw:
        print(f"    RAW ({status}): {json.dumps(resp, indent=4, default=str)}")
    if resp:
        balance = (
            resp.get("requests")
            or resp.get("user_credit_balance")
            or resp.get("balance")
            or resp.get("credits")
        )
        print(f"    Balance: {balance}")
        return {"ok": True, "balance": balance, "raw": resp}
    return {"ok": False, "error": "No response from /sys/balance"}


async def test_user_lookup(client: HikerAPIClient, raw: bool = False) -> dict[str, Any]:
    print("\n[2/6] Testing /v2/user/by/username (instagram)...")
    username = "instagram"
    resp, status = await client._get_debug("/v2/user/by/username", params={"username": username})
    if raw:
        print(f"    RAW ({status}): {json.dumps(resp, indent=4, default=str)[:2000]}")
    if resp:
        user = resp.get("user") or resp
        followers = user.get("follower_count", 0)
        is_biz = user.get("is_business", False)
        bio = user.get("biography", "")[:80]
        print(f"    Username: {user.get('username')}")
        print(f"    Followers: {followers:,}")
        print(f"    is_business: {is_biz}")
        print(f"    Bio: {bio}...")
        return {"ok": True, "followers": followers, "is_business": is_biz}
    return {"ok": False, "error": "Profile not found"}


async def test_hashtag_info(client: HikerAPIClient, raw: bool = False) -> dict[str, Any]:
    print("\n[3/6] Testing /v2/hashtag/by/name (recetasvenezuela)...")
    hashtag = "recetasvenezuela"
    resp, status = await client._get_debug("/v2/hashtag/by/name", params={"name": hashtag})
    if raw:
        print(f"    RAW ({status}): {json.dumps(resp, indent=4, default=str)[:2000]}")
    if resp:
        print(f"    Hashtag ID: {resp.get('id')}")
        print(f"    Media count: {resp.get('media_count')}")
        return {"ok": True, "hashtag_id": resp.get("id"), "media_count": resp.get("media_count")}
    return {"ok": False, "error": "Hashtag not found"}


async def test_hashtag_top(client: HikerAPIClient, raw: bool = False) -> dict[str, Any]:
    print("\n[4/6] Testing /v2/hashtag/medias/top (#recetasvenezuela)...")
    hashtag = "recetasvenezuela"
    resp, status = await client._get_debug("/v2/hashtag/medias/top", params={"name": hashtag})
    if raw:
        print(f"    RAW ({status}): {json.dumps(resp, indent=4, default=str)[:3000]}")
    if not resp:
        return {"ok": False, "error": "No response from /v2/hashtag/medias/top"}

    raw_items = client._extract_media_items(resp)
    print(f"    Top-level keys: {list(resp.keys())}")
    print(f"    Extracted media items: {len(raw_items)}")
    print(f"    'next_page_id': {resp.get('next_page_id')}")

    if raw_items:
        first_post = raw_items[0]
        print(f"    First post keys: {list(first_post.keys())}")
        user = first_post.get("user") if isinstance(first_post, dict) else None
        if not user:
            caption = first_post.get("caption", {})
            if isinstance(caption, dict):
                user = caption.get("user")
        print(f"    First post username: @{user.get('username') if user else 'N/A'}, followers: {user.get('follower_count', 0) if user else 0:,}")

    return {"ok": len(raw_items) > 0, "items": len(raw_items)}


async def test_keyword_search(client: HikerAPIClient, raw: bool = False) -> dict[str, Any]:
    print("\n[5/6] Testing /v2/fbsearch/accounts (keyword: recetas con leche)...")
    keyword = "recetas con leche evaporada"
    resp, status = await client._get_debug("/v2/fbsearch/accounts", params={"query": keyword, "rank_token": "discovery_pipeline"})
    if raw:
        print(f"    RAW ({status}): {json.dumps(resp, indent=4, default=str)[:3000]}")
    if not resp:
        return {"ok": False, "error": "No response from /v2/fbsearch/accounts"}

    raw_users = resp.get("users", [])
    print(f"    Top-level keys: {list(resp.keys())}")
    print(f"    'users' field count: {len(raw_users)}")
    print(f"    'page_token': {resp.get('page_token')}")
    print(f"    'has_more': {resp.get('has_more')}")

    if raw_users:
        first_user = raw_users[0].get("user") or raw_users[0]
        print(f"    First user: @{first_user.get('username')}, followers: {first_user.get('follower_count', 0):,}")

    return {"ok": len(raw_users) > 0, "users": len(raw_users)}


async def test_hashtag_pagination(client: HikerAPIClient, raw: bool = False) -> dict[str, Any]:
    print("\n[6/6] Testing hashtag pagination (cursor-based)...")
    hashtag = "cocinavenezuela"
    print(f"    Fetching page 1...")
    resp1, _ = await client._get_debug("/v2/hashtag/medias/top", params={"name": hashtag})
    if raw and resp1:
        print(f"    PAGE 1 RAW: {json.dumps(resp1, indent=4, default=str)[:1500]}")

    if not resp1:
        return {"ok": False, "error": "No response on first page"}

    items_p1 = client._extract_media_items(resp1)
    handles_p1 = set()
    for post in items_p1:
        user = post.get("user") if isinstance(post, dict) else None
        if user and user.get("username"):
            handles_p1.add(user.get("username"))

    print(f"    Page 1: {len(items_p1)} posts, handles: {handles_p1}")

    cursor = resp1.get("next_page_id")
    print(f"    Cursor for page 2: {cursor}")

    if cursor:
        print(f"    Fetching page 2 with cursor...")
        resp2, _ = await client._get_debug("/v2/hashtag/medias/top", params={"name": hashtag, "page_id": cursor})
        if raw and resp2:
            print(f"    PAGE 2 RAW: {json.dumps(resp2, indent=4, default=str)[:1500]}")
        items_p2 = client._extract_media_items(resp2) if resp2 else []
        handles_p2 = set()
        for post in items_p2:
            user = post.get("user") if isinstance(post, dict) else None
            if user and user.get("username"):
                handles_p2.add(user.get("username"))
        overlap = handles_p1 & handles_p2
        print(f"    Page 2: {len(items_p2)} posts, overlap with page1: {len(overlap)}")
    else:
        print(f"    No cursor — cannot test page 2")

    return {"ok": len(items_p1) > 0}


async def main():
    parser = argparse.ArgumentParser(description="Test HikerAPI end-to-end")
    parser.add_argument("--api-key", type=str, help="HikerAPI access key (or set HIKERAPI_API_KEY env var)")
    parser.add_argument("--raw", action="store_true", help="Print full raw JSON responses before field extraction")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("HIKERAPI_API_KEY")
    if not api_key:
        print("ERROR: No API key provided. Set HIKERAPI_API_KEY env var or use --api-key")
        print("Usage: python -m scripts.test_hikerapi --api-key $HIKERAPI_API_KEY [--raw]")
        return 1

    raw = args.raw

    print("=" * 70)
    print("HikerAPI End-to-End Diagnostic" + (" [RAW MODE]" if raw else ""))
    print("=" * 70)
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print()

    client = HikerAPIClient(api_key=api_key)

    tests = [
        ("Balance/Health", test_balance),
        ("User Lookup", test_user_lookup),
        ("Hashtag Info", test_hashtag_info),
        ("Hashtag Top Posts", test_hashtag_top),
        ("Keyword Search", test_keyword_search),
        ("Hashtag Pagination", test_hashtag_pagination),
    ]

    results: dict[str, Any] = {}
    for name, test_fn in tests:
        try:
            results[name] = await test_fn(client, raw=raw)
        except Exception as e:
            print(f"    EXCEPTION: {type(e).__name__}: {e}")
            if raw:
                import traceback
                traceback.print_exc()
            results[name] = {"ok": False, "error": str(e)}

    await client.close()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = 0
    failed = 0
    for name, r in results.items():
        status = "PASS" if r.get("ok") else "FAIL"
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
        if "hashtag_id" in r:
            extra = f" | id={r['hashtag_id']} media_count={r.get('media_count')}"
        if "items" in r:
            extra = f" | items={r['items']}"
        if "users" in r:
            extra = f" | users={r['users']}"
        if "error" in r:
            extra = f" | error={r['error']}"
        print(f"  [{status}]: {name}{extra}")

    print(f"\n  Total: {passed}/{len(tests)} passed")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
