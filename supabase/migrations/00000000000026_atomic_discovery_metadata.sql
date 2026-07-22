-- Migration: 00026_atomic_discovery_metadata_merge
-- Desc: RPC function for atomic metadata JSONB merge on discovery_runs
-- Fixes M5: eliminates read-modify-write race condition in _run_update_metadata

BEGIN;

CREATE OR REPLACE FUNCTION discovery_runs_merge_metadata(
    p_run_id UUID,
    p_metadata JSONB
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE discovery_runs
    SET
        metadata = (
            COALESCE(metadata, '{}'::jsonb) || p_metadata || '{"updated_at":"' || NOW()::TEXT || '"}'::jsonb
        ),
        updated_at = NOW()
    WHERE id = p_run_id;
END;
$$;

COMMENT ON FUNCTION discovery_runs_merge_metadata IS 'Atomically merges p_metadata into discovery_runs.metadata using JSONB || operator';

COMMIT;
