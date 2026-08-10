"""
Full discovery pipeline test with HikerAPI — simulates the worker pipeline
without enqueuing a background job.

Run from Railway shell:
    cd /app
    export HIKERAPI_API_KEY=your_key
    export INSTAGRAM_SOURCE=hikerapi
    python -m scripts.test_hikerapi_full \
        --hashtags recetasvenezuela,cocinavenezuela,postresvenezuela \
        --keywords "recetas con leche evaporada" \
        --country VE \
        --max-results 30

This script replicates the logic in worker.py but runs synchronously
and prints detailed diagnostics at each step.
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from discovery.tools.source_registry import get_instagram_source


async def run_pipeline(args) -> int:
    """Execute the full 4-step pipeline."""
    source_name = os.getenv("INSTAGRAM_SOURCE", "hikerapi")
    instagram_source = get_instagram_source(source_name)

    print("=" * 70)
    print(f"HikerAPI Full Pipeline Test")
    print(f"Source: {source_name}")
    print(f"Hashtags: {args.hashtags}")
    print(f"Keywords: {args.keywords}")
    print(f"Country: {args.country}")
    print(f"Max results per hashtag: {args.max_results}")
    print("=" * 70)

    # STEP 1: Hashtag search
    print("\n[STEP 1] Hashtag search...")
    hashtag_list = [h.strip() for h in args.hashtags.split(",") if h.strip()]
    profiles: dict[str, dict] = {}
    hashtag_results = {}

    for tag in hashtag_list:
        print(f"  Searching #{tag}...", end=" ", flush=True)
        try:
            results = await instagram_source.search_hashtag(tag, country=args.country, limit=args.max_results)
            hashtag_results[tag] = len(results)
            stores = 0
            for r in results:
                handle = r.get("username", "")
                if not handle:
                    continue
                if handle not in profiles:
                    profiles[handle] = r
                    if r.get("is_business") and r.get("follower_count", 0) < 50000:
                        stores += 1
            print(f"{len(results)} posts, {stores} stores")
        except Exception as e:
            print(f"ERROR: {e}")
            hashtag_results[tag] = 0

    print(f"\n  Total unique profiles: {len(profiles)}")

    # STEP 2: Keyword search
    print("\n[STEP 2] Keyword search...")
    keyword_list = [k.strip() for k in args.keywords.split(",") if k.strip()]
    keyword_results = {}

    for kw in keyword_list:
        print(f"  Searching '{kw}'...", end=" ", flush=True)
        try:
            results = await instagram_source.search_keyword(kw, limit=15)
            keyword_results[kw] = len(results)
            stores = 0
            for r in results:
                handle = r.get("username", "")
                if not handle:
                    continue
                if handle not in profiles:
                    profiles[handle] = r
                    if r.get("is_business") and r.get("follower_count", 0) < 50000:
                        stores += 1
            print(f"{len(results)} users, {stores} stores")
        except Exception as e:
            print(f"ERROR: {e}")
            keyword_results[kw] = 0

    print(f"\n  Total unique profiles after keyword step: {len(profiles)}")

    # STEP 3: Pre-filter (stores, low followers, private)
    print("\n[STEP 3] Pre-filtering...")
    MIN_FOLLOWERS = 1000
    prefiltered: dict[str, dict] = {}
    stats = {
        "low_followers": 0,
        "stores": 0,
        "private": 0,
        "ok": 0,
    }

    for handle, p in profiles.items():
        followers = p.get("follower_count", 0) or p.get("followersCount", 0) or 0
        is_biz = p.get("is_business", False) or p.get("isBusinessAccount", False)
        is_priv = p.get("is_private", False)

        if followers < MIN_FOLLOWERS:
            stats["low_followers"] += 1
            continue
        if is_biz and followers < 50000:
            stats["stores"] += 1
            continue
        if is_priv and followers < 10000:
            stats["private"] += 1
            continue
        stats["ok"] += 1
        prefiltered[handle] = p

    print(f"  Total collected: {len(profiles)}")
    print(f"  Filtered (low followers <{MIN_FOLLOWERS}): {stats['low_followers']}")
    print(f"  Filtered (stores/business): {stats['stores']}")
    print(f"  Filtered (private/<10k): {stats['private']}")
    print(f"  PASSED pre-filter: {stats['ok']}")

    # STEP 4: Profile enrichment via HikerAPI (deep dive)
    print("\n[STEP 4] Enriching top profiles via HikerAPI...")
    MIN_SCORE = 20

    enriched = []
    sample = list(prefiltered.items())[:args.enrich_count]

    for handle, p in sample:
        try:
            full = await instagram_source.enrich_profile(handle)
            if full:
                enriched.append(full)
                print(f"  @{handle}: {full.get('follower_count', 0):,} followers, "
                      f"is_business={full.get('is_business')}, "
                      f"bio={full.get('biography', '')[:50]}...")
            else:
                print(f"  @{handle}: NOT FOUND (private or deleted)")
        except Exception as e:
            print(f"  @{handle}: ERROR {e}")

    # Simple scoring
    print(f"\n[STEP 5] Simple scoring ({len(enriched)} profiles)...")
    scored = []
    for p in enriched:
        followers = p.get("follower_count", 0) or 0
        is_biz = p.get("is_business", False)
        bio = p.get("biography", "") or ""
        bio_lower = bio.lower()

        # Anti-tienda signals
        tienda_kw = sum(1 for kw in ["tienda", "shop", "store", "petshop", "ventas", "pedidos",
                                      "envíos", "delivery", "whatsapp", "precio", "oferta"]
                        if kw in bio_lower)
        # Creator signals
        creator_kw = sum(1 for kw in ["creador", "content creator", "cocin", "recipe", "chef",
                                       "blogger", "influencer", "comida", "postre", "receta",
                                       "horne", "bakery", "foodie"]
                         if kw in bio_lower)

        score = 50  # base
        if is_biz and tienda_kw > 0:
            score -= 40
        elif tienda_kw >= 3:
            score -= 25
        if creator_kw >= 2:
            score += 20
        if followers > 10000:
            score += 15
        if followers > 50000:
            score += 15

        score = max(0, min(100, score))
        p["_score"] = score
        p["_tienda_kw"] = tienda_kw
        p["_creator_kw"] = creator_kw
        scored.append(p)

    scored.sort(key=lambda x: x["_score"], reverse=True)

    print("\n  TOP 10 CANDIDATES:")
    print(f"  {'Rank':<5} {'Handle':<25} {'Followers':>10} {'Score':>6} {'Tienda':>6} {'Creator':>7} {'is_biz':>7} Bio")
    print("  " + "-" * 110)

    for i, p in enumerate(scored[:10], 1):
        bio = (p.get("biography") or "")[:40]
        print(f"  {i:<5} @{p.get('username', ''):<25} {p.get('follower_count', 0):>10,} "
              f"{p.get('_score', 0):>6.0f} {p.get('_tienda_kw', 0):>6} "
              f"{p.get('_creator_kw', 0):>7} {str(p.get('is_business', False)):>7} {bio}")

    # Final summary
    qualified = [p for p in scored if p.get("_score", 0) >= MIN_SCORE]
    stores_in_top10 = sum(1 for p in scored[:10] if p.get("is_business") and p.get("follower_count", 0) < 100000)

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"  Source: {source_name}")
    print(f"  Hashtags tested: {len(hashtag_list)} ({' '.join(hashtag_list[:5])}...)")
    print(f"  Total unique profiles collected: {len(profiles)}")
    print(f"  Passed pre-filter: {stats['ok']}")
    print(f"  Enriched (top {args.enrich_count}): {len(enriched)}")
    print(f"  Qualified (score >= {MIN_SCORE}): {len(qualified)}")
    print(f"  Stores in top 10: {stores_in_top10}")
    print(f"  Top score: {scored[0].get('_score', 0) if scored else 0:.0f}/100")
    print("=" * 70)

    await instagram_source.close()
    return 0 if len(qualified) >= 5 else 1


async def main():
    parser = argparse.ArgumentParser(description="HikerAPI full pipeline test")
    parser.add_argument("--hashtags", type=str,
                        default="recetasvenezuela,cocinavenezuela,postresvenezuela,"
                                "reposteriacasera,comidacasera,cafévenezuela,bebidascalientes,"
                                "dulcestipicos,cocinafacil,horneadocasa,comidasegura,"
                                "cocinacasera,recetasfaciles,postresfaciles",
                        help="Comma-separated hashtags (without #)")
    parser.add_argument("--keywords", type=str,
                        default="recetas con leche evaporada,postres caseros Venezuela,"
                                "cocina criolla venezolana,recetas faciles",
                        help="Comma-separated keywords")
    parser.add_argument("--country", type=str, default="VE", help="Country code")
    parser.add_argument("--max-results", type=int, default=10,
                        help="Max results per hashtag")
    parser.add_argument("--enrich-count", type=int, default=30,
                        help="How many profiles to enrich")
    args = parser.parse_args()

    return await run_pipeline(args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
