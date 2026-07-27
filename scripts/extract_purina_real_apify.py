import os
import sys
import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

import httpx

APIFY_API_KEY = os.environ.get("APIFY_API_KEY")

if not APIFY_API_KEY:
    print("ERROR: APIFY_API_KEY env var not set")
    sys.exit(1)

APIFY_BASE = "https://api.apify.com/v2"

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


def _country_boost(profile):
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


def _classify_tier(followers):
    if followers < 10000:
        return "NANO"
    if followers < 100000:
        return "MICRO"
    if followers < 500000:
        return "MID"
    return "MACRO"


async def _start_apify_actor(actor_id, run_input, timeout_s=300):
    headers = {"Authorization": f"Bearer {APIFY_API_KEY}"}
    async with httpx.AsyncClient(base_url=APIFY_BASE, headers=headers, timeout=timeout_s) as client:
        sync_url = f"/acts/{actor_id}/run-sync-get-dataset-items"
        print(f"  [APIFY] {actor_id} -> {sync_url}")
        resp = await client.post(sync_url, json=run_input)
        resp.raise_for_status()
        return resp.json()


async def fetch_purina_profiles():
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

    profiles = {}

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


def _build_rationale(p):
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


def write_dump_json_and_sql(candidates):
    """Plan B: dump candidates to /tmp/purina_dump.json and /tmp/purina_insert.sql for manual import."""
    run_id = str(uuid.uuid4())

    dump = {
        "extraction_timestamp": datetime.utcnow().isoformat(),
        "run_id": run_id,
        "total_candidates": len(candidates),
        "source": "extract_purina_real_apify.py v4 (Plan B - JSON dump, no DB insert)",
        "candidates": candidates,
    }

    with open("/tmp/purina_dump.json", "w") as f:
        json.dump(dump, f, indent=2, default=str, ensure_ascii=False)

    sql_lines = [
        "-- Purina Dog Chow candidates - paste in Supabase SQL Editor",
        "-- Generated: " + datetime.utcnow().isoformat() + " | Total: " + str(len(candidates)) + " candidates",
        "",
        "-- 1. Insert discovery_runs row",
        "INSERT INTO discovery_runs (id, brief_text, brief_parsed, product_name, brand_id, industry, niches, audience_gender, audience_age_min, audience_age_max, audience_countries, platforms, budget_usd, tone, status, total_candidates, started_at, completed_at, created_by, metadata) VALUES (",
        "    '" + run_id + "',",
        "    'Purina Dog Chow Venezuela perros 5000 USD Instagram',",
        "    '{\"product_name\": \"Purina Dog Chow\", \"industry\": \"mascotas\", \"niches\": [\"mascotas\", \"perros\"], \"audience_countries\": [\"VE\"], \"platforms\": [\"instagram\"], \"budget_usd\": 10000}'::jsonb,",
        "    'Purina Dog Chow',",
        "    'f0000000-0000-0000-0000-000000000002',",
        "    'mascotas',",
        "    ARRAY['mascotas','perros']::text[],",
        "    'female',",
        "    25, 44,",
        "    ARRAY['VE']::text[],",
        "    ARRAY['instagram']::text[],",
        "    10000.0,",
        "    ARRAY['emocional']::text[],",
        "    'completed',",
        "    " + str(len(candidates)) + ",",
        "    NOW(), NOW(),",
        "    '1e7ffbaf-8ab6-4baa-b507-9250d894a4d1',",
        "    '{\"source\": \"extract_v4_dump\", \"script\": \"extract_purina_real_apify.py\"}'::jsonb",
        ");",
        "",
        "-- 2. Insert " + str(len(candidates)) + " discovery_candidates rows",
        "",
    ]

    def esc(s):
        if s is None:
            return ""
        return str(s).replace("'", "''")

    for c in candidates:
        handle = (c.get("username") or "").lstrip("@")
        if not handle:
            continue
        followers = int(c.get("follower_count") or 0)
        er = float(c.get("engagement_rate") or 0)
        tier = c.get("tier", "NANO")
        composite = float(c.get("composite_score") or 0)
        geo_score = float(c.get("geo_score", 0))
        country = "VE" if geo_score >= 1.0 else ("LATAM" if geo_score >= 0.5 else "OTHER")
        niche_rel = 0.9 if tier in ("MICRO", "MID") else 0.7
        geo_rel = 1.0 if geo_score >= 1.0 else (0.5 if geo_score >= 0.5 else 0.2)

        rationale = esc(_build_rationale(c))
        bio = esc(c.get("bio", ""))
        full_name = esc(c.get("full_name", ""))
        avatar = esc(c.get("avatar_url", ""))
        raw_json = esc(json.dumps({
            "apify_extraction": True,
            "tier": tier,
            "has_full_profile": True,
            "geo_score": geo_score,
        }, ensure_ascii=False))

        sql_lines.append("INSERT INTO discovery_candidates (id, run_id, platform, handle, url, full_name, bio, avatar_url, country, city, followers, following, posts_count, engagement_rate, match_score, niche_relevance, geo_relevance, audience_relevance, content_quality, rationale, status, raw_payload, fetched_at, created_at, updated_at) VALUES (")
        sql_lines.append("    '" + str(uuid.uuid4()) + "', '" + run_id + "', 'instagram',")
        sql_lines.append("    '" + handle + "', 'https://instagram.com/" + handle + "',")
        sql_lines.append("    '" + full_name + "', '" + bio + "', '" + avatar + "',")
        sql_lines.append("    '" + country + "', NULL,")
        sql_lines.append("    " + str(followers) + ", " + str(int(c.get("following_count") or 0)) + ", " + str(int(c.get("posts_count") or 0)) + ",")
        sql_lines.append("    " + str(er) + ", " + str(composite) + ", " + str(niche_rel) + ", " + str(geo_rel) + ", 0.8, 0.8,")
        sql_lines.append("    '" + rationale + "', 'new',")
        sql_lines.append("    '" + raw_json + "'::jsonb,")
        sql_lines.append("    NOW(), NOW(), NOW()")
        sql_lines.append(");")
        sql_lines.append("")

    with open("/tmp/purina_insert.sql", "w") as f:
        f.write("\n".join(sql_lines))

    json_size = os.path.getsize("/tmp/purina_dump.json")
    sql_size = os.path.getsize("/tmp/purina_insert.sql")
    print("  -> /tmp/purina_dump.json written (" + str(json_size) + " bytes)")
    print("  -> /tmp/purina_insert.sql written (" + str(sql_size) + " bytes)")
    print("  -> Run ID for this dump: " + run_id)
    return run_id


async def main():
    print("=== Purina Dog Chow - Real Apify Extraction (v4 Plan B - JSON dump) ===")
    print("APIFY_API_KEY: " + APIFY_API_KEY[:12] + "...")

    candidates = await fetch_purina_profiles()
    print("\n>>> " + str(len(candidates)) + " candidates ranked")
    for c in candidates[:10]:
        print("  @" + str(c.get("username", ""))[:22].ljust(22) + " " + str(c.get("follower_count", 0))[:9].rjust(9) + " followers  ER " + str(round(c.get("engagement_rate", 0) * 100, 2)) + "%  geo=" + str(c.get("geo_score")) + "  tier=" + str(c.get("tier", ""))[:5].ljust(5) + "  score=" + str(round(c.get("composite_score", 0), 1)))

    if candidates:
        run_id = write_dump_json_and_sql(candidates)
        print("\nDONE. Dump ready at /tmp/purina_dump.json")
        print("Run ID for this dump: " + run_id)
        print("")
        print("To insert into DB: paste /tmp/purina_insert.sql in Supabase SQL Editor")
    else:
        print("\nNo candidates passed geo-filter.")


if __name__ == "__main__":
    asyncio.run(main())
