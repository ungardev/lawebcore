-- =============================================================================
-- RAILWAY POSTGRESQL BOOTSTRAP — La Web Core
-- =============================================================================
-- Single-file migration for Railway PostgreSQL.
-- Consolidates migrations 0001–0018 + 0019–0028 (already applied on prod).
-- Safe to re-run: uses IF NOT EXISTS / CREATE OR REPLACE throughout.
--
-- WHY: The original migrations were written for Supabase (auth schema, RLS,
-- role-based grants). Railway PostgreSQL is vanilla PostgreSQL.
-- This file adapts them for Railway with:
--   • Stub auth schema (auth.users + auth.uid())
--   • RLS policies OMITTED (asyncpg connects as postgres superuser)
--   • Grants simplified to PUBLIC
--   • Extensions installed in 'extensions' schema
--   • All ENUMs and tables created in dependency order
-- =============================================================================

-- =============================================================================
-- PHASE 0: Bootstrap schemas and extensions
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE SCHEMA IF NOT EXISTS auth;

-- uuid-ossp: provides uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA extensions;

-- pgcrypto: provides gen_random_uuid(), also used for auth
CREATE EXTENSION IF NOT EXISTS "pgcrypto" SCHEMA extensions;

-- pg_trgm: used for fuzzy text search on handles/bios
CREATE EXTENSION IF NOT EXISTS "pg_trgm" SCHEMA extensions;

-- pgvector: required for AI/RAG vector search (migration 0009).
-- If not available (Railway Starter plan), skip AI features.
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS "vector" SCHEMA extensions;
  RAISE NOTICE 'pgvector extension installed successfully';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'pgvector not available on this Railway plan — AI/RAG features disabled (non-critical for discovery pipeline)';
END $$;

GRANT USAGE ON SCHEMA extensions TO PUBLIC;
GRANT ALL ON SCHEMA extensions TO postgres;

-- =============================================================================
-- PHASE 1: Stub auth schema (satisfied FK references from users table)
-- =============================================================================
-- The original migrations reference auth.users(id) as FK.
-- In Railway we stub this table. The API never validates these FKs
-- (it connects as postgres superuser via asyncpg), so this is safe.
CREATE TABLE IF NOT EXISTS auth.users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- auth.uid() is called in some triggers. Stub it to return NULL
-- so triggers don't break (postgres superuser has no session auth context).
CREATE OR REPLACE FUNCTION auth.uid() RETURNS UUID
    LANGUAGE sql STABLE
    RETURN COALESCE(
        NULLIF(current_setting('request.jwt.claim.sub', true), '')::UUID,
        '00000000-0000-0000-0000-000000000000'::UUID
    );

-- =============================================================================
-- PHASE 2: Enums (migration 0002 — no Supabase dependencies)
-- =============================================================================
CREATE TYPE user_status AS ENUM ('active', 'invited', 'suspended', 'deactivated');

CREATE TYPE campaign_status AS ENUM (
    'BRIEF','CONTACTANDO','PLAN_DE_CUENTAS','PULL',
    'CAMPAÑA INTERNA','REPORTE','TERMINADA','CANCELADA','PAUSADA'
);

CREATE TYPE campaign_objective AS ENUM (
    'AWARENESS','CONSIDERACION','CONVERSION','GESTION_DE_CRISIS',
    'BRANDING','LANZAMIENTO','RETENCION'
);

CREATE TYPE influencer_tier AS ENUM ('NANO','MICRO','MID','MACRO','MEGA','MIX');

CREATE TYPE campaign_influencer_status AS ENUM (
    'PROPUESTO','CONTACTADO','CONFIRMADO','CONTRATADO',
    'CONTENIDO_ENTREGADO','PAGADO','RECHAZADO','CANCELADO'
);

CREATE TYPE campaign_link_type AS ENUM (
    'BRIEF','DOCUMENTO_INDUCCION','CONTRATO','HOOK','AUTOMATIZACION',
    'FORMULARIO','PULL','PLAN_DE_CUENTAS','CAMPANA_INTERNA','DRIVE',
    'REPORTE','CANVA','TRELLO','HYPEAUDITOR','OTRO'
);

CREATE TYPE kpi_category AS ENUM (
    'ALCANCE','ENGAGEMENT','CONVERSION','RETENCION',
    'AWARENESS','SENTIMIENTO','BRAND_HEALTH'
);

CREATE TYPE kpi_source AS ENUM (
    'MANUAL','HYPEAUDITOR','PLATAFORMA_NATIVA','FORMULARIO','IMPORTADO','IA'
);

CREATE TYPE task_status AS ENUM ('PENDIENTE','EN_PROGRESO','BLOQUEADA','COMPLETADA','CANCELADA');
CREATE TYPE task_priority AS ENUM ('BAJA','MEDIA','ALTA','URGENTE');

CREATE TYPE integration_provider AS ENUM (
    'HYPEAUDITOR','CANVA','GOOGLE_DRIVE','TRELLO','SLACK',
    'META','TIKTOK','YOUTUBE','OPENAI','ANTHROPIC'
);

CREATE TYPE ai_job_status AS ENUM ('PENDING','RUNNING','COMPLETED','FAILED','CANCELLED');

CREATE TYPE ai_job_type AS ENUM (
    'EMBEDDING','RAG_QUERY','BRIEF_GENERATION','POST_MORTEM_GENERATION',
    'INSIGHT_GENERATION','FORECAST','MATCHMAKING','SENTIMENT_ANALYSIS'
);

CREATE TYPE audit_action AS ENUM (
    'CREATE','UPDATE','DELETE','RESTORE',
    'LOGIN','LOGOUT','EXPORT','IMPORT',
    'STATUS_CHANGE','PERMISSION_CHANGE','ROLE_CHANGE'
);

-- =============================================================================
-- PHASE 3: Identity & Permissions (migration 0003 adapted)
-- =============================================================================

-- shared helper
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

CREATE TABLE IF NOT EXISTS business_units (
    id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    email               TEXT NOT NULL UNIQUE,
    full_name           TEXT NOT NULL,
    avatar_url          TEXT,
    phone               TEXT,
    job_title           TEXT,
    primary_bu_id       UUID REFERENCES business_units(id) ON DELETE SET NULL,
    status              user_status NOT NULL DEFAULT 'invited',
    locale              TEXT NOT NULL DEFAULT 'es-VE',
    timezone            TEXT NOT NULL DEFAULT 'America/Caracas',
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_primary_bu ON users(primary_bu_id);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

CREATE TABLE IF NOT EXISTS roles (
    id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT,
    is_system   BOOLEAN NOT NULL DEFAULT FALSE,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permissions (
    id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code        TEXT NOT NULL UNIQUE,
    resource    TEXT NOT NULL,
    action      TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_roles (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    business_unit_id UUID REFERENCES business_units(id) ON DELETE CASCADE,
    granted_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    UNIQUE (user_id, role_id, business_unit_id)
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_bu ON user_roles(business_unit_id);

CREATE TABLE IF NOT EXISTS teams (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    business_unit_id UUID NOT NULL REFERENCES business_units(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id    UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_in_team TEXT,
    joined_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (team_id, user_id)
);

CREATE TRIGGER trg_business_units_updated_at BEFORE UPDATE ON business_units
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO PUBLIC;

-- =============================================================================
-- PHASE 4: Commercial Hierarchy (migration 0004 adapted)
-- =============================================================================

CREATE TABLE IF NOT EXISTS clients (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    legal_name      TEXT,
    tax_id          TEXT,
    industry        TEXT,
    website         TEXT,
    logo_url        TEXT,
    notes           TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_clients_active ON clients(is_active) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS brands (
    id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    client_id   UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    code        TEXT NOT NULL,
    name        TEXT NOT NULL,
    category    TEXT,
    logo_url    TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ,
    UNIQUE (client_id, code)
);
CREATE INDEX IF NOT EXISTS idx_brands_client ON brands(client_id);

CREATE TABLE IF NOT EXISTS brand_contacts (
    id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    brand_id    UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    full_name   TEXT NOT NULL,
    email       TEXT,
    phone       TEXT,
    job_title   TEXT,
    is_primary  BOOLEAN NOT NULL DEFAULT FALSE,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS client_contracts (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    contract_type   TEXT NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE,
    total_value     NUMERIC(15, 2),
    currency        TEXT NOT NULL DEFAULT 'USD',
    status          TEXT NOT NULL DEFAULT 'active',
    document_url    TEXT,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_brands_updated_at BEFORE UPDATE ON brands
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_brand_contacts_updated_at BEFORE UPDATE ON brand_contacts
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_client_contracts_updated_at BEFORE UPDATE ON client_contracts
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- PHASE 5: Influencers (migration 0005 adapted)
-- =============================================================================

CREATE TABLE IF NOT EXISTS influencers (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    full_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    country         TEXT NOT NULL DEFAULT 'VE',
    city            TEXT,
    primary_tier    influencer_tier NOT NULL DEFAULT 'NANO',
    primary_handle  TEXT,
    avatar_url      TEXT,
    bio             TEXT,
    content_niches  TEXT[] NOT NULL DEFAULT '{}',
    languages       TEXT[] NOT NULL DEFAULT ARRAY['es'],
    status          TEXT NOT NULL DEFAULT 'active',
    tags            TEXT[] NOT NULL DEFAULT '{}',
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    source          TEXT,
    source_id       TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_influencers_primary_tier ON influencers(primary_tier);
CREATE INDEX IF NOT EXISTS idx_influencers_status ON influencers(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_influencers_niches ON influencers USING GIN(content_niches);
CREATE INDEX IF NOT EXISTS idx_influencers_tags ON influencers USING GIN(tags);

CREATE TABLE IF NOT EXISTS influencer_social_accounts (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    influencer_id   UUID NOT NULL REFERENCES influencers(id) ON DELETE CASCADE,
    platform        TEXT NOT NULL,
    handle          TEXT NOT NULL,
    url             TEXT,
    platform_user_id TEXT,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (platform, handle)
);
CREATE INDEX IF NOT EXISTS idx_social_accounts_influencer ON influencer_social_accounts(influencer_id);

CREATE TABLE IF NOT EXISTS influencer_metrics_snapshot (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    influencer_id           UUID NOT NULL REFERENCES influencers(id) ON DELETE CASCADE,
    social_account_id       UUID REFERENCES influencer_social_accounts(id) ON DELETE CASCADE,
    snapshot_date           DATE NOT NULL,
    followers               BIGINT,
    following               BIGINT,
    posts_count             INTEGER,
    avg_likes               NUMERIC(12, 2),
    avg_comments            NUMERIC(12, 2),
    avg_views               BIGINT,
    engagement_rate         NUMERIC(6, 4),
    reach_30d               BIGINT,
    impressions_30d         BIGINT,
    audience_credibility    NUMERIC(5, 2),
    audience_quality        NUMERIC(5, 2),
    source                  kpi_source NOT NULL DEFAULT 'MANUAL',
    raw_payload             JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (influencer_id, social_account_id, snapshot_date, source)
);
CREATE INDEX IF NOT EXISTS idx_metrics_snapshot_influencer ON influencer_metrics_snapshot(influencer_id);
CREATE INDEX IF NOT EXISTS idx_metrics_snapshot_date ON influencer_metrics_snapshot(snapshot_date DESC);

CREATE TRIGGER trg_influencers_updated_at BEFORE UPDATE ON influencers
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_social_accounts_updated_at BEFORE UPDATE ON influencer_social_accounts
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- PHASE 6: Campaigns (migration 0006 adapted)
-- =============================================================================

CREATE TABLE IF NOT EXISTS campaigns (
    id                  UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code                TEXT NOT NULL UNIQUE,
    client_id           UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    brand_id            UUID NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
    name                TEXT NOT NULL,
    campaign_type       TEXT,
    objective           campaign_objective NOT NULL,
    secondary_objectives campaign_objective[] NOT NULL DEFAULT '{}',
    influencer_tiers     influencer_tier[] NOT NULL DEFAULT '{}',
    target_audience     TEXT,
    start_date          DATE,
    end_date            DATE,
    budget_total        NUMERIC(15, 2),
    budget_currency     TEXT NOT NULL DEFAULT 'USD',
    num_influencers     INTEGER NOT NULL DEFAULT 0,
    status              campaign_status NOT NULL DEFAULT 'BRIEF',
    owner_user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    business_unit_id    UUID REFERENCES business_units(id) ON DELETE SET NULL,
    team_id             UUID REFERENCES teams(id) ON DELETE SET NULL,
    tags                TEXT[] NOT NULL DEFAULT '{}',
    notes               TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    CONSTRAINT chk_campaign_dates CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);
CREATE INDEX IF NOT EXISTS idx_campaigns_client ON campaigns(client_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_brand ON campaigns(brand_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_objective ON campaigns(objective);
CREATE INDEX IF NOT EXISTS idx_campaigns_dates ON campaigns(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_campaigns_owner ON campaigns(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_bu ON campaigns(business_unit_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_tags ON campaigns USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_campaigns_active ON campaigns(deleted_at) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS campaign_status_history (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    from_status     campaign_status,
    to_status       campaign_status NOT NULL,
    changed_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    reason          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_status_history_campaign ON campaign_status_history(campaign_id, created_at DESC);

CREATE TABLE IF NOT EXISTS campaign_influencers (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    influencer_id   UUID NOT NULL REFERENCES influencers(id) ON DELETE RESTRICT,
    role            TEXT,
    tier            influencer_tier NOT NULL,
    agreed_fee      NUMERIC(12, 2),
    currency        TEXT NOT NULL DEFAULT 'USD',
    deliverables    JSONB NOT NULL DEFAULT '[]'::jsonb,
    status          campaign_influencer_status NOT NULL DEFAULT 'PROPUESTO',
    contracted_at   TIMESTAMPTZ,
    delivered_at    TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (campaign_id, influencer_id)
);
CREATE INDEX IF NOT EXISTS idx_campaign_influencers_campaign ON campaign_influencers(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_influencers_influencer ON campaign_influencers(influencer_id);
CREATE INDEX IF NOT EXISTS idx_campaign_influencers_status ON campaign_influencers(status);

CREATE TABLE IF NOT EXISTS campaign_links (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    link_type       campaign_link_type NOT NULL,
    title           TEXT NOT NULL,
    url             TEXT NOT NULL,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_campaign_links_campaign ON campaign_links(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_links_type ON campaign_links(link_type);

CREATE TABLE IF NOT EXISTS campaign_documents (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    doc_type        campaign_link_type NOT NULL,
    title           TEXT NOT NULL,
    storage_path    TEXT,
    external_url    TEXT,
    file_name       TEXT,
    file_size_bytes BIGINT,
    mime_type       TEXT,
    uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    is_current      BOOLEAN NOT NULL DEFAULT TRUE,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_campaign_documents_campaign ON campaign_documents(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_documents_type ON campaign_documents(doc_type);

-- Trigger: log status changes
-- auth.uid() stub returns NULL in Railway; COALESCE prevents crashes
CREATE OR REPLACE FUNCTION public.log_campaign_status_change()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO campaign_status_history (campaign_id, from_status, to_status, changed_by)
        VALUES (NEW.id, NULL, NEW.status, NEW.created_by);
    ELSIF (TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status) THEN
        INSERT INTO campaign_status_history (campaign_id, from_status, to_status, changed_by)
        VALUES (NEW.id, OLD.status, NEW.status,
                COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000'::UUID));
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_campaign_status_change
    AFTER INSERT OR UPDATE OF status ON campaigns
    FOR EACH ROW EXECUTE FUNCTION public.log_campaign_status_change();

CREATE TRIGGER trg_campaigns_updated_at BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_campaign_influencers_updated_at BEFORE UPDATE ON campaign_influencers
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_campaign_links_updated_at BEFORE UPDATE ON campaign_links
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- PHASE 7: KPIs (migration 0007 adapted)
-- =============================================================================

CREATE TABLE IF NOT EXISTS kpi_definitions (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    description     TEXT,
    category        kpi_category NOT NULL,
    unit            TEXT NOT NULL,
    format_hint     TEXT,
    higher_is_better BOOLEAN NOT NULL DEFAULT TRUE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS campaign_kpi_values (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    kpi_definition_id UUID NOT NULL REFERENCES kpi_definitions(id) ON DELETE RESTRICT,
    value           NUMERIC(18, 6) NOT NULL,
    period_start    DATE,
    period_end      DATE,
    source          kpi_source NOT NULL DEFAULT 'MANUAL',
    notes           TEXT,
    recorded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (campaign_id, kpi_definition_id, period_start, period_end, source)
);
CREATE INDEX IF NOT EXISTS idx_campaign_kpi_campaign ON campaign_kpi_values(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_kpi_definition ON campaign_kpi_values(kpi_definition_id);
CREATE INDEX IF NOT EXISTS idx_campaign_kpi_period ON campaign_kpi_values(period_start, period_end);

CREATE TABLE IF NOT EXISTS benchmarks (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    kpi_definition_id UUID NOT NULL REFERENCES kpi_definitions(id) ON DELETE CASCADE,
    scope_type      TEXT NOT NULL,
    scope_id        UUID,
    p25_value       NUMERIC(18, 6),
    p50_value       NUMERIC(18, 6),
    p75_value       NUMERIC(18, 6),
    min_value       NUMERIC(18, 6),
    max_value       NUMERIC(18, 6),
    sample_size     INTEGER,
    period_start    DATE,
    period_end      DATE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_benchmarks_kpi ON benchmarks(kpi_definition_id);
CREATE INDEX IF NOT EXISTS idx_benchmarks_scope ON benchmarks(scope_type, scope_id);

CREATE TABLE IF NOT EXISTS insights (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    insight_type    TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    supporting_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_winning_format BOOLEAN NOT NULL DEFAULT FALSE,
    generated_by_ai BOOLEAN NOT NULL DEFAULT FALSE,
    ai_job_id       UUID,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_insights_campaign ON insights(campaign_id);

CREATE TABLE IF NOT EXISTS winning_formats (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    format_name     TEXT NOT NULL,
    description     TEXT,
    performance_score NUMERIC(6, 2),
    sample_data     JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_kpi_definitions_updated_at BEFORE UPDATE ON kpi_definitions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_benchmarks_updated_at BEFORE UPDATE ON benchmarks
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- PHASE 8: Operations (migration 0008 adapted)
-- =============================================================================

CREATE TABLE IF NOT EXISTS budgets (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE UNIQUE,
    total_planned   NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_committed NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_spent     NUMERIC(15, 2) NOT NULL DEFAULT 0,
    currency        TEXT NOT NULL DEFAULT 'USD',
    notes           TEXT,
    approved_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS budget_items (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    budget_id       UUID NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
    category        TEXT NOT NULL,
    description     TEXT NOT NULL,
    planned_amount  NUMERIC(15, 2) NOT NULL DEFAULT 0,
    committed_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
    spent_amount    NUMERIC(15, 2) NOT NULL DEFAULT 0,
    vendor          TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_budget_items_budget ON budget_items(budget_id);

CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id     UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    business_unit_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    status          task_status NOT NULL DEFAULT 'PENDIENTE',
    priority        task_priority NOT NULL DEFAULT 'MEDIA',
    assignee_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date        TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    trello_card_id  TEXT,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tasks_campaign ON tasks(campaign_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);

CREATE TABLE IF NOT EXISTS forms (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code            TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    description     TEXT,
    schema          JSONB NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    target_tier     influencer_tier,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS form_submissions (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    form_id         UUID NOT NULL REFERENCES forms(id) ON DELETE CASCADE,
    campaign_id     UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    influencer_id   UUID REFERENCES influencers(id) ON DELETE SET NULL,
    submitter_email TEXT,
    submitter_name  TEXT,
    payload         JSONB NOT NULL,
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed       BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at    TIMESTAMPTZ,
    processed_by    UUID REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_form_submissions_form ON form_submissions(form_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_campaign ON form_submissions(campaign_id);

CREATE TABLE IF NOT EXISTS automations (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    description     TEXT,
    trigger_type    TEXT NOT NULL,
    trigger_config  JSONB NOT NULL DEFAULT '{}'::jsonb,
    conditions      JSONB NOT NULL DEFAULT '[]'::jsonb,
    actions         JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at     TIMESTAMPTZ,
    run_count       INTEGER NOT NULL DEFAULT 0,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS automation_logs (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    automation_id   UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
    campaign_id     UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    trigger_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    actions_executed JSONB NOT NULL DEFAULT '[]'::jsonb,
    status          TEXT NOT NULL,
    error           TEXT,
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_automation_logs_automation ON automation_logs(automation_id, executed_at DESC);

CREATE TRIGGER trg_budgets_updated_at BEFORE UPDATE ON budgets
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_budget_items_updated_at BEFORE UPDATE ON budget_items
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_forms_updated_at BEFORE UPDATE ON forms
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_automations_updated_at BEFORE UPDATE ON automations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- PHASE 9: AI / RAG (migration 0009 adapted)
-- CONDITIONAL: only if pgvector extension is available
-- =============================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN

        CREATE TABLE IF NOT EXISTS ai_prompts (
            id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            code            TEXT NOT NULL,
            version         INTEGER NOT NULL DEFAULT 1,
            name            TEXT NOT NULL,
            description     TEXT,
            system_prompt   TEXT NOT NULL,
            user_template   TEXT NOT NULL,
            model_provider  TEXT NOT NULL DEFAULT 'openai',
            model_name      TEXT NOT NULL DEFAULT 'gpt-4o-mini',
            temperature     NUMERIC(3, 2) NOT NULL DEFAULT 0.7,
            max_tokens      INTEGER NOT NULL DEFAULT 2000,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (code, version)
        );

        CREATE TABLE IF NOT EXISTS documents (
            id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            campaign_id     UUID REFERENCES campaigns(id) ON DELETE SET NULL,
            brand_id        UUID REFERENCES brands(id) ON DELETE SET NULL,
            client_id       UUID REFERENCES clients(id) ON DELETE SET NULL,
            title           TEXT NOT NULL,
            description     TEXT,
            doc_type        TEXT NOT NULL,
            source          TEXT NOT NULL,
            source_url      TEXT,
            storage_path    TEXT,
            file_name       TEXT,
            mime_type       TEXT,
            file_size_bytes BIGINT,
            status          TEXT NOT NULL DEFAULT 'pending',
            chunk_count     INTEGER NOT NULL DEFAULT 0,
            metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
            uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
            indexed_at      TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_documents_campaign ON documents(campaign_id);
        CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
        CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type);

        CREATE TABLE IF NOT EXISTS document_chunks (
            id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index     INTEGER NOT NULL,
            content         TEXT NOT NULL,
            content_tokens  INTEGER,
            embedding       extensions.vector(1536),
            metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (document_id, chunk_index)
        );
        CREATE INDEX IF NOT EXISTS idx_document_chunks_doc ON document_chunks(document_id);

        CREATE TABLE IF NOT EXISTS ai_conversations (
            id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title           TEXT,
            context_type    TEXT,
            context_id      UUID,
            system_prompt_code TEXT,
            is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_ai_conversations_user ON ai_conversations(user_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS ai_messages (
            id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            model_provider  TEXT,
            model_name      TEXT,
            tokens_input    INTEGER,
            tokens_output   INTEGER,
            cost_usd        NUMERIC(10, 6),
            latency_ms      INTEGER,
            metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation ON ai_messages(conversation_id, created_at);

        CREATE TABLE IF NOT EXISTS ai_jobs (
            id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            job_type        ai_job_type NOT NULL,
            status          ai_job_status NOT NULL DEFAULT 'PENDING',
            payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
            result          JSONB,
            error           TEXT,
            attempts        INTEGER NOT NULL DEFAULT 0,
            max_attempts    INTEGER NOT NULL DEFAULT 3,
            scheduled_for   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at      TIMESTAMPTZ,
            completed_at    TIMESTAMPTZ,
            user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
            campaign_id     UUID REFERENCES campaigns(id) ON DELETE SET NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_ai_jobs_status ON ai_jobs(status, scheduled_for);
        CREATE INDEX IF NOT EXISTS idx_ai_jobs_campaign ON ai_jobs(campaign_id);

        CREATE TABLE IF NOT EXISTS notifications (
            id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title           TEXT NOT NULL,
            body            TEXT,
            category        TEXT,
            severity        TEXT NOT NULL DEFAULT 'info',
            link            TEXT,
            is_read         BOOLEAN NOT NULL DEFAULT FALSE,
            read_at         TIMESTAMPTZ,
            metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC);

        CREATE OR REPLACE FUNCTION public.match_document_chunks(
            query_embedding extensions.vector(1536),
            match_threshold FLOAT DEFAULT 0.7,
            match_count INT DEFAULT 10,
            filter_campaign_id UUID DEFAULT NULL
        )
        RETURNS TABLE (id UUID, document_id UUID, content TEXT, similarity FLOAT, metadata JSONB)
        LANGUAGE plpgsql AS $$
        BEGIN
            RETURN QUERY
            SELECT dc.id, dc.document_id, dc.content,
                   1 - (dc.embedding <=> query_embedding) AS similarity,
                   dc.metadata
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.embedding IS NOT NULL
              AND 1 - (dc.embedding <=> query_embedding) > match_threshold
              AND (filter_campaign_id IS NULL OR d.campaign_id = filter_campaign_id)
            ORDER BY dc.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;

        CREATE TRIGGER trg_documents_updated_at BEFORE UPDATE ON documents
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        CREATE TRIGGER trg_ai_conversations_updated_at BEFORE UPDATE ON ai_conversations
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        CREATE TRIGGER trg_ai_jobs_updated_at BEFORE UPDATE ON ai_jobs
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        CREATE TRIGGER trg_ai_prompts_updated_at BEFORE UPDATE ON ai_prompts
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

        RAISE NOTICE 'Migration 0009 (AI/RAG) applied successfully';
    ELSE
        RAISE NOTICE 'Migration 0009 (AI/RAG) SKIPPED — pgvector extension not available';
    END IF;
END $$;

-- =============================================================================
-- PHASE 10: Dashboards, Audit, Integrations (migration 0010 adapted)
-- =============================================================================

CREATE TABLE IF NOT EXISTS dashboards (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id         UUID REFERENCES teams(id) ON DELETE CASCADE,
    business_unit_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    layout          JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    is_shared       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS widgets (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    dashboard_id    UUID NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    widget_type     TEXT NOT NULL,
    title           TEXT NOT NULL,
    config          JSONB NOT NULL DEFAULT '{}'::jsonb,
    position_x      INTEGER NOT NULL DEFAULT 0,
    position_y      INTEGER NOT NULL DEFAULT 0,
    width           INTEGER NOT NULL DEFAULT 4,
    height          INTEGER NOT NULL DEFAULT 3,
    refresh_interval_seconds INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_widgets_dashboard ON widgets(dashboard_id);

CREATE TABLE IF NOT EXISTS scheduled_reports (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    description     TEXT,
    report_type     TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    query_config    JSONB NOT NULL DEFAULT '{}'::jsonb,
    template_code   TEXT,
    delivery_channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    recipients      JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at     TIMESTAMPTZ,
    next_run_at     TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    action          audit_action NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     UUID,
    bu_id           UUID REFERENCES business_units(id) ON DELETE SET NULL,
    old_values      JSONB,
    new_values      JSONB,
    ip_address      INET,
    user_agent      TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);

CREATE TABLE IF NOT EXISTS integrations (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    provider        integration_provider NOT NULL,
    business_unit_id UUID REFERENCES business_units(id) ON DELETE CASCADE,
    config          JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_sync_at    TIMESTAMPTZ,
    last_error      TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, business_unit_id)
);

CREATE TABLE IF NOT EXISTS webhooks (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    name            TEXT NOT NULL,
    url             TEXT NOT NULL,
    secret          TEXT,
    events          TEXT[] NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered_at TIMESTAMPTZ,
    failure_count   INTEGER NOT NULL DEFAULT 0,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exports (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    export_type     TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    query_config    JSONB NOT NULL DEFAULT '{}'::jsonb,
    file_path       TEXT,
    row_count       INTEGER,
    file_size_bytes BIGINT,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_exports_user ON exports(user_id, created_at DESC);

CREATE TRIGGER trg_dashboards_updated_at BEFORE UPDATE ON dashboards
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_widgets_updated_at BEFORE UPDATE ON widgets
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_scheduled_reports_updated_at BEFORE UPDATE ON scheduled_reports
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_integrations_updated_at BEFORE UPDATE ON integrations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_webhooks_updated_at BEFORE UPDATE ON webhooks
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- PHASE 11: RLS OMITTED (migration 0011 — asyncpg bypasses RLS)
-- =============================================================================
-- RATIONALE: The API connects as postgres superuser via asyncpg (direct TCP,
-- not through Supabase Auth). RLS policies are enforced only for queries run
-- through Supabase's Auth gateway. Since we bypass that entirely, all RLS
-- policies are a no-op. They are omitted here for clarity and to avoid
-- confusing errors if auth.uid() returns NULL.
--
-- The original helper functions (current_user_role_codes, current_user_bu_ids,
-- is_admin_general) are not created since they depend on auth.uid().
-- If Supabase Auth is re-introduced later, re-run migration 0011 from scratch.
--
-- =============================================================================

-- =============================================================================
-- PHASE 12: Data Quality (migration 0012 adapted)
-- =============================================================================

CREATE TABLE IF NOT EXISTS data_quality_issues (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    resource_type   TEXT NOT NULL,
    resource_id     UUID,
    issue_type      TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'warning',
    description     TEXT,
    raw_value       TEXT,
    source          TEXT NOT NULL DEFAULT 'excel_migration',
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_resolved     BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ,
    resolved_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_notes  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dqi_resource ON data_quality_issues(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_dqi_unresolved ON data_quality_issues(is_resolved) WHERE is_resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_dqi_issue_type ON data_quality_issues(issue_type);
CREATE INDEX IF NOT EXISTS idx_dqi_severity ON data_quality_issues(severity);

-- =============================================================================
-- PHASE 13: P.I.A.R. Foundation (migration 0015 adapted)
-- =============================================================================

CREATE TABLE IF NOT EXISTS publicaciones (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id             UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    influencer_id           UUID REFERENCES influencers(id) ON DELETE SET NULL,
    fecha_publicacion       TIMESTAMPTZ NOT NULL,
    vistas                  BIGINT,
    alcance                 BIGINT,
    likes                   INTEGER,
    comentarios             INTEGER,
    compartidos             INTEGER,
    guardados               INTEGER,
    er_alcance              NUMERIC(8, 6),
    er_vistas               NUMERIC(8, 6),
    retencion               NUMERIC(6, 4),
    sentimiento_positivo     INTEGER DEFAULT 0,
    sentimiento_neutro      INTEGER DEFAULT 0,
    sentimiento_negativo    INTEGER DEFAULT 0,
    url_publicacion         TEXT,
    plataforma             TEXT NOT NULL DEFAULT 'instagram',
    formato                TEXT,
    source                 TEXT NOT NULL DEFAULT 'SHEETS',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_publicaciones_campaign ON publicaciones(campaign_id);
CREATE INDEX IF NOT EXISTS idx_publicaciones_influencer ON publicaciones(influencer_id);
CREATE INDEX IF NOT EXISTS idx_publicaciones_fecha ON publicaciones(fecha_publicacion DESC);
CREATE INDEX IF NOT EXISTS idx_publicaciones_campaign_fecha ON publicaciones(campaign_id, fecha_publicacion DESC);
CREATE INDEX IF NOT EXISTS idx_publicaciones_source ON publicaciones(source);

CREATE TABLE IF NOT EXISTS comentarios (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    publicacion_id          UUID NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    autor_handle            TEXT,
    texto                   TEXT NOT NULL,
    sentimiento             TEXT,
    confianza              NUMERIC(3, 2),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_comentarios_publicacion ON comentarios(publicacion_id);
CREATE INDEX IF NOT EXISTS idx_comentarios_sentimiento ON comentarios(sentimiento) WHERE sentimiento IS NOT NULL;

-- set_updated_at helper for P.I.A.R.
CREATE OR REPLACE FUNCTION public.set_updated_at_piar()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

CREATE TRIGGER trg_publicaciones_updated_at
    BEFORE UPDATE ON publicaciones
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_piar();

-- =============================================================================
-- PHASE 14: Tier Benchmarks LWFA (migration 0016 adapted)
-- =============================================================================

CREATE TYPE influencer_subtier AS ENUM (
    'NANO_BAJO','NANO_ALTO',
    'MICRO_BAJO','MICRO_MEDIO','MICRO_ALTO',
    'MID_BAJO','MID_ALTO',
    'MACRO_BAJO','MACRO_ALTO'
);

CREATE TABLE IF NOT EXISTS tier_benchmarks (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    subtier         influencer_subtier NOT NULL UNIQUE,
    followers_min   BIGINT NOT NULL,
    followers_max   BIGINT NOT NULL,
    vf_min          NUMERIC(5, 3) NOT NULL,
    vf_max          NUMERIC(5, 3) NOT NULL,
    er_min          NUMERIC(5, 2) NOT NULL,
    er_max          NUMERIC(5, 2) NOT NULL,
    cpv_ideal       NUMERIC(8, 4) NOT NULL,
    role_description TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tier_benchmarks_subtier ON tier_benchmarks(subtier);

CREATE OR REPLACE FUNCTION public.set_updated_at_benchmarks()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

CREATE TRIGGER trg_tier_benchmarks_updated_at
    BEFORE UPDATE ON tier_benchmarks
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_benchmarks();

-- Seed tier_benchmarks data
INSERT INTO tier_benchmarks (subtier, followers_min, followers_max, vf_min, vf_max, er_min, er_max, cpv_ideal, role_description) VALUES
    ('NANO_BAJO',      500,      4999,   1.200, 2.500, 10.00, 15.00, 0.0050, 'Volumen + viralidad orgánica'),
    ('NANO_ALTO',      5000,     9999,   0.900, 1.500,  8.00, 12.00, 0.0080, 'Distribución orgánica'),
    ('MICRO_BAJO',     10000,    29999,  0.900, 1.800,  8.00, 13.00, 0.0100, 'Engagement + conversión'),
    ('MICRO_MEDIO',    30000,    59999,  0.800, 1.800,  6.00, 11.00, 0.0110, 'Balance performance'),
    ('MICRO_ALTO',     60000,    99999,  0.700, 1.500,  5.00, 10.00, 0.0120, 'Escala + validación'),
    ('MID_BAJO',       100000,   249999, 0.500, 1.000,  4.00,  8.00, 0.0150, 'Credibilidad'),
    ('MID_ALTO',       250000,   499999, 0.300, 0.800,  3.00,  7.00, 0.0170, 'Awareness + branding'),
    ('MACRO_BAJO',     500000,   749999, 0.400, 1.500,  3.00,  6.00, 0.0210, 'Amplificación masiva'),
    ('MACRO_ALTO',     750000,   1000000,0.200, 0.900,  2.00,  5.00, 0.0240, 'Top awareness')
ON CONFLICT (subtier) DO NOTHING;

-- Add columns to existing influencers table (these are idempotent — won't fail if columns exist)
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS sub_tier influencer_subtier;
CREATE INDEX IF NOT EXISTS idx_influencers_sub_tier ON influencers(sub_tier) WHERE sub_tier IS NOT NULL;

-- Add scoring columns to publicaciones
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_retention NUMERIC(3, 2);
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_engagement NUMERIC(3, 2);
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_viralidad NUMERIC(3, 2);
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_final NUMERIC(3, 2);
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_decision TEXT;
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_decision_mode TEXT;
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_publicaciones_score ON publicaciones(score_final) WHERE score_final IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_publicaciones_decision ON publicaciones(score_decision) WHERE score_decision IS NOT NULL;

-- Helper functions for subtier resolution
CREATE OR REPLACE FUNCTION public.resolve_subtier(p_followers BIGINT)
RETURNS influencer_subtier LANGUAGE plpgsql AS $$
DECLARE result influencer_subtier;
BEGIN
    SELECT subtier INTO result FROM tier_benchmarks
    WHERE p_followers >= followers_min AND p_followers <= followers_max
    LIMIT 1;
    RETURN result;
END;
$$;

CREATE OR REPLACE FUNCTION public.set_influencer_subtier()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.sub_tier IS NULL THEN
        NEW.sub_tier := public.resolve_subtier(
            (NEW.metadata_ ->> 'last_known_followers')::BIGINT
        );
    END IF;
    RETURN NEW;
END;
$$;

-- =============================================================================
-- PHASE 15: Sentiment Analysis (migration 0017 adapted)
-- =============================================================================
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS comentarios_analizados JSONB;
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS sentimiento_analizado_at TIMESTAMPTZ;
ALTER TABLE comentarios ADD COLUMN IF NOT EXISTS analyzed_sentiment TEXT;
ALTER TABLE comentarios ADD COLUMN IF NOT EXISTS analyzed_confidence NUMERIC(3, 2);
ALTER TABLE comentarios ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ;

-- =============================================================================
-- PHASE 16: Migration Tracking (migration 0018 adapted)
-- =============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum    TEXT
);

-- =============================================================================
-- PHASE 17: Discovery Foundation (migrations 0019-0028)
-- These tables ALREADY EXIST on production (confirmed via Railway logs).
-- IF NOT EXISTS makes this idempotent — safe to re-run.
-- =============================================================================

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
                            CHECK (status IN ('pending','running','completed','failed','cancelled')),
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
CREATE INDEX IF NOT EXISTS idx_discovery_runs_status ON discovery_runs(status);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_created_by ON discovery_runs(created_by);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_brand ON discovery_runs(brand_id);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_created_at ON discovery_runs(created_at DESC);

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
                            CHECK (status IN ('new','saved','dismissed','contacted','replied','won','lost')),
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
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_run ON discovery_candidates(run_id);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_status ON discovery_candidates(status);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_platform ON discovery_candidates(platform);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_match_score ON discovery_candidates(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_country ON discovery_candidates(country);

CREATE TABLE IF NOT EXISTS discovery_conversations (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id                 UUID REFERENCES users(id) ON DELETE CASCADE,
    bu_id                   UUID REFERENCES business_units(id) ON DELETE SET NULL,
    state                   JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_step            TEXT CHECK (current_step IN ('start','brief','refining','searching','ranking','candidates_review','done')),
    discovery_run_id        UUID REFERENCES discovery_runs(id) ON DELETE SET NULL,
    accumulated_brief       TEXT,
    message_count           INTEGER DEFAULT 0,
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status                  TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active','completed','abandoned'))
);
CREATE INDEX IF NOT EXISTS idx_discovery_conversations_user ON discovery_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_discovery_conversations_status ON discovery_conversations(status);
CREATE INDEX IF NOT EXISTS idx_discovery_conversations_last_message ON discovery_conversations(last_message_at DESC);

CREATE TABLE IF NOT EXISTS discovery_messages (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    conversation_id         UUID NOT NULL REFERENCES discovery_conversations(id) ON DELETE CASCADE,
    role                    TEXT NOT NULL CHECK (role IN ('user','assistant','tool')),
    content                 TEXT NOT NULL,
    tool_calls              JSONB,
    tool_results            JSONB,
    reasoning               TEXT,
    cost_usd                NUMERIC(10,6),
    latency_ms              INTEGER,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_discovery_messages_conversation ON discovery_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_discovery_messages_created_at ON discovery_messages(created_at);

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
CREATE INDEX IF NOT EXISTS idx_api_costs_provider ON api_costs(provider, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_costs_entity ON api_costs(entity_id) WHERE entity_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS integration_credentials (
    id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    provider                TEXT NOT NULL,
    business_unit_id        UUID REFERENCES business_units(id) ON DELETE CASCADE,
    encrypted_credentials   JSONB NOT NULL,
    scopes                  TEXT[],
    status                  TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active','expired','revoked','error')),
    expires_at              TIMESTAMPTZ,
    last_used_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, business_unit_id)
);
CREATE INDEX IF NOT EXISTS idx_integration_credentials_provider ON integration_credentials(provider);
CREATE INDEX IF NOT EXISTS idx_integration_credentials_status ON integration_credentials(status);

-- Add extensions columns to influencers (migration 0019)
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS gender TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS age_range TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS latitude NUMERIC(9,6);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS longitude NUMERIC(9,6);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS audience_demographics JSONB DEFAULT '{}'::jsonb;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS is_discoverable BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovery_query TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS discovery_confidence NUMERIC(5,2);

-- Additional discovery_candidates additions (migrations 0022, 0024)
ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS tier TEXT CHECK (tier IN ('NANO','MICRO','MID','MACRO'));
ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS is_tienda BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_tier ON discovery_candidates(tier);
CREATE INDEX IF NOT EXISTS idx_discovery_candidates_is_tienda ON discovery_candidates(is_tienda);

ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS audience_top_countries JSONB;
ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS audience_top_cities JSONB;
ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS audience_interests TEXT[];
ALTER TABLE discovery_candidates ADD COLUMN IF NOT EXISTS language_primary TEXT;

-- Enums for discovery
DO $$
BEGIN
    CREATE TYPE candidate_status AS ENUM ('new','saved','dismissed','contacted','replied','won','lost');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;
DO $$
BEGIN
    CREATE TYPE discovery_run_status AS ENUM ('pending','running','completed','failed','cancelled');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;
DO $$
BEGIN
    CREATE TYPE conversation_step AS ENUM ('start','brief','refining','searching','ranking','candidates_review','done');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- Triggers for discovery tables
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

CREATE TRIGGER trg_discovery_runs_updated_at BEFORE UPDATE ON discovery_runs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_discovery_candidates_updated_at BEFORE UPDATE ON discovery_candidates
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_discovery_conversations_updated_at BEFORE UPDATE ON discovery_conversations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_integration_credentials_updated_at BEFORE UPDATE ON integration_credentials
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RPC function for discovery_runs metadata merge (migration 0026)
CREATE OR REPLACE FUNCTION discovery_runs_merge_metadata(p_run_id UUID, p_metadata JSONB)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    UPDATE discovery_runs
    SET metadata = metadata || p_metadata,
        updated_at = NOW()
    WHERE id = p_run_id;
END;
$$;

-- =============================================================================
-- PHASE 18: Mark all migrations as applied in schema_migrations
-- This prevents apply_migrations.py from attempting to re-run them.
-- =============================================================================
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
    ('28', '00000000000028_discovery_tier_persistence.sql')
ON CONFLICT (version) DO NOTHING;

-- =============================================================================
-- PHASE 19: Smoke tests
-- =============================================================================
DO $$
DECLARE
    table_count INTEGER;
    ext_count INTEGER;
    migration_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public';

    SELECT COUNT(*) INTO ext_count
    FROM pg_extension;

    SELECT COUNT(*) INTO migration_count
    FROM schema_migrations;

    RAISE NOTICE '=== LA WEB CORE RAILWAY BOOTSTRAP COMPLETE ===';
    RAISE NOTICE 'Tables created: %', table_count;
    RAISE NOTICE 'Extensions installed: %', ext_count;
    RAISE NOTICE 'Migrations tracked: %', migration_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Smoke test queries to run manually:';
    RAISE NOTICE '  SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ''public'';';
    RAISE NOTICE '  SELECT extname FROM pg_extension ORDER BY extname;';
    RAISE NOTICE '  SELECT COUNT(*) FROM schema_migrations;';
    RAISE NOTICE '  SELECT COUNT(*) FROM discovery_candidates;';
    RAISE NOTICE '  SELECT table_name FROM information_schema.tables WHERE table_schema = ''public'' AND table_name LIKE ''discovery_%%'';';
END $$;
