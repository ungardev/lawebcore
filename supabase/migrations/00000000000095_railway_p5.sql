-- =================================================================
-- Railway Bootstrap P5 — Discovery tables + Migration tracking
-- Version 95 — runs AFTER existing migrations 1-28
-- Mark all railway bootstrap migrations as applied in schema_migrations
-- Idempotent: uses CREATE TABLE IF NOT EXISTS + ON CONFLICT DO NOTHING
-- =================================================================

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

CREATE TABLE IF NOT EXISTS api_costs (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    provider TEXT NOT NULL, operation TEXT, entity_id UUID,
    cost_usd NUMERIC(10,6) NOT NULL, request_count INTEGER DEFAULT 1,
    tokens_input INTEGER, tokens_output INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb, occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_costs_provider ON api_costs(provider, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_costs_entity ON api_costs(entity_id) WHERE entity_id IS NOT NULL;

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

CREATE TRIGGER trg_discovery_runs_updated_at BEFORE UPDATE ON discovery_runs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_discovery_candidates_updated_at BEFORE UPDATE ON discovery_candidates
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_discovery_conversations_updated_at BEFORE UPDATE ON discovery_conversations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_integration_credentials_updated_at BEFORE UPDATE ON integration_credentials
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE OR REPLACE FUNCTION discovery_runs_merge_metadata(p_run_id UUID, p_metadata JSONB)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE discovery_runs
    SET metadata = COALESCE(metadata, '{}'::jsonb) || p_metadata,
        updated_at = NOW()
    WHERE id = p_run_id;
END; $$;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY, filename TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), checksum TEXT
);

INSERT INTO schema_migrations (version, filename) VALUES
    ('91', '00000000000091_railway_p1.sql'),
    ('92', '00000000000092_railway_p2.sql'),
    ('93', '00000000000093_railway_p3.sql'),
    ('94', '00000000000094_railway_p4.sql'),
    ('95', '00000000000095_railway_p5.sql'),
    ('96', '00000000000096_railway_remaining.sql'),
    ('97', '00000000000097_railway_patches.sql')
ON CONFLICT (version) DO NOTHING;

DO $$
DECLARE cnt INTEGER;
BEGIN
    SELECT COUNT(*) INTO cnt FROM information_schema.tables WHERE table_schema = 'public';
    RAISE NOTICE '=== Railway Bootstrap P5 complete — % tables ===', cnt;
END $$;
