import os, sys, time, json
import httpx

SUPABASE_URL = "https://sdrsxeobcnnqdxqhjb.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkcnN4ZXdlb2Jjbm5xZHhxaGpiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM2MTI5ODEsImV4cCI6MjA5OTE4ODk4MX0.o575lFqXbBd-xKZlu5UEw3BJZnmyAcBlWC0UmDYy0R0"
API_BASE_URL = "https://lawebcore-production.up.railway.app"
TEST_EMAIL = "ungar.villamizar@hacemosloquenosgusta.com"
TEST_PASSWORD = "TuPasswordSegura2026!"

PURINA = {
    "product_name": "Purina Dog Chow",
    "industry": "pet_food",
    "niches": ["mascotas", "perros"],
    "audience_countries": ["VE"],
    "audience_cities": ["Caracas", "Valencia"],
    "platforms": ["instagram"],
    "audience_gender": "all",
    "audience_age_min": 18,
    "audience_age_max": 45,
    "budget_usd": 5000,
    "tone": "warm and authentic",
}

def step(n, title):
    print(f"\n{'='*60}\n[STEP {n}] {title}\n{'='*60}", flush=True)

def ok(msg): print(f"  OK: {msg}", flush=True)
def fail(msg): print(f"  FAIL: {msg}", flush=True); sys.exit(1)

def login():
    step(1, f"Login {TEST_EMAIL}")
    r = httpx.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}, timeout=30)
    if r.status_code != 200: fail(f"Login failed: {r.status_code} {r.text[:200]}")
    ok(f"JWT obtained ({len(r.json()['access_token'])} chars)")
    return r.json()["access_token"]

def health():
    step(2, "Health check")
    r = httpx.get(f"{API_BASE_URL}/api/v1/health", timeout=10)
    if r.status_code != 200: fail(f"Health failed: {r.status_code}")
    ok(r.json())

def create_run(token):
    step(3, "Create discovery run - Purina brief")
    r = httpx.post(f"{API_BASE_URL}/api/v1/discovery/search",
        json=PURINA, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=30)
    if r.status_code not in (200, 201): fail(f"Create run failed: {r.status_code} {r.text[:300]}")
    run = r.json()
    ok(f"Run {run['id']} - status: {run.get('status')}")
    return run["id"]

def wait_run(token, run_id, timeout=600):
    step(4, f"Polling run {run_id[:8]}... (max {timeout}s)")
    start = time.time()
    last = None
    while time.time() - start < timeout:
        r = httpx.get(f"{API_BASE_URL}/api/v1/discovery/runs/{run_id}",
            headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if r.status_code != 200: print(f"  ! poll error {r.status_code}"); time.sleep(5); continue
        data = r.json()
        status = data.get("status")
        elapsed = int(time.time() - start)
        if status != last: print(f"  [{elapsed:>3}s] {status}", flush=True); last = status
        if status == "completed": ok(f"Done in {elapsed}s"); return data
        if status == "failed": fail(f"Run failed: {data.get('error')}")
        time.sleep(5)
    fail(f"Timeout after {timeout}s")

def verify(data):
    step(5, "Verify results")
    total = data.get("total_candidates", 0)
    cost = data.get("actual_cost_usd")
    print(f"  total_candidates={total}  actual_cost_usd={cost}  status={data.get('status')}")
    if total > 0: ok(f"H1 fixed: {total} candidates (was 0)")
    else: fail("H1 still broken: 0 candidates")
    if cost and cost > 0: ok(f"M2 cost tracking: ${cost}")
    else: print(f"  ~ M2: cost={cost} (ok if cache hits)")

def candidates(token, run_id):
    step(6, "Fetch candidates score>=15")
    r = httpx.get(f"{API_BASE_URL}/api/v1/discovery/runs/{run_id}/candidates?min_score=15&limit=20",
        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code != 200: fail(f"Fetch failed: {r.status_code}")
    cs = r.json()
    print(f"  Found {len(cs)} candidates")
    if not cs: fail("No candidates scored >= 15")
    for c in cs[:5]: print(f"    @{c.get('handle','?'):<25} score={c.get('match_score',0):>6.1f} followers={c.get('followers',0):>8,}")
    ok(f"Got {len(cs)} qualified candidates")

def metrics(token):
    step(7, "Discovery metrics")
    r = httpx.get(f"{API_BASE_URL}/api/v1/discovery/metrics",
        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code != 200: fail(f"Metrics failed: {r.status_code}")
    m = r.json()
    print(json.dumps(m, indent=2))
    if m.get("avg_cost_per_run", 0) > 0: ok(f"M2 cost: avg_cost_per_run=${m['avg_cost_per_run']}")

def main():
    print("="*60)
    print(" LA WEB CORE - DISCOVERY PIPELINE E2E TEST")
    print("="*60, flush=True)
    token = login()
    health()
    run_id = create_run(token)
    data = wait_run(token, run_id)
    verify(data)
    candidates(token, run_id)
    metrics(token)
    print("\n" + "="*60)
    print(" ALL TESTS PASSED")
    print("="*60)

if __name__ == "__main__":
    main()
