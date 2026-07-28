-- =================================================================
-- Migration 0028: Persist tier and is_tienda to discovery_candidates
-- Previously computed on-the-fly in _serialize_candidate().
-- Now computed once at insert time in discovery_run_task and stored
-- as a proper column for efficient filtering and display.
-- =================================================================

ALTER TABLE discovery_candidates
    ADD COLUMN IF NOT EXISTS tier TEXT CHECK (tier IN ('NANO', 'MICRO', 'MID', 'MACRO')),
    ADD COLUMN IF NOT EXISTS is_tienda BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN discovery_candidates.tier IS 'Influencer tier based on follower count: NANO (<10k), MICRO (<100k), MID (<500k), MACRO (500k+)';
COMMENT ON COLUMN discovery_candidates.is_tienda IS 'True if bio contains tienda/shop patterns indicating a commercial account';

CREATE INDEX IF NOT EXISTS idx_discovery_candidates_tier ON discovery_candidates(tier);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_is_tienda ON discovery_candidates(is_tienda);
