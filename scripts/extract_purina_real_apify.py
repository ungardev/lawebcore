"""
Real Apify extraction script for Purina Dog Chow / Nestlé Venezuela.

Usage:
    python scripts/extract_purina_real_apify.py

Requires:
    APIFY_API_KEY env var (loaded from Railway or .env)
    DATABASE_URL env var (Supabase Postgres)

This script:
1. Calls Apify with Purina-related hashtags + keyword searches for Instagram VE
2. Enriches the resulting profiles (followers, latestPosts, country)
3. Runs engagement analytics
4. Scores with LWFA composite
5. Persists 15-20 ranked candidates into discovery_candidates
"""

import os
import sys
import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

import asyncpg
import httpx

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL env var not set")
    sys.exit(1)

APIFY_API_KEY = os.environ.get("APIFY_API_KEY")
if not APIFY_API_KEY:
    print("ERROR: APIFY_API_KEY env var not set")
    sys.exit(1)

APIFY_BASE = "https://api.apify.com/v2"

BUSINESS_UNIT_ID = "00000000-0000-0000-0000-000000000003"
USER_ID = "00000000-0000-0000-0000-000000000001"
TARGET_CANDIDATES = 18

PURINA_HASHTAGS = [
    "purinaVE",
    "dogchowVE",
    "amorporruno",
    "mascotasVE",
    "perrosVE",
    "mascotasVenezuela",
    "dogChow",
    "purina",
    "petlovers",
    "doglover",
]

PURINA_KEYWORDS = [
    "PurinaVE",
    "DogChowVE",
    "purina dog chow venezuela",
    "mascotasVE",
    "perrosVenezuela",
]


def _country_boost(profile: dict) -> float:
    """Return 1.0 if VE, 0.5 if nearby country, 0.0 otherwise."""
    bio = (profile.get("biography") or "").lower()
    country = (profile.get("country") or "").lower()
    if "venezuela" in bio or "vzla" in bio or "caracas" in bio or country == "ve":
        return 1.0
    if any(k in bio for k in ["colombia", "medellin", "bogota", "panama", "ecuador"]):
        return 0.5
    return 0.0


def _classify_tier(followers: int) -> str:
    if followers < 10_000:
        return "NANO"
    if followers < 100_000:
        return "MICRO"
    if followers < 500_000:
        return "MID"
    return "MACRO"


async def _start_apify_actor(actor_id: str, run_input: dict, timeout_s: int = 600) -> list[dict]:
    """Run an Apify actor synchronously and return dataset items."""
    headers = {"Authorization": f"Bearer {APIFY_API_KEY}"}
    async with httpx.AsyncClient(base_url=APIFY_BASE, headers=headers, timeout=timeout_s) as client:
        sync_url = f"/acts/{actor_id.replace('~', '/')}/run-sync-get-dataset-items"
        print(f"  [APIFY] {actor_id} -> {sync_url}")
        resp = await client.post(sync_url, json=run_input)
        resp.raise_for_status()
        return resp.json()


async def fetch_purina_profiles() -> list[dict]:
    """Run combined Apify extraction: hashtag + keyword discovery."""

    print("\n[1/4] Hashtag search via instagram-hashtag-scraper...")
    hashtag_items = await _start_apify_actor(
        "apify/instagram-hashtag-scraper",
        {"hashtags": PURINA_HASHTAGS, "resultsLimit": 30},
    )
    print(f"  -> {len(hashtag_items)} posts")

    print("\n[2/4] Keyword search via instagram-search-scraper...")
    keyword_items = await _start_apify_actor(
        "apify/instagram-search-scraper",
        {"searchQueries": PURINA_KEYWORDS, "searchType": "user", "resultsLimit": 30},
    )
    print(f"  -> {len(keyword_items)} users")

    profiles: dict[str, dict] = {}
    for item in hashtag_items:
        handle = item.get("ownerUsername") or item.get("username")
        if handle and handle not in profiles:
            profiles[handle] = {
                "username": handle,
                "full_name": item.get("ownerFullName", ""),
                "bio": item.get("caption", ""),
                "avatar_url": item.get("displayUrl", ""),
                "follower_count": 0,
                "following_count": 0,
                "posts_count": 0,
                "is_business": False,
                "is_verified": False,
            }

    for item in keyword_items:
        handle = item.get("username")
        if handle and handle not in profiles:
            profiles[handle] = item
        elif handle:
            profiles[handle].update(item)

    print(f"\n  -> {len(profiles)} unique profiles before enrichment")

    print("\n[3/4] Profile enrichment via instagram-profile-scraper...")
    handles = list(profiles.keys())[:50]
    if handles:
        enriched = await _start_apify_actor(
            "apify/instagram-profile-scraper",
            {"usernames": handles, "profileScrape": ["followersCount", "followsCount", "postsCount", "latestPosts", "biography", "fullName", "profilePicUrl"]},
        )
        for e in enriched:
            handle = e.get("username")
            if handle and handle in profiles:
                profiles[handle].update({
                    "follower_count": e.get("followersCount", 0) or 0,
                    "following_count": e.get("followsCount", 0) or 0,
                    "posts_count": e.get("postsCount", 0) or 0,
                    "is_business": e.get("isBusinessAccount", False),
                    "is_verified": e.get("isVerified", False),
                    "bio": e.get("biography", profiles[handle].get("bio", "")),
                    "full_name": e.get("fullName", profiles[handle].get("full_name", "")),
                    "avatar_url": e.get("profilePicUrl", profiles[handle].get("avatar_url", "")),
                })

    print(f"\n  -> {len(profiles)} enriched profiles")

    scored = []
    for handle, p in profiles.items():
        followers = p.get("follower_count") or 0
        if followers < 1000:
            continue
        latest = p.get("latestPosts") or []
        engagement = 0.0
        if latest and followers > 0:
            likes_avg = sum((post.get("likesCount") or 0) for post in latest) / max(len(latest), 1)
            comments_avg = sum((post.get("commentsCount") or 0) for post in latest) / max(len(latest), 1)
            engagement = (likes_avg + comments_avg) / followers

        geo = _country_boost(p)
        if geo == 0:
            continue

        score = (engagement * 100) + geo * 30 + (20 if p.get("is_business") else 0) + (10 if p.get("is_verified") else 0)

        scored.append({
            **p,
            "engagement_rate": round(engagement, 6),
            "geo_score": geo,
            "tier": _classify_tier(followers),
            "composite_score": round(score, 2),
        })

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    return scored[:TARGET_CANDIDATES]


def _build_rationale(p: dict) -> str:
    tier = p.get("tier", "NANO")
    followers = p.get("follower_count") or 0
    er = (p.get("engagement_rate") or 0) * 100
    geo = "VE" if p.get("geo_score") == 1.0 else "Latam"
    niches = []
    bio = (p.get("bio") or "").lower()
    if "perro" in bio or "dog" in bio or "mascota" in bio:
        niches.append("mascotas")
    if "coach" in bio or "adopta" in bio:
        niches.append("activismo animal")
    if "caracas" in bio or "maracaibo" in bio or "valencia" in bio:
        niches.append("VE")
    if not niches:
        niches.append("perros")
    return f"Perfil {tier} de {', '.join(niches[:2])} en {geo}. ER {er:.1f}%, {followers:,} seguidores. Coincide con audiencia Purina Dog Chow."


async def write_to_db(candidates: list[dict]) -> str:
    """Persist candidates to discovery_runs + discovery_candidates."""
    run_id = str(uuid.uuid4())

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print(f"\n[4/4] Persisting to discovery_runs + discovery_candidates (run_id={run_id})...")

        await conn.execute("""
            INSERT INTO discovery_runs (
                id, brief_text, brief_parsed, product_name, brand_id, industry,
                niches, audience_gender, audience_age_min, audience_age_max,
                audience_countries, platforms, budget_usd, tone, status,
                total_candidates, started_at, completed_at, created_by,
                metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, NOW(), NOW(), $17, $18
            )
        """,
            uuid.UUID(run_id),
            "Busco influencers para Purina Dog Chow en Instagram Venezuela. Perfiles nano, micro y mid. Presupuesto 10K USD.",
            json.dumps({
                "product_name": "Purina Dog Chow",
                "brand_id": "f0000000-0000-0000-0000-000000000002",
                "industry": "mascotas",
                "niches": ["mascotas", "perros"],
                "audience_gender": "female",
                "audience_age_min": 25,
                "audience_age_max": 44,
                "audience_countries": ["VE"],
                "platforms": ["instagram"],
                "budget_usd": 10000,
                "tone": ["emocional"],
            }),
            "Purina Dog Chow",
            uuid.UUID("f0000000-0000-0000-0000-000000000002"),
            "mascotas",
            ["mascotas", "perros"],
            "female",
            25,
            44,
            ["VE"],
            ["instagram"],
            10000.0,
            ["emocional"],
            "completed",
            len(candidates),
            uuid.UUID(USER_ID),
            json.dumps({"source": "apify", "extraction": "purina_real_apify"}),
        )

        for c in candidates:
            followers = c.get("follower_count") or 0
            er = c.get("engagement_rate") or 0
            tier = c.get("tier", "NANO")
            composite = c.get("composite_score") or 0
            rationale = _build_rationale(c)

            await conn.execute("""
                INSERT INTO discovery_candidates (
                    id, run_id, platform, handle, url, full_name, bio,
                    avatar_url, country, city, followers, following, posts_count,
                    engagement_rate, match_score, niche_relevance, geo_relevance,
                    audience_relevance, content_quality, rationale, status,
                    raw_payload, fetched_at, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                    $14, $15, $16, $17, $18, $19, $20, $21, $22, NOW(), NOW(), NOW()
                )
            """,
                uuid.uuid4(),
                uuid.UUID(run_id),
                "instagram",
                c.get("username", ""),
                f"https://instagram.com/{c.get('username', '')}",
                c.get("full_name", ""),
                c.get("bio", ""),
                c.get("avatar_url", ""),
                "VE" if c.get("geo_score") == 1.0 else "LATAM",
                None,
                followers,
                c.get("following_count") or 0,
                c.get("posts_count") or 0,
                er,
                composite,
                0.9 if tier in ("MICRO", "MID") else 0.7,
                1.0 if c.get("geo_score") == 1.0 else 0.5,
                0.8,
                0.8,
                rationale,
                "new",
                json.dumps({"apify_extraction": True, "tier": tier}),
            )

        print(f"  -> {len(candidates)} candidates inserted")
        return run_id

    finally:
        await conn.close()


async def main():
    print("=== Purina Dog Chow — Real Apify Extraction ===\n")
    candidates = await fetch_purina_profiles()
    print(f"\n>>> {len(candidates)} candidates ranked")
    for c in candidates[:10]:
        print(f"  @{c.get('username'):20} {c.get('follower_count', 0):>9,} followers  ER {c.get('engagement_rate', 0) * 100:.2f}%  score {c.get('composite_score', 0):.1f}  geo={c.get('geo_score')}")

    run_id = await write_to_db(candidates)
    print(f"\n✅ DONE. Run ID: {run_id}")


if __name__ == "__main__":
    asyncio.run(main())
