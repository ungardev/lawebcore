-- =================================================================
-- Migration 0024: Enrichment Metric Columns
-- Adds columns required by enrich_influencers endpoint so that
-- Apify profile data (followers, ER, etc.) can be stored directly
-- on the influencers table instead of only in metrics snapshots.
-- =================================================================

ALTER TABLE influencers ADD COLUMN IF NOT EXISTS platform TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS followers BIGINT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS following BIGINT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS posts_count INTEGER;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS avg_likes NUMERIC(12, 2);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS avg_comments NUMERIC(12, 2);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS engagement_rate NUMERIC(6, 4);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS audience_credibility NUMERIC(5, 2);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS profile_pic_url TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;
