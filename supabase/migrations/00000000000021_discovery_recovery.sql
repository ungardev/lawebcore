-- =================================================================
-- LA WEB CORE - Migration 0021: Discovery Module Recovery
-- =================================================================
-- Re-aplica completo lo que migración 0019 intentó crear (y no pudo
-- por error 42P17: DATE_TRUNC not IMMUTABLE).
--
-- CONTEXTO HISTÓRICO:
-- - Migration 0019: falló al aplicar (transaction rolled back)
-- - Migration 0020: intentó arreglar solo el índice (pero la tabla
--   api_costs tampoco existía — 42P01: relation "api_costs" does not exist)
-- - Migration 0021: recovery completo — TODO en una sola ejecución
--
-- CORRECCIONES vs 0019 original:
-- - Wrapper IMMUTABLE date_trunc_month_immutable() antes de usarlo
-- - idx_api_costs_month usa la función wrapper, no DATE_TRUNC directa
--
-- EJECUTAR EN SQL EDITOR: un solo bloque, de principio a fin.
-- Es idempotente donde sea posible.
-- =================================================================

-- 1. Wrapper IMMUTABLE para DATE_TRUNC (fix del bug 42P17)
-- =================================================================
CREATE OR REPLACE FUNCTION public.date_trunc_month_immutable(ts TIMESTAMPTZ)
RETURNS TIMESTAMPTZ
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT date_trunc('month', ts AT TIME ZONE 'UTC');
$$;

COMMENT ON FUNCTION public.date_trunc_month_immutable(TIMESTAMPTZ) IS
  'Wraps DATE_TRUNC to make it IMMUTABLE by explicitly using UTC timezone.';

-- 2. Helper: updated_at trigger
-- =================================================================
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

-- 3. Enums (IF NOT EXISTS para idempotencia)
-- =================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'candidate_status') THEN
        CREATE TYPE candidate_status AS ENUM ('new', 'saved', 'dismissed', 'contacted', 'replied', 'won', 'lost');
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'discovery_run_status') THEN
        CREATE TYPE discovery_run_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'conversation_step') THEN
        CREATE TYPE conversation_step AS ENUM ('start', 'brief', 'refining', 'searching', 'ranking', 'candidates_review', 'done');
    END IF;
END $$;

-- 4. discovery_runs
-- =================================================================
CREATE TABLE IF NOT EXISTS discovery_runs (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    bu_id                   UUID REFERENCES business_units(id) ON DELETE SET NULL,
    created_by              UUID REFERENCES users(id) ON DELETE SET NULL,

    brief_text              TEXT NOT NULL,
    brief_parsed            JSONB,

    product_name            TEXT,
    brand_id                UUID REFERENCES brands(id) ON DELETE SET NULL,
    industry                TEXT,
    niches                  TEXT[],
    audience_gender         TEXT,
    audience_age_min        INTEGER,
    audience_age_max        INTEGER,
    audience_countries      TEXT[],
    audience_cities         TEXT[],
    budget_usd              NUMERIC(12,2),
    tone                    TEXT,
    platforms               TEXT[],

    status                  TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    total_candidates        INTEGER DEFAULT 0,
    accepted                INTEGER DEFAULT 0,
    estimated_cost_usd      NUMERIC(10,4),
    actual_cost_usd         NUMERIC(10,4),
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    error                   TEXT,
    metadata                JSONB DEFAULT '{}'::jsonb,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE discovery_runs IS 'Jobs de búsqueda de influencers. Un run puede tardar minutos ejecutándose en workers ARQ.';

CREATE INDEX IF NOT EXISTS idx_discovery_runs_status ON discovery_runs(status);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_created_by ON discovery_runs(created_by);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_brand ON discovery_runs(brand_id);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_created_at ON discovery_runs(created_at DESC);

CREATE TRIGGER trg_discovery_runs_updated_at BEFORE UPDATE ON discovery_runs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- 5. discovery_candidates
-- =================================================================
CREATE TABLE IF NOT EXISTS discovery_candidates (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    run_id                  UUID NOT NULL REFERENCES discovery_runs(id) ON DELETE CASCADE,

    platform                TEXT NOT NULL,
    platform_user_id        TEXT,
    handle                  TEXT NOT NULL,
    url                     TEXT,
    full_name               TEXT,
    bio                     TEXT,
    avatar_url              TEXT,

    country                 TEXT,
    city                    TEXT,
    language_primary        TEXT,

    followers               BIGINT,
    following              BIGINT,
    posts_count             INTEGER,
    avg_likes               INTEGER,
    avg_comments            INTEGER,
    avg_views               BIGINT,
    engagement_rate         NUMERIC(8,6),

    audience_credibility    NUMERIC(5,2),
    audience_quality        NUMERIC(5,2),
    audience_gender_split   JSONB,
    audience_age_buckets    JSONB,
    audience_top_countries  JSONB,
    audience_top_cities     JSONB,
    audience_interests       TEXT[],

    match_score             NUMERIC(5,2),
    niche_relevance         NUMERIC(5,2),
    geo_relevance           NUMERIC(5,2),
    audience_relevance      NUMERIC(5,2),
    content_quality         NUMERIC(5,2),
    rationale               TEXT,

    status                  TEXT NOT NULL DEFAULT 'new'
                            CHECK (status IN ('new', 'saved', 'dismissed', 'contacted', 'replied', 'won', 'lost')),
    saved_as_influencer_id  UUID REFERENCES influencers(id) ON DELETE SET NULL,

    contact_email           TEXT,
    contact_phone           TEXT,

    source_actor_run_id     TEXT,
    raw_payload             JSONB,
    fetched_at              TIMESTAMPTZ DEFAULT NOW(),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (run_id, platform, handle)
);

COMMENT ON TABLE discovery_candidates IS 'Candidatos encontrados por un discovery_run. Antes de aprobarse como influencer real.';

CREATE INDEX IF NOT EXISTS idx_discovery_candidates_run ON discovery_candidates(run_id);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_status ON discovery_candidates(status);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_platform ON discovery_candidates(platform);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_match_score ON discovery_candidates(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_country ON discovery_candidates(country);

CREATE TRIGGER trg_discovery_candidates_updated_at BEFORE UPDATE ON discovery_candidates
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- 6. discovery_conversations
-- =================================================================
CREATE TABLE IF NOT EXISTS discovery_conversations (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id                 UUID REFERENCES users(id) ON DELETE CASCADE,
    bu_id                   UUID REFERENCES business_units(id) ON DELETE SET NULL,

    state                   JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_step            TEXT CHECK (current_step IN ('start', 'brief', 'refining', 'searching', 'ranking', 'candidates_review', 'done')),

    discovery_run_id        UUID REFERENCES discovery_runs(id) ON DELETE SET NULL,

    accumulated_brief       TEXT,

    message_count           INTEGER DEFAULT 0,

    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status                  TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'completed', 'abandoned'))
);

COMMENT ON TABLE discovery_conversations IS 'Conversaciones del chat de discovery. Gestionada por LangGraph orchestrator.';

CREATE INDEX IF NOT EXISTS idx_discovery_conversations_user ON discovery_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_discovery_conversations_status ON discovery_conversations(status);
CREATE INDEX IF NOT EXISTS idx_discovery_conversations_last_message ON discovery_conversations(last_message_at DESC);

-- 7. discovery_messages
-- =================================================================
CREATE TABLE IF NOT EXISTS discovery_messages (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    conversation_id         UUID NOT NULL REFERENCES discovery_conversations(id) ON DELETE CASCADE,
    role                    TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content                 TEXT NOT NULL,

    tool_calls              JSONB,
    tool_results            JSONB,

    reasoning               TEXT,

    cost_usd                NUMERIC(10,6),
    latency_ms              INTEGER,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE discovery_messages IS 'Mensajes individuales dentro de una conversación de discovery.';

CREATE INDEX IF NOT EXISTS idx_discovery_messages_conversation ON discovery_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_discovery_messages_created_at ON discovery_messages(created_at);

-- 8. api_costs
-- =================================================================
CREATE TABLE IF NOT EXISTS api_costs (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    provider                TEXT NOT NULL,
    operation               TEXT,
    entity_id               UUID,

    cost_usd                NUMERIC(10,6) NOT NULL,
    request_count           INTEGER DEFAULT 1,

    tokens_input            INTEGER,
    tokens_output           INTEGER,

    metadata                JSONB DEFAULT '{}'::jsonb,
    occurred_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE api_costs IS 'Tracking de costos de todas las APIs externas (Apify, Meta, TikTok, YouTube, LLM providers).';

CREATE INDEX IF NOT EXISTS idx_api_costs_provider ON api_costs(provider, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_costs_entity ON api_costs(entity_id) WHERE entity_id IS NOT NULL;
-- Uso del wrapper IMMUTABLE (fix del bug 42P17 que tenía migration 0019):
CREATE INDEX IF NOT EXISTS idx_api_costs_month
  ON api_costs(public.date_trunc_month_immutable(occurred_at), provider);

-- 9. integration_credentials
-- =================================================================
CREATE TABLE IF NOT EXISTS integration_credentials (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    provider                TEXT NOT NULL,
    business_unit_id        UUID REFERENCES business_units(id) ON DELETE CASCADE,

    encrypted_credentials   JSONB NOT NULL,

    scopes                  TEXT[],

    status                  TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'expired', 'revoked', 'error')),

    expires_at              TIMESTAMPTZ,
    last_used_at            TIMESTAMPTZ,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (provider, business_unit_id)
);

COMMENT ON TABLE integration_credentials IS 'Credenciales encriptadas (pgcrypto) para APIs externas, por BU.';

CREATE INDEX IF NOT EXISTS idx_integration_credentials_provider ON integration_credentials(provider);
CREATE INDEX IF NOT EXISTS idx_integration_credentials_status ON integration_credentials(status);

CREATE TRIGGER trg_integration_credentials_updated_at BEFORE UPDATE ON integration_credentials
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- 10. Extensión: influencers (9 columnas nuevas)
-- =================================================================
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS gender TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS age_range TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS latitude NUMERIC(9,6);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS longitude NUMERIC(9,6);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS audience_demographics JSONB DEFAULT '{}'::jsonb;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS is_discoverable BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovery_query TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovery_confidence NUMERIC(5,2);

COMMENT ON COLUMN influencers.gender IS 'Género del influencer: female, male, non_binary, prefer_not_to_say';
COMMENT ON COLUMN influencers.age_range IS 'Rango etario: 18-24, 25-34, 35-44, 45-54, 55+';
COMMENT ON COLUMN influencers.is_discoverable IS 'Si FALSE, no aparece en resultados de discovery';
COMMENT ON COLUMN influencers.discovered_at IS 'Cuándo fue descubierto por el módulo de discovery';
COMMENT ON COLUMN influencers.discovery_query IS 'Query original que lo descubrió';

-- =================================================================
-- VALIDACIÓN: verificar que todo quedó creado
-- =================================================================
DO $$
BEGIN
    -- Verificar tablas
    PERFORM 1 FROM information_schema.tables WHERE table_name = 'discovery_runs';
    PERFORM 1 FROM information_schema.tables WHERE table_name = 'discovery_candidates';
    PERFORM 1 FROM information_schema.tables WHERE table_name = 'discovery_conversations';
    PERFORM 1 FROM information_schema.tables WHERE table_name = 'discovery_messages';
    PERFORM 1 FROM information_schema.tables WHERE table_name = 'api_costs';
    PERFORM 1 FROM information_schema.tables WHERE table_name = 'integration_credentials';

    -- Verificar índice修复
    PERFORM 1 FROM pg_indexes WHERE indexname = 'idx_api_costs_month';

    RAISE NOTICE 'Migration 0021 completada: discovery module creado exitosamente.';
END $$;
