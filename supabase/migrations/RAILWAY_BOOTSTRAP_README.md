# Railway PostgreSQL Bootstrap — Execution Guide

## How it works

Railway applies migrations automatically on every deploy via `apply_migrations()` in `main.py:56`.
This script fetches `.sql` files from GitHub and executes them **one by one** in version order.

The `apply_migrations()` regex extracts version from filename: `^0*(\d+)_.*\.sql$`
So `00000000000001_extensions.sql` → version "1", `00000000000091_railway_p1.sql` → version "91".

**Existing migrations 1-28** run first (from the original Supabase migrations).
**New bootstrap files 91-97** run AFTER, applying the full Railway schema idempotently.

---

## Execution Order

### Via `apply_migrations()` (automatic on every deploy)

`apply_migrations()` runs these automatically in version order:

| # | File | Creates |
|---|------|---------|
| 1-28 | `00000000000001-28_*.sql` | Original Supabase migrations (existing) |
| 91 | `00000000000091_railway_p1.sql` | Extensions + auth stub + all enums |
| 92 | `00000000000092_railway_p2.sql` | Identity + commercial tables |
| 93 | `00000000000093_railway_p3.sql` | Influencers + campaigns + KPIs + operations |
| 94 | `00000000000094_railway_p4.sql` | AI/RAG + dashboards + audit + PIAR + benchmarks |
| 95 | `00000000000095_railway_p5.sql` | Discovery tables + schema_migrations + mark applied |
| 96 | `00000000000096_railway_remaining.sql` | date_trunc_month_immutable + idx_api_costs_month |
| 97 | `00000000000097_railway_patches.sql` | Repair discovery tables (updated_at, estimated_cost_usd, triggers) |

All files are **idempotent** — `CREATE TABLE IF NOT EXISTS` + `ON CONFLICT DO NOTHING`.
They can be re-run safely.

---

## Manual Execution (Railway Query Editor)

If you need to run manually (bypassing `apply_migrations()`):

1. `00000000000091_railway_p1.sql` — extensions + auth + enums
2. `00000000000092_railway_p2.sql` — identity + commercial
3. `00000000000093_railway_p3.sql` — influencers + campaigns + KPIs
4. `00000000000094_railway_p4.sql` — AI + dashboards + PIAR + benchmarks
5. `00000000000095_railway_p5.sql` — discovery + mark applied
6. `00000000000096_railway_remaining.sql` — remaining index fixes
7. `00000000000097_railway_patches.sql` — **run LAST** to repair broken discovery tables

---

## Smoke Test (run after all files)

```sql
SELECT COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema = 'public';
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
SELECT COUNT(*) AS migration_count FROM schema_migrations;
SELECT extname FROM pg_extension ORDER BY extname;
```

Expected: 45+ tables, 35+ migrations tracked, 4+ extensions installed.
