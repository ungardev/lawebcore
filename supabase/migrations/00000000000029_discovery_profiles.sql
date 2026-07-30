-- Migration: 00029_discovery_profiles
-- Desc: Create discovery_profiles table for universal discovery engine
-- Profiles are agency-shared knowledge (not per-client data), so SELECT
-- is open to all authenticated users. Only service role and admins can write.

BEGIN;

CREATE TABLE IF NOT EXISTS discovery_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint TEXT NOT NULL UNIQUE,
    vertical_slug TEXT NOT NULL,
    languages JSONB NOT NULL DEFAULT '["es"]'::jsonb,
    countries JSONB NOT NULL DEFAULT '[]'::jsonb,
    hashtags JSONB NOT NULL DEFAULT '[]'::jsonb,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    niche_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    geo_indicators JSONB NOT NULL DEFAULT '[]'::jsonb,
    buy_intent_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    source TEXT NOT NULL DEFAULT 'llm'
        CHECK (source IN ('seed', 'llm', 'fallback', 'manual')),
    quality_score NUMERIC,
    times_used INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discovery_profiles_vertical
    ON discovery_profiles(vertical_slug);

CREATE INDEX IF NOT EXISTS idx_discovery_profiles_fingerprint
    ON discovery_profiles(fingerprint);

ALTER TABLE discovery_profiles ENABLE ROW LEVEL SECURITY;

-- SELECT: open to any authenticated user (agency-shared knowledge)
CREATE POLICY discovery_profiles_select ON discovery_profiles
    FOR SELECT USING (true);

-- INSERT/UPDATE/DELETE: restricted to service role and admin_general role
-- Service role bypasses RLS automatically; for user-level admins check role
CREATE POLICY discovery_profiles_admin ON discovery_profiles
    FOR ALL USING (
        auth.jwt() ->> 'app_role' IN ('admin_general', 'service_role')
    )
    WITH CHECK (
        auth.jwt() ->> 'app_role' IN ('admin_general', 'service_role')
    );

COMMIT;
