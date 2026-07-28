-- =================================================================
-- LA WEB CORE — Railway Bootstrap Part 5 of 5 (FINAL)
-- Discovery tables + Migration tracking + Mark all applied
-- Run in Railway Query Editor FIFTH (LAST)
-- =================================================================

-- Discovery enums
DO $$ BEGIN CREATE TYPE candidate_status AS ENUM ('new','saved','dismissed','contacted','replied','won','lost'); EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE discovery_run_status AS ENUM ('pending','running','completed','failed','cancelled'); EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE conversation_step AS ENUM ('start','brief','refining','searching','ranking','candidates_review','done'); EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- discovery_runs
CREATE TABLE IF NOT EXISTS discovery_runs (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    bu_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    brief_text TEXT NOT NULL, brief_parsed JSONB,
    product_name TEXT, brand_id UUID REFERENCES brands(id) ON DELETE SET NULL,
    industry TEXT, niches TEXT[], audience_gender TEXT,
    audience_age_min INTEGER, audience_age_max INTEGER,
    audience_countries TEXT[], audience_cities TEXT[],
    budget_usd NUMERIC(12,2), tone TEXT, platforms TEXT[],
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed','cancelled')),
    total_candidates INTEGER DEFAULT 0, accepted INTEGER DEFAULT 0,
    estimated_cost_usd NUMERIC(10,4), actual_cost_usd NUMERIC(10,4),
    started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, error TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_status ON discovery_runs(status);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_created_by ON discovery_runs(created_by);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_brand ON discovery_runs(brand_id);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_created_at ON discovery_runs(created_at DESC);

-- discovery_candidates
CREATE TABLE IF NOT EXISTS discovery_candidates (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES discovery_runs(id) ON DELETE CASCADE,
    platform TEXT NOT NULL, platform_user_id TEXT, handle TEXT NOT NULL,
    url TEXT, full_name TEXT, bio TEXT, avatar_url TEXT,
    country TEXT, city TEXT, language_primary TEXT,
    followers BIGINT, following BIGINT, posts_count INTEGER,
    avg_likes INTEGER, avg_comments INTEGER, avg_views BIGINT,
    engagement_rate NUMERIC(8,6),
    audience_credibility NUMERIC(5,2), audience_quality NUMERIC(5,2),
    audience_gender_split JSONB, audience_age_buckets JSONB,
    audience_top_countries JSONB, audience_top_cities JSONB, audience_interests TEXT[],
    match_score NUMERIC(5,2), niche_relevance NUMERIC(5,2),
    geo_relevance NUMERIC(5,2), audience_relevance NUMERIC(5,2),
    content_quality NUMERIC(5,2), rationale TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','saved','dismissed','contacted','replied','won','lost')),
    saved_as_influencer_id UUID REFERENCES influencers(id) ON DELETE SET NULL,
    contact_email TEXT, contact_phone TEXT,
    source_actor_run_id TEXT, raw_payload JSONB, fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tier TEXT CHECK (tier IN ('NANO','MICRO','MID','MACRO')),
    is_tienda BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (run_id, platform, handle)
);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_run ON discovery_candidates(run_id);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_status ON discovery_candidates(status);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_platform ON discovery_candidates(platform);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_match_score ON discovery_candidates(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_country ON discovery_candidates(country);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_tier ON discovery_candidates(tier);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_is_tienda ON discovery_candidates(is_tienda);

-- discovery_conversations
CREATE TABLE IF NOT EXISTS discovery_conversations (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    bu_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_step TEXT CHECK (current_step IN ('start','brief','refining','searching','ranking','candidates_review','done')),
    discovery_run_id UUID REFERENCES discovery_runs(id) ON DELETE SET NULL,
    accumulated_brief TEXT, message_count INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','abandoned'))
);
CREATE INDEX IF NOT EXISTS idx_discovery_conversations_user ON discovery_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_discovery_conversations_status ON discovery_conversations(status);
CREATE INDEX IF NOT EXISTS idx_discovery_conversations_last_message ON discovery_conversations(last_message_at DESC);

-- discovery_messages
CREATE TABLE IF NOT EXISTS discovery_messages (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES discovery_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','tool')),
    content TEXT NOT NULL, tool_calls JSONB, tool_results JSONB,
    reasoning TEXT, cost_usd NUMERIC(10,6), latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_discovery_messages_conversation ON discovery_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_discovery_messages_created_at ON discovery_messages(created_at);

-- api_costs
CREATE TABLE IF NOT EXISTS api_costs (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    provider TEXT NOT NULL, operation TEXT, entity_id UUID,
    cost_usd NUMERIC(10,6) NOT NULL, request_count INTEGER DEFAULT 1,
    tokens_input INTEGER, tokens_output INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb, occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_costs_provider ON api_costs(provider, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_costs_entity ON api_costs(entity_id) WHERE entity_id IS NOT NULL;

-- integration_credentials
CREATE TABLE IF NOT EXISTS integration_credentials (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    provider TEXT NOT NULL, business_unit_id UUID REFERENCES business_units(id) ON DELETE CASCADE,
    encrypted_credentials JSONB NOT NULL, scopes TEXT[],
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','expired','revoked','error')),
    expires_at TIMESTAMPTZ, last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, business_unit_id)
);
CREATE INDEX IF NOT EXISTS idx_integration_credentials_provider ON integration_credentials(provider);
CREATE INDEX IF NOT EXISTS idx_integration_credentials_status ON integration_credentials(status);

-- Influencer discovery columns
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS gender TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS age_range TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS latitude NUMERIC(9,6);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS longitude NUMERIC(9,6);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS audience_demographics JSONB DEFAULT '{}'::jsonb;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS is_discoverable BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovery_query TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovery_confidence NUMERIC(5,2);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS sub_tier TEXT;

CREATE INDEX IF NOT EXISTS idx_influencers_sub_tier ON influencers(sub_tier) WHERE sub_tier IS NOT NULL;

-- Discovery triggers
CREATE TRIGGER trg_discovery_runs_updated_at BEFORE UPDATE ON discovery_runs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_discovery_candidates_updated_at BEFORE UPDATE ON discovery_candidates
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_discovery_conversations_updated_at BEFORE UPDATE ON discovery_conversations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_integration_credentials_updated_at BEFORE UPDATE ON integration_credentials
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RPC: discovery_runs_merge_metadata
CREATE OR REPLACE FUNCTION discovery_runs_merge_metadata(p_run_id UUID, p_metadata JSONB)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE discovery_runs
    SET metadata = COALESCE(metadata, '{}'::jsonb) || p_metadata,
        updated_at = NOW()
    WHERE id = p_run_id;
END; $$;

-- Migration tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY, filename TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), checksum TEXT
);

-- Mark ALL migrations as applied (idempotent — ON CONFLICT DO NOTHING)
INSERT INTO schema_migrations (version, filename) VALUES
    ('1',  '00000000000001_extensions.sql'),
    ('2',  '00000000000002_enums.sql'),
    ('3',  '00000000000003_identity.sql'),
    ('4',  '00000000000004_commercial.sql'),
    ('5',  '00000000000005_influencers.sql'),
    ('6',  '00000000000006_campaigns.sql'),
    ('7',  '00000000000007_kpis.sql'),
    ('8',  '00000000000008_operations.sql'),
    ('9',  '00000000000009_ai.sql'),
    ('10', '00000000000010_audit_integrations.sql'),
    ('11', '00000000000011_rls.sql'),
    ('12', '00000000000012_data_quality.sql'),
    ('15', '00000000000015_piar_foundation.sql'),
    ('16', '00000000000016_benchmarks_lwfa.sql'),
    ('17', '00000000000017_sentiment_analysis.sql'),
    ('18', '00000000000018_migration_tracking.sql'),
    ('19', '00000000000019_discovery_foundation.sql'),
    ('20', '00000000000020_api_costs_index_fix.sql'),
    ('21', '00000000000021_discovery_recovery.sql'),
    ('22', '00000000000022_discovery_candidates_additions.sql'),
    ('23', '00000000000023_embeddings_384.sql'),
    ('24', '00000000000024_enrichment_columns.sql'),
    ('26', '00000000000026_atomic_discovery_metadata.sql'),
    ('27', '00000000000027_rls_discovery_tables.sql'),
    ('28', '00000000000028_discovery_tier_persistence.sql'),
    ('p1', '0000_02_railway_bootstrap_p1.sql'),
    ('p2', '0000_03_railway_bootstrap_p2.sql'),
    ('p3', '0000_04_railway_bootstrap_p3.sql'),
    ('p4', '0000_05_railway_bootstrap_p4.sql'),
    ('p5', '0000_06_railway_bootstrap_p5.sql')
ON CONFLICT (version) DO NOTHING;

-- Final smoke test
DO $$
DECLARE cnt INTEGER;
BEGIN
    SELECT COUNT(*) INTO cnt FROM information_schema.tables WHERE table_schema = 'public';
    RAISE NOTICE '=== LA WEB CORE RAILWAY BOOTSTRAP COMPLETE ===';
    RAISE NOTICE 'Public tables: %', cnt;
END $$;
