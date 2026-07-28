-- =================================================================
-- Railway Bootstrap — Remaining migrations 0020, 0023, 0024
-- Version 96 — runs AFTER existing migrations 1-28
-- These were not fully covered by the original bootstrap
-- =================================================================

CREATE OR REPLACE FUNCTION public.date_trunc_month_immutable(ts TIMESTAMPTZ)
RETURNS TIMESTAMPTZ LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT date_trunc('month', ts AT TIME ZONE 'UTC');
$$;

DROP INDEX IF EXISTS idx_api_costs_month;
CREATE INDEX idx_api_costs_month ON api_costs(public.date_trunc_month_immutable(occurred_at), provider);

INSERT INTO schema_migrations (version, filename) VALUES
    ('96', '00000000000096_railway_remaining.sql')
ON CONFLICT (version) DO NOTHING;
