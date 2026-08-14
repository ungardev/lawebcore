-- Hito 18: Externalize vocabulary from worker.py to discovery_profiles table
-- Adds configurable signal keywords per discovery profile (vertical/client)

BEGIN;

ALTER TABLE discovery_profiles
  ADD COLUMN IF NOT EXISTS commerce_signal_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS creator_signal_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS exclusion_keywords JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN discovery_profiles.commerce_signal_keywords IS 'List of keywords that indicate a commerce/shop profile, e.g. ["tienda","shop","ventas"]';
COMMENT ON COLUMN discovery_profiles.creator_signal_keywords IS 'List of keywords that indicate a creator/influencer profile, e.g. ["influencer","youtuber","content creator"]';
COMMENT ON COLUMN discovery_profiles.exclusion_keywords IS 'List of keywords that cause a profile to be filtered out (brand safety), e.g. political terms';

CREATE INDEX IF NOT EXISTS idx_discovery_profiles_commerce_signal ON discovery_profiles USING GIN (commerce_signal_keywords);
CREATE INDEX IF NOT EXISTS idx_discovery_profiles_creator_signal ON discovery_profiles USING GIN (creator_signal_keywords);
CREATE INDEX IF NOT EXISTS idx_discovery_profiles_exclusion ON discovery_profiles USING GIN (exclusion_keywords);

COMMIT;
