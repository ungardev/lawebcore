-- =================================================================
-- LA WEB CORE - Migration 0020: Fix api_costs monthly index
-- =================================================================
-- Fix for: ERROR 42P17: functions in index expression must be IMMUTABLE
--
-- Postgres rejects DATE_TRUNC('month', TIMESTAMPTZ) inside CREATE INDEX
-- because DATE_TRUNC() depends on the session's timezone setting, making
-- it non-IMMUTABLE in Postgres's eyes.
--
-- Solution: wrapper function explicitly marked IMMUTABLE that forces UTC.
-- This makes the function deterministic regardless of session settings.
--
-- Replaces: idx_api_costs_month from migration 0019 (line 214)
-- =================================================================

-- 1. Create IMMUTABLE wrapper for DATE_TRUNC
CREATE OR REPLACE FUNCTION public.date_trunc_month_immutable(ts TIMESTAMPTZ)
RETURNS TIMESTAMPTZ
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT date_trunc('month', ts AT TIME ZONE 'UTC');
$$;

COMMENT ON FUNCTION public.date_trunc_month_immutable(TIMESTAMPTZ) IS
  'Wraps DATE_TRUNC to make it IMMUTABLE by explicitly using UTC timezone.';

-- 2. Drop the broken index from migration 0019
DROP INDEX IF EXISTS idx_api_costs_month;

-- 3. Recreate the index using the IMMUTABLE wrapper function
CREATE INDEX idx_api_costs_month
  ON api_costs(public.date_trunc_month_immutable(occurred_at), provider);

COMMENT ON INDEX idx_api_costs_month IS
  'Monthly cost aggregation index for api_costs. Uses UTC-fixed DATE_TRUNC wrapper.';
