-- =================================================================
-- Railway Patches — Fix broken discovery tables from partial bootstrap
-- Version 97 — runs LAST (91-97 order)
-- Repairs discovery_runs missing columns that broke the RPC function
-- =================================================================

ALTER TABLE discovery_runs ADD COLUMN IF NOT EXISTS audience_cities TEXT[];
ALTER TABLE discovery_runs ADD COLUMN IF NOT EXISTS estimated_cost_usd NUMERIC(10,4);
ALTER TABLE discovery_runs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE discovery_candidates ALTER COLUMN id SET DEFAULT extensions.uuid_generate_v4();

CREATE OR REPLACE FUNCTION discovery_runs_merge_metadata(p_run_id UUID, p_metadata JSONB)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE discovery_runs
    SET metadata = COALESCE(metadata, '{}'::jsonb) || p_metadata,
        updated_at = NOW()
    WHERE id = p_run_id;
END; $$;

DO $$
BEGIN
    CREATE TRIGGER trg_discovery_runs_updated_at BEFORE UPDATE ON discovery_runs
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TRIGGER trg_discovery_candidates_updated_at BEFORE UPDATE ON discovery_candidates
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TRIGGER trg_discovery_conversations_updated_at BEFORE UPDATE ON discovery_conversations
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS tier TEXT CHECK (tier IN ('NANO','MICRO','MID','MACRO'));
ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS is_tienda BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_tier ON discovery_candidates(tier);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_is_tienda ON discovery_candidates(is_tienda);

ALTER TABLE influencers ADD COLUMN IF NOT EXISTS gender TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS age_range TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS latitude NUMERIC(9,6);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS longitude NUMERIC(9,6);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS audience_demographics JSONB DEFAULT '{}'::jsonb;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS is_discoverable BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovery_query TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovery_confidence NUMERIC(5,2);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS sub_tier TEXT;
CREATE INDEX IF NOT EXISTS idx_influencers_sub_tier ON influencers(sub_tier) WHERE sub_tier IS NOT NULL;

DO $$
BEGIN CREATE TYPE influencer_subtier AS ENUM ('NANO_BAJO','NANO_ALTO','MICRO_BAJO','MICRO_MEDIO','MICRO_ALTO','MID_BAJO','MID_ALTO','MACRO_BAJO','MACRO_ALTO'); EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$
BEGIN CREATE TYPE candidate_status AS ENUM ('new','saved','dismissed','contacted','replied','won','lost'); EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$
BEGIN CREATE TYPE discovery_run_status AS ENUM ('pending','running','completed','failed','cancelled'); EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$
BEGIN CREATE TYPE conversation_step AS ENUM ('start','brief','refining','searching','ranking','candidates_review','done'); EXCEPTION WHEN OTHERS THEN NULL; END $$;

INSERT INTO schema_migrations (version, filename) VALUES
    ('97', '00000000000097_railway_patches.sql')
ON CONFLICT (version) DO NOTHING;
