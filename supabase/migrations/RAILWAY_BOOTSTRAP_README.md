# Railway PostgreSQL Bootstrap — Execution Guide

## The Problem

The original `0000_railway_bootstrap.sql` (1515 lines) failed on Railway Query Editor
because it was executed as a **single batch**, causing PostgreSQL to fail at `BEGIN`
when parsing mixed `DO $$` procedural blocks with regular DDL statements.

## The Solution

Split into **5 sequential files + 1 patches file + 1 remaining migrations file**.
Execute them one by one in Railway Query Editor.

---

## Execution Order (Railway Query Editor)

### Step 0: PATCHES (repair broken tables from partial bootstrap run)
Run **FIRST** if the original bootstrap partially failed:
```
supabase/migrations/0000_01_railway_patches.sql
```

### Steps 1–5: BOOTSTRAP (in order)
Run in strict sequence — each step builds on the previous:

1. `supabase/migrations/0000_02_railway_bootstrap_p1.sql`
   → Extensions + Auth stub + All Enums

2. `supabase/migrations/0000_03_railway_bootstrap_p2.sql`
   → Identity tables (users, roles, teams) + Commercial (clients, brands)

3. `supabase/migrations/0000_04_railway_bootstrap_p4.sql`
   → Influencers + Campaigns + KPIs + Operations

4. `supabase/migrations/0000_05_railway_bootstrap_p4.sql`
   → AI/RAG + Dashboards + Audit + Data Quality + PIAR + Benchmarks + Sentiment

5. `supabase/migrations/0000_06_railway_bootstrap_p5.sql`
   → Discovery tables + Migration tracking + Mark all applied (FINAL)

### Step 6: REMAINING MIGRATIONS
After all bootstrap parts succeed:
```
supabase/migrations/0000_07_railway_remaining_migrations.sql
```
Adds: `date_trunc_month_immutable`, `idx_api_costs_month`, vector(384) embeddings, influencer enrichment columns.

---

## How apply_migrations.py Works

The API's `apply_migrations.py` fetches migrations from GitHub and applies them **one file at a time** via asyncpg. The new sequential files (p1–p5, patches, remaining) are named with numeric prefixes so they are applied in the correct order automatically.

Key behavior:
- **Each file = one transaction** (wrapped in `async with conn.transaction()`)
- Files with lower numeric prefix execute first
- `ON CONFLICT DO NOTHING` makes everything idempotent — safe to re-run
- The schema_migrations table tracks what's been applied and prevents re-runs

---

## What Each File Creates

| File | Creates |
|------|---------|
| p1.sql | Extensions, auth stub, all 13 enum types |
| p2.sql | business_units, users, roles, permissions, teams, clients, brands, brand_contacts, contracts |
| p3.sql | influencers, campaigns, kpis, budgets, tasks, forms, automations |
| p4.sql | AI/RAG tables, dashboards, audit_logs, integrations, webhooks, data_quality, publicaciones, comentarios, tier_benchmarks |
| p5.sql | discovery_runs, discovery_candidates, discovery_conversations, discovery_messages, api_costs, integration_credentials |
| patches.sql | Adds missing columns to broken discovery tables, recreates broken triggers/functions |
| remaining.sql | date_trunc_month_immutable, idx_api_costs_month, vector(384), influencer enrichment columns |

---

## Smoke Test (run after all files)

```sql
SELECT COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema = 'public';
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
SELECT COUNT(*) AS migration_count FROM schema_migrations;
SELECT extname FROM pg_extension ORDER BY extname;
```

Expected: 40+ tables, 30+ migrations tracked, 4+ extensions installed.
