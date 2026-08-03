-- =================================================================
-- Add brand_fit and ai_rationale columns to discovery_candidates
-- These columns store AI-generated quality scores and rationales
-- from the DeepSeek analyzer in STEP 5 of the discovery pipeline
-- Version 99
-- =================================================================

ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS brand_fit INTEGER DEFAULT NULL;
ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS ai_rationale TEXT DEFAULT NULL;

INSERT INTO schema_migrations (version, filename) VALUES
    ('99', '00000000000099_add_brand_fit_and_ai_rationale.sql')
ON CONFLICT (version) DO NOTHING;
