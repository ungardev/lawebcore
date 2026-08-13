#!/usr/bin/env python3
"""
E2E test for Lens VE mascotas discovery — validates all 6 fix changes.

Usage:
    python scripts/test_lens_mascotas_ve.py

This script:
1. Creates a discovery run for mascotas VE
2. Polls until completion (up to 10 min)
3. Prints top 20 candidates with full metrics
4. Validates success criteria (≥30% with ER>4%, ≥80% with VE geo signal)
"""

import os
import sys
import time

import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://sdrsxeobcnnqdxqhjb.supabase.co")
SUPABASE_ANON_KEY = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkcnN4ZXdlb2Jjbm5xZHhqaGpiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM2MTI5ODEsImV4cCI6MjA5OTE4ODk4MX0.o575lFqXbBd-xKZlu5UEw3BJZnmyAcBlWC0UmDYy0R0"
)
TEST_EMAIL = os.environ.get("TEST_EMAIL", "ungar.villamizar@hacemosloquenosgusta.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "TuPasswordSegura2026!")

BRIEF = {
    "product_name": "Purina Dog Chow",
    "industry": "mascotas",
    "niches": ["mascotas", "perros", "gatos", "pet care", "adopcion"],
    "hashtags": ["mascotasvzla", "mascotasvenezuela", "petloversvzla"],
    "audience_countries": ["VE"],
    "audience_cities": ["Caracas", "Valencia", "Maracaibo"],
    "platforms": ["instagram"],
    "audience_gender": "all",
    "audience_age_min": 18,
    "audience_age_max": 45,
    "budget_usd": 5000,
    "tone": "warm and authentic",
    "analyze_with_ai": True,
}


def step(n, title):
    print(f"\n{'='*60}\n[STEP {n}] {title}\n{'='*60}", flush=True)


def ok(msg):
    print(f"  OK: {msg}", flush=True)


def warn(msg):
    print(f"  WARN: {msg}", flush=True)


def fail(msg):
    print(f"  FAIL: {msg}", flush=True)
    sys.exit(1)


def login():
    step(1, f"Login {TEST_EMAIL}")
    r = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        timeout=30,
    )
    if r.status_code != 200:
        fail(f"Login failed: {r.status_code} {r.text[:200]}")
    ok(f"JWT obtained ({len(r.json()['access_token'])} chars)")
    return r.json()["access_token"]


def create_run(token):
    step(2, "Create discovery run — mascotas VE")
    r = httpx.post(
        f"{API_BASE_URL}/api/v1/lens/discovery/search",
        json=BRIEF,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        fail(f"Create run failed: {r.status_code} {r.text[:500]}")
    run = r.json()
    ok(f"Run created: {run.get('id')}")
    return run["id"], token


def poll_run(run_id: str, token: str, max_wait_sec: int = 600, interval_sec: int = 5):
    step(3, f"Polling run {run_id} (max {max_wait_sec}s)")
    start = time.time()
    last_status = None
    while time.time() - start < max_wait_sec:
        r = httpx.get(
            f"{API_BASE_URL}/api/v1/lens/discovery/runs/{run_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if r.status_code != 200:
            warn(f"Status poll failed: {r.status_code} — retrying")
            time.sleep(interval_sec)
            continue
        run = r.json()
        status = run.get("status", "unknown")
        elapsed = int(time.time() - start)
        if status != last_status:
            print(f"  [{elapsed}s] status={status}", flush=True)
            last_status = status
        if status in ("completed", "partial"):
            ok(f"Run completed after {elapsed}s")
            return run
        if status in ("failed", "cancelled"):
            fail(f"Run ended with status={status}: {run.get('error', 'no error detail')}")
        time.sleep(interval_sec)
    fail(f"Timeout after {max_wait_sec}s waiting for run")


def get_candidates(run_id: str, token: str, limit: int = 50):
    step(4, f"Fetching top {limit} candidates")
    r = httpx.get(
        f"{API_BASE_URL}/api/v1/lens/discovery/runs/{run_id}/candidates",
        params={"limit": limit},
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    if r.status_code != 200:
        fail(f"Candidates fetch failed: {r.status_code} {r.text[:300]}")
    candidates = r.json()
    ok(f"Fetched {len(candidates)} candidates")
    return candidates


def print_candidates(candidates: list[dict]):
    step(5, "Top 20 candidates")
    print(f"{'#':<3} {'Handle':<25} {'Followers':>10} {'ER%':>6} {'Score':>6} {'Geo':>6} {'Niche':>6} {'City':<15} {'Tier':<6}")
    print("-" * 105)
    for i, c in enumerate(candidates[:20], 1):
        er = (c.get("engagement_rate") or 0) * 100
        print(
            f"{i:<3} @{c.get('handle', ''):<25} "
            f"{c.get('followers', 0):>10,} "
            f"{er:>5.1f}% "
            f"{c.get('match_score', 0):>6.1f} "
            f"{c.get('geo_relevance', 0):>6.1f} "
            f"{c.get('niche_relevance', 0):>6.1f} "
            f"{c.get('city') or ''!s:<15} "
            f"{c.get('tier', ''):<6}"
        )


def validate_criteria(candidates: list[dict]):
    step(6, "Validating success criteria")

    total = len(candidates)
    if total == 0:
        fail("No candidates returned")

    er_threshold = 0.04
    ve_signals = ["caracas", "vzla", "venezuela", "maracaibo", "valencia", "maturin",
                  "barquisimeto", "maracay", "vzlatex", "vzlan", "venezolano"]

    er_good = [c for c in candidates if (c.get("engagement_rate") or 0) > er_threshold]
    geo_signals = [c for c in candidates if any(
        sig in (c.get("city", "") + " " + (c.get("bio") or "") + " " + (c.get("handle", "")).lower()).lower()
        for sig in ve_signals
    )]
    tier_micro = [c for c in candidates if c.get("tier") == "MICRO"]
    tier_nano = [c for c in candidates if c.get("tier") == "NANO"]
    rising_stars = [c for c in candidates if (c.get("engagement_rate") or 0) > 0.05
                    and (c.get("tier") in ("NANO", "MICRO"))]

    er_pct = len(er_good) / max(total, 1) * 100
    geo_pct = len(geo_signals) / max(total, 1) * 100

    print(f"\n  Total candidates:     {total}")
    print(f"  Candidates with ER>4%: {len(er_good)} ({er_pct:.0f}%) — {'PASS' if er_pct >= 30 else 'FAIL'} (threshold 30%)")
    print(f"  VE geo signals:       {len(geo_signals)} ({geo_pct:.0f}%) — {'PASS' if geo_pct >= 80 else 'FAIL'} (threshold 80%)")
    print(f"  MICRO tier:           {len(tier_micro)}")
    print(f"  NANO tier:            {len(tier_nano)}")
    print(f"  Rising stars (ER>5% nano/micro): {len(rising_stars)}")
    print(f"  Avg match_score:      {sum(c.get('match_score', 0) for c in candidates) / max(len(candidates), 1):.1f}")
    print(f"  Avg ER:               {(sum(c.get('engagement_rate', 0) for c in candidates) / max(len(candidates), 1)) * 100:.2f}%")

    passed = er_pct >= 30 and geo_pct >= 80
    if passed:
        ok("All criteria PASSED")
    else:
        warn("Some criteria FAILED — review above")

    return passed


def main():
    print("=" * 60)
    print("Lens VE Mascotas — E2E Validation Test")
    print("=" * 60)

    try:
        token = login()
        run_id, token = create_run(token)
        poll_run(run_id, token)
        candidates = get_candidates(run_id, token, limit=50)
        print_candidates(candidates)
        validate_criteria(candidates)

        step(7, "Done")
        print(f"\nRun ID: {run_id}")
        print(f"API URL: {API_BASE_URL}")
        ok("E2E test completed successfully")

    except Exception as e:
        fail(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
