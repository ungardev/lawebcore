"""
End-to-end test for Purina Dog Chow discovery via HikerAPI.

This script:
1. Logs in via local bcrypt auth (Railway Postgres)
2. Creates a discovery run with the Purina Dog Chow brief (VE, Instagram)
3. Polls until completion
4. Returns top candidates

Run from Railway shell:
    cd /app/apps/api
    python3 scripts/test_purina_dogchow.py

Requirements:
    - HIKERAPI_API_KEY env var set in Railway
    - DATABASE_URL pointing to Railway Postgres
    - ADMIN_TOKEN set (for API auth)
    - User with email/password in users table (e.g. from create_user_ignacio.sql)
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import httpx
from discovery.tools.hikerapi_client import HikerAPIClient


PURINA_BRIEF = {
    "product_name": "Purina Dog Chow",
    "industry": "mascotas",
    "niches": [
        "mascotas", "perros", "pet care", "mascotas Venezuela", "perrosvzla",
        "vet Venezuela", "adopcion", "rescate animal", "dog mom", "pet parent",
        "cachorrosvzla", "mascotasfelices", "petloversvzla", "veterinario",
    ],
    "hashtags": [
        "dogmomvzla", "dogdadvzla", "perrosdeinstagram", "cachorrovzla",
        "mascotafelizve", "adoptavzla", "perrosaludablevzla", "cachorrosbonitos",
        "petloversve", "mascotasdevenezuela", "duenoperro", "cachorrosdeinstagram",
    ],
    "audience_countries": ["VE"],
    "audience_cities": ["Caracas", "Maracaibo", "Valencia", "Barquisimeto", "Maracay", "Ciudad Guayana"],
    "audience_states": ["Distrito Capital", "Miranda", "Carabobo", "Lara", "Zulia", "Aragua", "Bolivar"],
    "platforms": ["instagram"],
    "audience_gender": "all",
    "audience_age_min": 25,
    "audience_age_max": 55,
    "tone": ["familiar", "educativo", "autentico"],
    "additional_context": "Solo creadores de contenido individuales, NO tiendas. Engagement autentico > produccion profesional. Audiencia duena de perros en Venezuela.",
    "exclude_stores": True,
    "analyze_with_ai": False,
}

API_BASE_URL = os.getenv("API_BASE_URL", "https://lawebcore-production.up.railway.app")


async def check_hikerapi_balance() -> dict:
    """Check HikerAPI balance before running."""
    api_key = os.getenv("HIKERAPI_API_KEY", "")
    if not api_key:
        return {"status": "error", "error": "HIKERAPI_API_KEY not set"}
    client = HikerAPIClient(api_key=api_key)
    resp, status = await client._get_debug("/sys/balance")
    await client.close()
    return resp or {}


async def main():
    print("=" * 60)
    print("PURINA DOG CHOW — E2E DISCOVERY TEST (HikerAPI Only)")
    print("=" * 60)

    print("\n[0/5] Pre-flight: HikerAPI balance check...")
    balance_resp = await check_hikerapi_balance()
    if balance_resp.get("status") == "error":
        print(f"  FAIL: {balance_resp['error']}")
        return 1
    balance = balance_resp.get("requests", 0)
    amount = balance_resp.get("amount", 0)
    print(f"  Balance: {balance} requests, ${amount} USD")
    if balance < 100:
        print(f"  WARNING: Low balance ({balance} requests). Test needs ~100.")
    else:
        print(f"  OK: Sufficient for Purina test")

    print("\n[1/5] Login via local auth...")
    login_email = os.getenv("TEST_EMAIL", "ignacio.chacon@hacemosloquenosgusta.com")
    login_password = os.getenv("TEST_PASSWORD", "aYavBm8xwrTTLGuxtCPEEQ")
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        try:
            r = await client.post("/api/v1/auth/login", json={"email": login_email, "password": login_password})
            if r.status_code == 401:
                print(f"  FAIL: Login failed — 401 Unauthorized. Check email/password.")
                print(f"  Response: {r.text[:200]}")
                return 1
            if r.status_code != 200:
                print(f"  FAIL: Login failed — {r.status_code}")
                print(f"  Response: {r.text[:200]}")
                return 1
            token = r.json()["access_token"]
            user_id = r.json()["user_id"]
            role = r.json()["role"]
            print(f"  OK: Logged in as {login_email} (role={role}, user_id={user_id[:8]}...)")
        except Exception as e:
            print(f"  FAIL: Login error — {e}")
            return 1

        print("\n[2/5] Create discovery run — Purina Dog Chow (VE, Instagram)...")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            r = await client.post("/api/v1/discovery/search", json=PURINA_BRIEF, headers=headers)
            if r.status_code not in (200, 201):
                print(f"  FAIL: Create run failed — {r.status_code}")
                print(f"  Response: {r.text[:300]}")
                return 1
            run_data = r.json()
            run_id = run_data.get("id")
            print(f"  OK: Run {run_id[:8]}... created, status={run_data.get('status')}")
        except Exception as e:
            print(f"  FAIL: Create run error — {e}")
            return 1

        print(f"\n[3/5] Polling run {run_id[:8]}... (max 1200s)...")
        start_time = time.time()
        last_status = None
        while True:
            elapsed = int(time.time() - start_time)
            try:
                r = await client.get(f"/api/v1/discovery/runs/{run_id}", headers=headers, timeout=10.0)
                if r.status_code != 200:
                    print(f"  ! poll error {r.status_code}: {r.text[:100]}")
                    await asyncio.sleep(5)
                    continue
                data = r.json()
                status = data.get("status")
                if status != last_status:
                    print(f"  [{elapsed:>4}s] status={status}", flush=True)
                    last_status = status
                if status == "completed":
                    total = data.get("total_candidates", 0)
                    cost = data.get("actual_cost_usd", 0)
                    print(f"\n  DONE in {elapsed}s — {total} candidates, cost=${cost}")
                    break
                if status == "failed":
                    error = data.get("error", "Unknown error")
                    print(f"\n  FAIL: Run failed — {error}")
                    return 1
                if elapsed > 1200:
                    print(f"\n  FAIL: Timeout after {elapsed}s")
                    return 1
            except Exception as e:
                print(f"  ! poll error: {e}")
            await asyncio.sleep(5)

        print("\n[4/5] Fetch top candidates (min_score=15)...")
        try:
            r = await client.get(
                f"/api/v1/discovery/runs/{run_id}/candidates",
                params={"min_score": 15, "limit": 20},
                headers=headers,
                timeout=10.0,
            )
            if r.status_code != 200:
                print(f"  FAIL: Fetch candidates failed — {r.status_code}")
                return 1
            candidates = r.json()
            print(f"  Found {len(candidates)} candidates with score >= 15")
            for c in candidates[:10]:
                handle = c.get("handle", "?")
                score = c.get("match_score", 0)
                followers = c.get("followers", 0)
                tier = c.get("tier", "?")
                print(f"    @{handle:<30} score={score:>5.1f}  followers={followers:>8,}  tier={tier}")
        except Exception as e:
            print(f"  FAIL: Fetch candidates error — {e}")
            return 1

        print("\n[5/5] Final balance check...")
        balance_resp2 = await check_hikerapi_balance()
        final_balance = balance_resp2.get("requests", 0)
        used = balance - final_balance
        print(f"  Started: {balance}, Used: {used}, Remaining: {final_balance}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
