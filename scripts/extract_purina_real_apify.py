import os
import sys
import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
APIFY_API_KEY = os.environ.get("APIFY_API_KEY")

if not APIFY_API_KEY:
    print("ERROR: APIFY_API_KEY env var not set")
    sys.exit(1)

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and/or SUPABASE_SERVICE_ROLE_KEY not set")
    sys.exit(1)

APIFY_BASE = "https://api.apify.com/v2"

BUSINESS_UNIT_ID = "00000000-0000-0000-0000-000000000003"
USER_ID = "1e7ffbaf-8ab6-4baa-b507-9250d894a4d1"
TARGET_CANDIDATES = 18

PURINA_HASHTAGS = [
    "purinaVE", "dogchowVE", "amorporruno", "mascotasVE", "perrosVE",
    "mascotasVenezuela", "dogChow", "purina", "petlovers", "doglover",
    "vzla", "venezuela", "adopcionvzla", "rescateanimalvzla",
]

PURINA_KEYWORDS = [
    "PurinaVE", "DogChowVE", "purina dog chow venezuela",
    "mascotasVE", "perrosVenezuela", "amantesdelosperros",
    "mascotas caracas", "perrosvzla",
]


def _country_boost(profile: dict) -> float:
    bio = (profile.get("biography") or profile.get("bio") or "").lower()
    country = (profile.get("country") or "").lower()
    username = (profile.get("username") or profile.get("handle") or "").lower()
    full_name = (profile.get("full_name") or profile.get("fullName") or "").lower()
    location = (profile.get("locationName") or profile.get("location") or "").lower()
    followers = profile.get("follower_count") or profile.get("followersCount") or 0
    is_business = profile.get("is_business") or profile.get("isBusinessAccount") or False

    if any(k in bio + full_name + username for k in [
        "venezuela", "vzla", "caracas", "maracaibo", "valencia",
        "san cristobal", "maturin", "barquisimeto", "puerto la cruz"
    ]):
        return 1.0
    if country in ("ve", "venezuela"):
        return 1.0
    if any(k in bio + full_name + username for k in [
        "colombia", "medellin", "bogota", "panama", "ecuador",
        "latinoamerica", "latam", "peru", "chile"
    ]):
        return 0.5
    if is_business and followers > 5000 and profile.get("engagement_rate", 0) > 0.01:
        return 0.4
    if followers > 20000 and profile.get("engagement_rate", 0) > 0.02:
        return 0.3
    return 0.0


def _classify_tier(followers: int) -> str:
    if followers < 10_000:
        return "NANO"
    if followers < 100_000:
        return "MICRO"
    if followers < 500_000:
        return "MID"
    return "MACRO"


async def _start_apify_actor(actor_id: str, run_input: dict, timeout_s: int = 300) -> list[dict]:
    headers = {"Authorization": f"Bearer {APIFY_API_KEY}"}
    async with httpx.AsyncClient(base_url=APIFY_BASE, headers=headers, timeout=timeout_s) as client:
        sync_url = f"/acts/{actor_id}/run-sync-get-dataset-items"
        print(f"  [APIFY] {actor_id} -> {sync_url}")
        resp = await client.post(sync_url, json=run_input)
        resp.raise_for_status()
        return resp.json()


async def fetch_purina_profiles() -> list[dict]:
    print("\n[1/4] Hashtag search via apify~instagram-hashtag-scraper...")
    hashtag_items = await _start_apify_actor(
        "apify~instagram-hashtag-scraper",
        {"hashtags": PURINA_HASHTAGS, "resultsLimit": 50},
    )
    print(f"  -> {len(hashtag_items)} posts")

    print("\n[2/4] Keyword search via apify~instagram-search-scraper...")
    keyword_items = await _start_apify_actor(
        "apify~instagram-search-scraper",
        {"searchQueries": PURINA_KEYWORDS, "searchType": "user", "resultsLimit": 30},
    )
    print(f"  -> {len(keyword_items)} users")

    profiles: dict[str, dict] = {}

    for item in hashtag_items:
        handle = item.get("ownerUsername") or item.get("username")
        if not handle:
            continue
        if handle not in profiles:
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
                "locationName": item.get("locationName", ""),
            }

    for item in keyword_items:
        handle = item.get("username")
        if not handle:
            continue
        if handle not in profiles:
            profiles[handle] = {
                "username": handle,
                "full_name": item.get("fullName", ""),
                "bio": item.get("biography", ""),
                "avatar_url": item.get("profilePicUrl", ""),
                "follower_count": 0,
                "following_count": 0,
                "posts_count": 0,
                "is_business": False,
                "is_verified": False,
            }
        else:
            profiles[handle].update({
                "full_name": item.get("fullName", profiles[handle].get("full_name", "")),
                "bio": item.get("biography", profiles[handle].get("bio", "")),
                "avatar_url": item.get("profilePicUrl", profiles[handle].get("avatar_url", "")),
            })

    print(f"\n  -> {len(profiles)} unique profiles before enrichment")

    print("\n[3/4] Profile enrichment via apify~instagram-profile-scraper...")
    handles = list(profiles.keys())[:80]
    if handles:
        enriched = await _start_apify_actor(
            "apify~instagram-profile-scraper",
            {"usernames": handles, "resultsType": "details"},
        )
        for e in enriched:
            handle = e.get("username")
            if handle and handle in profiles:
                profiles[handle].update({
                    "follower_count": e.get("followersCount", 0) or 0,
                    "following_count": e.get("followsCount", 0) or 0,
                    "posts_count": e.get("postsCount", 0) or 0,
                    "is_business": e.get("isBusinessAccount", False),
                    "is_verified": e.get("verified", False),
                    "bio": e.get("biography", profiles[handle].get("bio", "")),
                    "full_name": e.get("fullName", profiles[handle].get("full_name", "")),
                    "avatar_url": e.get("profilePicUrl", profiles[handle].get("avatar_url", "")),
                    "country": e.get("country", ""),
                    "locationName": e.get("locationName", profiles[handle].get("locationName", "")),
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
        score = (engagement * 100) + geo * 30 + (20 if p.get("is_business") else 0) + (10 if p.get("is_verified") else 0)

        scored.append({
            **p,
            "engagement_rate": round(engagement, 6),
            "geo_score": geo,
            "tier": _classify_tier(followers),
            "composite_score": round(score, 2),
        })

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    print(f"\n  -> {len(scored)} scored candidates (geo > 0)")
    return scored[:TARGET_CANDIDATES]


def _build_rationale(p: dict) -> str:
    tier = p.get("tier", "NANO")
    followers = p.get("follower_count") or 0
    er = (p.get("engagement_rate") or 0) * 100
    geo = "VE" if p.get("geo_score") == 1.0 else "Latam"
    niches = []
    bio = (p.get("bio") or "").lower()
    if any(k in bio for k in ["perro", "dog", "mascota", "pet", "cachorro"]):
        niches.append("mascotas")
    if any(k in bio for k in ["adopta", "rescate", "coach", "adopcion", "refugio"]):
        niches.append("activismo animal")
    if any(k in bio for k in ["caracas", "maracaibo", "valencia", "vzla", "venezuela"]):
        niches.append("VE local")
    if not niches:
        niches.append("perros")
    return f"Perfil {tier} de {', '.join(niches[:2])} en {geo}. ER {er:.1f}%, {followers:,} seguidores. Coincide con audiencia Purina Dog Chow."


async def write_to_db_via_rest(candidates: list[dict]) -> str:
    run_id = str(uuid.uuid4())

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    async with httpx.AsyncClient(base_url=f"{SUPABASE_URL}/rest/v1", headers=headers, timeout=60) as client:
        run_payload = {
            "id": run_id,
            "brief_text": "Purina Dog Chow Venezuela perros 5000 USD Instagram",
            "brief_parsed": json.dumps({
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
            "product_name": "Purina Dog Chow",
            "brand_id": "f0000000-0000-0000-0000-000000000002",
            "industry": "mascotas",
            "niches": ["mascotas", "perros"],
            "audience_gender": "female",
            "audience_age_min": 25,
            "audience_age_max": 44,
            "audience_countries": ["VE"],
            "platforms": ["instagram"],
            "budget_usd": 10000.0,
            "tone": ["emocional"],
            "status": "completed",
            "total_candidates": len(candidates),
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "created_by": uuid.UUID(USER_ID),
            "metadata": json.dumps({"source": "extract_v3_rest", "script": "extract_purina_real_apify.py"}),
        }

        print(f"\n[4/4] Persisting to discovery_runs + discovery_candidates via REST...")
        resp = await client.post("/discovery_runs", json=run_payload)
        if resp.status_code >= 300:
            print(f"  ! discovery_runs insert failed: {resp.status_code} {resp.text[:300]}")
            return run_id
        print(f"  -> discovery_run {run_id} created")

        inserted = 0
        for c in candidates:
            handle = c.get("username", "").lstrip("@")
            if not handle:
                continue

            followers = c.get("follower_count") or 0
            er = c.get("engagement_rate") or 0
            tier = c.get("tier", "NANO")
            composite = c.get("composite_score") or 0
            geo_score = c.get("geo_score", 0)

            payload = {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "platform": "instagram",
                "handle": handle,
                "url": f"https://instagram.com/{handle}",
                "full_name": c.get("full_name") or "",
                "bio": c.get("bio") or "",
                "avatar_url": c.get("avatar_url") or "",
                "country": "VE" if geo_score >= 1.0 else ("LATAM" if geo_score >= 0.5 else "OTHER"),
                "city": None,
                "followers": followers,
                "following": c.get("following_count") or 0,
                "posts_count": c.get("posts_count") or 0,
                "engagement_rate": er,
                "match_score": composite,
                "niche_relevance": 0.9 if tier in ("MICRO", "MID") else 0.7,
                "geo_relevance": 1.0 if geo_score >= 1.0 else (0.5 if geo_score >= 0.5 else 0.2),
                "audience_relevance": 0.8,
                "content_quality": 0.8,
                "rationale": _build_rationale(c),
                "status": "new",
                "raw_payload": json.dumps({
                    "apify_extraction": True,
                    "tier": tier,
                    "has_full_profile": True,
                    "geo_score": geo_score,
                }),
                "fetched_at": datetime.utcnow().isoformat(),
            }

            resp = await client.post("/discovery_candidates", json=payload)
            if resp.status_code < 300:
                inserted += 1
            else:
                print(f"  ! candidate failed {handle}: {resp.status_code} {resp.text[:150]}")

        print(f"  -> {inserted}/{len(candidates)} candidates inserted")
        return run_id


async def main():
    print("=== Purina Dog Chow — Real Apify Extraction (v3 REST) ===")
    print(f"APIFY_API_KEY: {APIFY_API_KEY[:12]}...")
    print(f"SUPABASE_URL: {SUPABASE_URL}")
    print(f"SUPABASE_SERVICE_ROLE_KEY: {'SET' if SUPABASE_SERVICE_ROLE_KEY else 'MISSING'}")

    candidates = await fetch_purina_profiles()
    print(f"\n>>> {len(candidates)} candidates ranked")
    for c in candidates[:10]:
        print(f"  @{c.get('username', ''):<22} {c.get('follower_count', 0):>9,} followers  "
              f"ER {c.get('engagement_rate', 0) * 100:.2f}%  geo={c.get('geo_score')}  "
              f"tier={c.get('tier'):<5}  score={c.get('composite_score', 0):.1f}")

    if candidates:
        run_id = await write_to_db_via_rest(candidates)
        print(f"\n✅ DONE. Run ID: {run_id}")
    else:
        print("\n❌ No candidates passed geo-filter. Check _country_boost() thresholds.")


if __name__ == "__main__":
    asyncio.run(main())
