-- =================================================================
-- LA WEB CORE - Migration 0019: Discovery Foundation
-- =================================================================
-- Tablas para el módulo de descubrimiento conversacional IA:
-- - discovery_runs: jobs de búsqueda en background
-- - discovery_candidates: candidatos encontrados antes de aprobarse
-- - discovery_conversations: conversaciones del chat de discovery
-- - discovery_messages: mensajes individuales
-- - api_costs: tracking de costos de APIs externas
-- - integration_credentials: credenciales encriptadas por BU
-- - Extensiones a influencers (8 columnas nuevas)
-- =================================================================

-- ---------- discovery_runs ----------
CREATE TABLE discovery_runs (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    bu_id                   UUID REFERENCES business_units(id) ON DELETE SET NULL,
    created_by              UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Brief en lenguaje natural
    brief_text              TEXT NOT NULL,
    brief_parsed            JSONB,  -- Output del LLM parser

    -- Criterios estructurados
    product_name            TEXT,
    brand_id                UUID REFERENCES brands(id) ON DELETE SET NULL,
    industry                TEXT,
    niches                  TEXT[],
    audience_gender         TEXT,   -- 'female' | 'male' | 'all'
    audience_age_min        INTEGER,
    audience_age_max        INTEGER,
    audience_countries      TEXT[],
    audience_cities         TEXT[],
    budget_usd              NUMERIC(12,2),
    tone                    TEXT,
    platforms               TEXT[], -- ['instagram', 'tiktok', 'youtube']

    -- Estado del job
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

CREATE INDEX idx_discovery_runs_status ON discovery_runs(status);
CREATE INDEX idx_discovery_runs_created_by ON discovery_runs(created_by);
CREATE INDEX idx_discovery_runs_brand ON discovery_runs(brand_id);
CREATE INDEX idx_discovery_runs_created_at ON discovery_runs(created_at DESC);

-- ---------- discovery_candidates ----------
CREATE TABLE discovery_candidates (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    run_id                  UUID NOT NULL REFERENCES discovery_runs(id) ON DELETE CASCADE,

    -- Identidad del candidato
    platform                TEXT NOT NULL,
    platform_user_id        TEXT,
    handle                  TEXT NOT NULL,
    url                     TEXT,
    full_name               TEXT,
    bio                     TEXT,
    avatar_url              TEXT,

    -- Ubicación
    country                 TEXT,
    city                    TEXT,
    language_primary        TEXT,

    -- Métricas scrapeadas
    followers               BIGINT,
    following              BIGINT,
    posts_count             INTEGER,
    avg_likes               INTEGER,
    avg_comments            INTEGER,
    avg_views               BIGINT,
    engagement_rate         NUMERIC(8,6),

    -- Calidad de audiencia
    audience_credibility    NUMERIC(5,2),
    audience_quality        NUMERIC(5,2),
    audience_gender_split   JSONB,
    audience_age_buckets    JSONB,
    audience_top_countries  JSONB,
    audience_top_cities     JSONB,
    audience_interests       TEXT[],

    -- Scoring (sobre 100)
    match_score             NUMERIC(5,2),
    niche_relevance         NUMERIC(5,2),
    geo_relevance           NUMERIC(5,2),
    audience_relevance      NUMERIC(5,2),
    content_quality         NUMERIC(5,2),
    rationale               TEXT,  -- Por qué DeepSeek lo seleccionó

    -- Estado del candidato
    status                  TEXT NOT NULL DEFAULT 'new'
                            CHECK (status IN ('new', 'saved', 'dismissed', 'contacted', 'replied', 'won', 'lost')),
    saved_as_influencer_id  UUID REFERENCES influencers(id) ON DELETE SET NULL,

    -- Contacto
    contact_email           TEXT,
    contact_phone           TEXT,

    -- Source
    source_actor_run_id     TEXT,
    raw_payload             JSONB,
    fetched_at              TIMESTAMPTZ DEFAULT NOW(),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (run_id, platform, handle)
);

COMMENT ON TABLE discovery_candidates IS 'Candidatos encontrados por un discovery_run. Antes de aprobarse como influencer real.';

CREATE INDEX idx_discovery_candidates_run ON discovery_candidates(run_id);
CREATE INDEX idx_discovery_candidates_status ON discovery_candidates(status);
CREATE INDEX idx_discovery_candidates_platform ON discovery_candidates(platform);
CREATE INDEX idx_discovery_candidates_match_score ON discovery_candidates(match_score DESC);
CREATE INDEX idx_discovery_candidates_country ON discovery_candidates(country);

-- ---------- discovery_conversations ----------
CREATE TABLE discovery_conversations (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id                 UUID REFERENCES users(id) ON DELETE CASCADE,
    bu_id                   UUID REFERENCES business_units(id) ON DELETE SET NULL,

    -- Estado de la máquina de estados LangGraph
    state                   JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_step            TEXT CHECK (current_step IN ('start', 'brief', 'refining', 'searching', 'ranking', 'candidates_review', 'done')),

    -- Run asociado (cuando se ejecuta una búsqueda)
    discovery_run_id        UUID REFERENCES discovery_runs(id) ON DELETE SET NULL,

    -- Contexto acumulado del brief
    accumulated_brief       TEXT,

    -- Stats
    message_count           INTEGER DEFAULT 0,

    -- Timestamps
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status                  TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'completed', 'abandoned'))
);

COMMENT ON TABLE discovery_conversations IS 'Conversaciones del chat de discovery. Gestionada por LangGraph orchestrator.';

CREATE INDEX idx_discovery_conversations_user ON discovery_conversations(user_id);
CREATE INDEX idx_discovery_conversations_status ON discovery_conversations(status);
CREATE INDEX idx_discovery_conversations_last_message ON discovery_conversations(last_message_at DESC);

-- ---------- discovery_messages ----------
CREATE TABLE discovery_messages (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    conversation_id         UUID NOT NULL REFERENCES discovery_conversations(id) ON DELETE CASCADE,
    role                    TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content                 TEXT NOT NULL,

    -- Function calls cuando el LLM usa herramientas (Apify, Meta, etc.)
    tool_calls              JSONB,
    tool_results            JSONB,

    -- Razonamiento visible (DeepSeek-R1 o similar)
    reasoning               TEXT,

    -- Cost tracking
    cost_usd                NUMERIC(10,6),
    latency_ms              INTEGER,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE discovery_messages IS 'Mensajes individuales dentro de una conversación de discovery.';

CREATE INDEX idx_discovery_messages_conversation ON discovery_messages(conversation_id);
CREATE INDEX idx_discovery_messages_created_at ON discovery_messages(created_at);

-- ---------- api_costs ----------
CREATE TABLE api_costs (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    provider                TEXT NOT NULL,
    operation               TEXT,
    entity_id               UUID,  -- Puede referenciar run_id, candidate_id, message_id, etc.

    cost_usd                NUMERIC(10,6) NOT NULL,
    request_count           INTEGER DEFAULT 1,

    -- Tokens (para LLM calls)
    tokens_input            INTEGER,
    tokens_output           INTEGER,

    metadata                JSONB DEFAULT '{}'::jsonb,
    occurred_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE api_costs IS 'Tracking de costos de todas las APIs externas (Apify, Meta, TikTok, YouTube, LLM providers).';

CREATE INDEX idx_api_costs_provider ON api_costs(provider, occurred_at DESC);
CREATE INDEX idx_api_costs_entity ON api_costs(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_api_costs_month ON api_costs(DATE_TRUNC('month', occurred_at), provider);

-- ---------- integration_credentials ----------
CREATE TABLE integration_credentials (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    provider                TEXT NOT NULL,
    business_unit_id        UUID REFERENCES business_units(id) ON DELETE CASCADE,

    -- Credenciales encriptadas con pgcrypto
    encrypted_credentials   JSONB NOT NULL,

    -- OAuth scopes concedidos
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

CREATE INDEX idx_integration_credentials_provider ON integration_credentials(provider);
CREATE INDEX idx_integration_credentials_status ON integration_credentials(status);

-- ---------- Extension: influencers ----------
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

-- ---------- Extension: candidate_status enum ----------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'candidate_status') THEN
        CREATE TYPE candidate_status AS ENUM ('new', 'saved', 'dismissed', 'contacted', 'replied', 'won', 'lost');
    ELSE
        -- Add missing values if enum already exists
        ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'new';
        ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'saved';
        ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'dismissed';
        ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'contacted';
        ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'replied';
        ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'won';
        ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'lost';
    END IF;
END $$;

-- ---------- Extension: discovery_run_status enum ----------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'discovery_run_status') THEN
        CREATE TYPE discovery_run_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
    ELSE
        ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'pending';
        ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'running';
        ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'completed';
        ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'failed';
        ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'cancelled';
    END IF;
END $$;

-- ---------- Extension: conversation_step enum ----------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'conversation_step') THEN
        CREATE TYPE conversation_step AS ENUM ('start', 'brief', 'refining', 'searching', 'ranking', 'candidates_review', 'done');
    ELSE
        ALTER TYPE conversation_step ADD VALUE IF NOT EXISTS 'start';
        ALTER TYPE conversation_step ADD VALUE IF NOT EXISTS 'brief';
        ALTER TYPE conversation_step ADD VALUE IF NOT EXISTS 'refining';
        ALTER TYPE conversation_step ADD VALUE IF NOT EXISTS 'searching';
        ALTER TYPE conversation_step ADD VALUE IF NOT EXISTS 'ranking';
        ALTER TYPE conversation_step ADD VALUE IF NOT EXISTS 'candidates_review';
        ALTER TYPE conversation_step ADD VALUE IF NOT EXISTS 'done';
    END IF;
END $$;

-- ---------- Updated_at trigger ----------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_discovery_runs_updated_at BEFORE UPDATE ON discovery_runs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_discovery_candidates_updated_at BEFORE UPDATE ON discovery_candidates
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_discovery_conversations_updated_at BEFORE UPDATE ON discovery_conversations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_integration_credentials_updated_at BEFORE UPDATE ON integration_credentials
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
