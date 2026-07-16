-- =============================================================================
-- Migration: 00022_discovery_candidates_additions
-- Purpose: Add columns that were referenced in code but never added to the table
--   - expected_reach, expected_engagement: shown in frontend insights
--   - estimated_cost: cost estimation per candidate
--   - roi_estimate: ROI estimation
-- =============================================================================

ALTER TABLE discovery_candidates
    ADD COLUMN IF NOT EXISTS estimated_cost      NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS expected_reach      INTEGER,
    ADD COLUMN IF NOT EXISTS expected_engagement NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS roi_estimate        NUMERIC(10,4);
