-- Migration 0099: Discovery performance indexes
-- Adds composite indexes for the most common Lens query patterns.

-- Candidates: lookup by run + score ordering (top candidates per run)
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_run_match
  ON discovery_candidates(run_id, match_score DESC);

-- Candidates: dedup handle+platform (upsert target)
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_handle_platform
  ON discovery_candidates(platform, handle);

-- Runs: active runs by status + recency (health monitoring)
CREATE INDEX IF NOT EXISTS idx_discovery_runs_status_started
  ON discovery_runs(status, started_at DESC);

-- API costs: monthly cost aggregation by provider
CREATE INDEX IF NOT EXISTS idx_api_costs_provider_occurred
  ON api_costs(provider, occurred_at DESC);
