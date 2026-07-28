-- =================================================================
-- Railway patches: repair broken discovery tables from partial bootstrap
-- Run FIRST before applying any other migrations
-- =================================================================
-- Problem: the original bootstrap ran as single batch and failed partway.
-- discovery_runs exists but is missing columns added in later phases.
-- discovery_candidates exists but id DEFAULT may not work.
-- discovery_runs_merge_metadata references updated_at which doesn't exist.

-- ---------- Fix 1: Add missing columns to discovery_runs ----------
ALTER TABLE discovery_runs ADD COLUMN IF NOT EXISTS audience_cities TEXT[];
ALTER TABLE discovery_runs ADD COLUMN IF NOT EXISTS estimated_cost_usd NUMERIC(10,4);
ALTER TABLE discovery_runs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- ---------- Fix 2: Ensure discovery_candidates id has DEFAULT ----------
ALTER TABLE discovery_candidates ALTER COLUMN id SET DEFAULT extensions.uuid_generate_v4();

-- ---------- Fix 3: Recreate discovery_runs_merge_metadata correctly ----------
CREATE OR REPLACE FUNCTION discovery_runs_merge_metadata(p_run_id UUID, p_metadata JSONB)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE discovery_runs
    SET metadata = COALESCE(metadata, '{}'::jsonb) || p_metadata,
        updated_at = NOW()
    WHERE id = p_run_id;
END;
$$;

COMMENT ON FUNCTION discovery_runs_merge_metadata IS 'Atomically merges p_metadata into discovery_runs.metadata using JSONB || operator';

-- ---------- Fix 4: Ensure discovery triggers exist ----------
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

-- ---------- Fix 5: Add missing columns to discovery_candidates (0022, 0024, 0028) ----------
ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS tier TEXT CHECK (tier IN ('NANO','MICRO','MID','MACRO'));
ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS is_tienda BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS language_primary TEXT;

CREATE INDEX IF NOT EXISTS idx_discovery_candidates_tier ON discovery_candidates(tier);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_is_tienda ON discovery_candidates(is_tienda);

-- ---------- Fix 6: Ensure influencers has discovery columns (0019) ----------
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

-- ---------- Fix 7: Ensure extensiones enum exists ----------
DO $$
BEGIN
    CREATE TYPE influencer_subtier AS ENUM (
        'NANO_BAJO','NANO_ALTO',
        'MICRO_BAJO','MICRO_MEDIO','MICRO_ALTO',
        'MID_BAJO','MID_ALTO',
        'MACRO_BAJO','MACRO_ALTO'
    );
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE candidate_status AS ENUM ('new','saved','dismissed','contacted','replied','won','lost');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE discovery_run_status AS ENUM ('pending','running','completed','failed','cancelled');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE conversation_step AS ENUM ('start','brief','refining','searching','ranking','candidates_review','done');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- ---------- Fix 8: Ensure set_updated_at helper exists ----------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;
