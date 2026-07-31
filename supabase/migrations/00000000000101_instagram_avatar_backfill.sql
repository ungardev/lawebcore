-- Migration 0101: Backfill Instagram avatar URLs for existing candidates
-- Constructs public Instagram profile picture URL for candidates where avatar_url is NULL

UPDATE discovery_candidates
SET avatar_url = 'https://instagram.com/' || handle || '/profile_picture'
WHERE platform = 'instagram'
  AND avatar_url IS NULL
  AND handle IS NOT NULL
  AND handle != '';
