-- =================================================================
-- Remove budget client fields from discovery
-- Budget (budget_usd) was a client-facing cost field used to determine
-- tier selection. We now rely solely on follower-based tiers and the
-- agency negotiates pricing directly.
-- Version 98
-- =================================================================

-- Remove budget_usd from discovery_runs (client budget, not API cost)
ALTER TABLE discovery_runs DROP COLUMN IF EXISTS budget_usd;

-- Remove estimated_cost from discovery_candidates (derived cost estimate, not needed)
-- expected_reach, expected_engagement, roi_estimate are kept as performance metrics
ALTER TABLE discovery_candidates DROP COLUMN IF EXISTS estimated_cost;

-- Update schema_migrations
INSERT INTO schema_migrations (version, filename) VALUES
    ('98', '00000000000098_remove_budget_cost_fields.sql')
ON CONFLICT (version) DO NOTHING;
