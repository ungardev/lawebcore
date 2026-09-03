-- Migration: 00111_discovery_candidates_discovery_query
-- Add discovery_query TEXT column to discovery_candidates
-- Fix: worker.py:1620 writes discovery_query but column didn't exist in schema
-- Issue: H-2 — 4th case of _discovery_query → discovery_query dual-name pattern

ALTER TABLE discovery_candidates
ADD COLUMN IF NOT EXISTS discovery_query TEXT DEFAULT '';

COMMENT ON COLUMN discovery_candidates.discovery_query IS 'Query original que lo descubrió (hashtag/keyword/location/reels/topsearch/suggested)';
