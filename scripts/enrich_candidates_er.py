#!/usr/bin/env python3
"""
Enrich discovery_candidates with real engagement_rate from Apify.

Usage:
    DATABASE_URL="postgresql+asyncpg://postgres:PASSWORD@host:5432/railway" \
    APIFY_API_KEY="apify_api_..." \
    python3 scripts/enrich_candidates_er.py [run_id]

Example:
    DATABASE_URL="postgresql+asyncpg://postgres:PASSWORD@host:5432/railway" \
    APIFY_API_KEY="apify_api_YOUR_KEY_HERE" \
    python3 scripts/enrich_candidates_er.py c2e73451-db11-412b-9d4a-70beb663d446
"""

import asyncio
import os
import sys
import json
from datetime import datetime, timezone

import httpx


DATABASE_URL = os.environ.get("DATABASE_URL", "")
APIFY_TOKEN = os.environ.get("APIFY_API_KEY", "")
APIFY_BASE = "https://api.apify.com/v2"
BATCH_SIZE = 5


async def call_instagram_profile(client: httpx.AsyncClient, handles: list[str]) -> list[dict]:
    """Call apify~instagram-profile-scraper for handles."""
    print(f"  [Apify] Calling instagram-profile-scraper for {len(handles)} handles...")
    try:
        resp = await client.post(
            f"{APIFY_BASE}/acts/apify~instagram-profile-scraper/runs",
            params={"token": APIFY_TOKEN},
            json={"usernames": handles},
            timeout=90.0,
        )
        if resp.status_code not in (200, 201):
            print(f"  [Apify] Start failed: {resp.status_code} {resp.text[:200]}")
            return []
        run_data = resp.json()
        run_id = run_data["data"]["id"]
        dataset_id = run_data["data"]["defaultDatasetId"]
        print(f"  [Apify] Run started: {run_id}, waiting for completion...")

        for attempt in range(60):
            await asyncio.sleep(5)
            try:
                status_resp = await client.get(
                    f"{APIFY_BASE}/actor-runs/{run_id}",
                    params={"token": APIFY_TOKEN},
                    timeout=30.0,
                )
                if status_resp.status_code == 200:
                    status = status_resp.json()["data"]["status"]
                    print(f"  [Apify] Attempt {attempt+1}: status={status}")
                    if status in ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"):
                        break
            except Exception as e:
                print(f"  [Apify] Status check error: {e}")
                continue

        if status != "SUCCEEDED":
            print(f"  [Apify] Run {run_id} final status: {status}")
            return []
        items_resp = await client.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"token": APIFY_TOKEN, "format": "json"},
            timeout=60.0,
        )
        if items_resp.status_code == 200:
            return items_resp.json()
        return []
    except Exception as e:
        print(f"  [Apify] Error: {e}")
        return []


def _normalize_followers(raw: dict) -> int:
    for key in ["followersCount", "followers_count", "followers"]:
        v = raw.get(key)
        if v is not None:
            return int(v)
    return 0


def _normalize_er(raw: dict) -> float | None:
    for key in ["avgLikesPercent", "avg_likes_percent", "engagementRate", "er"]:
        v = raw.get(key)
        if v is not None:
            return round(float(v), 6)
    return None


def _compute_er_from_avgs(raw: dict) -> float | None:
    followers = _normalize_followers(raw)
    if not followers or followers == 0:
        return None
    avg_likes = raw.get("avgLikes") or raw.get("avg_likes") or raw.get("averageLikes")
    avg_comments = raw.get("avgComments") or raw.get("avg_comments") or raw.get("averageComments")
    if avg_likes is not None and avg_comments is not None:
        return round((float(avg_likes) + float(avg_comments)) / followers * 100, 4)
    if avg_likes is not None:
        return round(float(avg_likes) / followers * 100, 4)
    return None


async def update_candidate(engine, candidate_id: str, updates: dict):
    """Update a single discovery_candidate record."""
    import asyncpg
    set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
    vals = list(updates.values())
    vals.append(candidate_id)
    query = f"UPDATE discovery_candidates SET {set_clauses}, updated_at = NOW() WHERE id = ${len(vals)}"
    async with engine.acquire() as conn:
        await conn.execute(query, *vals)


async def main():
    run_id = sys.argv[1] if len(sys.argv) > 1 else "c2e73451-db11-412b-9d4a-70beb663d446"

    engine = asyncpg.create_pool(
        DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"),
        min_size=1,
        max_size=5,
    )

    async with engine.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, handle, followers, engagement_rate
            FROM discovery_candidates
            WHERE run_id = $1
            ORDER BY match_score DESC
            """,
            run_id,
        )

    if not rows:
        print(f"No candidates found for run_id={run_id}")
        await engine.close()
        return

    print(f"Found {len(rows)} candidates for run_id={run_id}")

    candidates = [(str(r["id"]), r["handle"]) for r in rows]
    needs_enrichment = [
        (cid, h) for cid, h in candidates
        if rows[candidates.index((cid, h))]["engagement_rate"] in (None, 0, 0.0)
    ]

    if not needs_enrichment:
        print("All candidates already have engagement_rate. Nothing to do.")
        await engine.close()
        return

    print(f"Need to enrich {len(needs_enrichment)} candidates")

    async with httpx.AsyncClient(timeout=120.0) as client:
        for i in range(0, len(needs_enrichment), BATCH_SIZE):
            batch = needs_enrichment[i : i + BATCH_SIZE]
            handles = [h for _, h in batch if h]
            if not handles:
                continue

            print(f"\nBatch {i // BATCH_SIZE + 1}: {handles}")
            profiles = await call_instagram_profile(client, handles)

            if not profiles:
                print(f"  No results from Apify, skipping batch")
                continue

            profile_map = {}
            for p in profiles:
                username = (
                    p.get("username", "")
                    .lower()
                    .lstrip("@")
                )
                profile_map[username] = p

            for candidate_id, handle in batch:
                h_lower = handle.lower().lstrip("@")
                profile = profile_map.get(h_lower)

                if not profile:
                    for username, p in profile_map.items():
                        if username == h_lower:
                            profile = p
                            break

                if not profile:
                    print(f"  Skip {handle}: no profile found")
                    continue

                followers = _normalize_followers(profile)
                er = _normalize_er(profile)
                if er is None:
                    er = _compute_er_from_avgs(profile)

                updates = {
                    "followers": followers,
                    "engagement_rate": er if er is not None else 0.0,
                    "avg_likes": profile.get("avgLikes") or profile.get("avg_likes"),
                    "avg_comments": profile.get("avgComments") or profile.get("avg_comments"),
                    "posts_count": profile.get("postsCount") or profile.get("posts_count"),
                    "avatar_url": profile.get("profilePicUrlHD") or profile.get("profilePicUrl"),
                    "bio": profile.get("biography") or profile.get("bio"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                try:
                    await update_candidate(engine, candidate_id, updates)
                    print(
                        f"  ✓ @{handle}: {followers:,} followers, ER={er:.4f}%" if er else f"  ✓ @{handle}: {followers:,} followers, ER=N/A"
                    )
                except Exception as e:
                    print(f"  ✗ @{handle}: update failed: {e}")

    print(f"\nDone! Run ID: {run_id}")
    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
