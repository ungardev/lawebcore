-- =================================================================
-- LA WEB CORE — Railway Bootstrap Part 3 of 5
-- Influencers + Campaigns + KPIs + Operations
-- Run in Railway Query Editor THIRD
-- =================================================================

-- Influencers
CREATE TABLE IF NOT EXISTS influencers (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    full_name TEXT NOT NULL, email TEXT, phone TEXT,
    country TEXT NOT NULL DEFAULT 'VE', city TEXT,
    primary_tier influencer_tier NOT NULL DEFAULT 'NANO', primary_handle TEXT, avatar_url TEXT, bio TEXT,
    content_niches TEXT[] NOT NULL DEFAULT '{}', languages TEXT[] NOT NULL DEFAULT ARRAY['es'],
    status TEXT NOT NULL DEFAULT 'active', tags TEXT[] NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb, source TEXT, source_id TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_influencers_primary_tier ON influencers(primary_tier);
CREATE INDEX IF NOT EXISTS idx_influencers_status ON influencers(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_influencers_niches ON influencers USING GIN(content_niches);
CREATE INDEX IF NOT EXISTS idx_influencers_tags ON influencers USING GIN(tags);

CREATE TABLE IF NOT EXISTS influencer_social_accounts (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    influencer_id UUID NOT NULL REFERENCES influencers(id) ON DELETE CASCADE,
    platform TEXT NOT NULL, handle TEXT NOT NULL, url TEXT, platform_user_id TEXT,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE, is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (platform, handle)
);
CREATE INDEX IF NOT EXISTS idx_social_accounts_influencer ON influencer_social_accounts(influencer_id);

CREATE TABLE IF NOT EXISTS influencer_metrics_snapshot (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    influencer_id UUID NOT NULL REFERENCES influencers(id) ON DELETE CASCADE,
    social_account_id UUID REFERENCES influencer_social_accounts(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL, followers BIGINT, following BIGINT, posts_count INTEGER,
    avg_likes NUMERIC(12,2), avg_comments NUMERIC(12,2), avg_views BIGINT,
    engagement_rate NUMERIC(6,4), reach_30d BIGINT, impressions_30d BIGINT,
    audience_credibility NUMERIC(5,2), audience_quality NUMERIC(5,2),
    source kpi_source NOT NULL DEFAULT 'MANUAL', raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (influencer_id, social_account_id, snapshot_date, source)
);
CREATE INDEX IF NOT EXISTS idx_metrics_snapshot_influencer ON influencer_metrics_snapshot(influencer_id);
CREATE INDEX IF NOT EXISTS idx_metrics_snapshot_date ON influencer_metrics_snapshot(snapshot_date DESC);

CREATE TRIGGER trg_influencers_updated_at BEFORE UPDATE ON influencers FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_social_accounts_updated_at BEFORE UPDATE ON influencer_social_accounts FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE, client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE RESTRICT, name TEXT NOT NULL,
    campaign_type TEXT, objective campaign_objective NOT NULL,
    secondary_objectives campaign_objective[] NOT NULL DEFAULT '{}',
    influencer_tiers influencer_tier[] NOT NULL DEFAULT '{}',
    target_audience TEXT, start_date DATE, end_date DATE,
    budget_total NUMERIC(15,2), budget_currency TEXT NOT NULL DEFAULT 'USD', num_influencers INTEGER NOT NULL DEFAULT 0,
    status campaign_status NOT NULL DEFAULT 'BRIEF',
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    business_unit_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    tags TEXT[] NOT NULL DEFAULT '{}', notes TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ,
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
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    from_status campaign_status, to_status campaign_status NOT NULL,
    changed_by UUID REFERENCES users(id) ON DELETE SET NULL, reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_status_history_campaign ON campaign_status_history(campaign_id, created_at DESC);

CREATE TABLE IF NOT EXISTS campaign_influencers (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    influencer_id UUID NOT NULL REFERENCES influencers(id) ON DELETE RESTRICT,
    role TEXT, tier influencer_tier NOT NULL, agreed_fee NUMERIC(12,2),
    currency TEXT NOT NULL DEFAULT 'USD', deliverables JSONB NOT NULL DEFAULT '[]'::jsonb,
    status campaign_influencer_status NOT NULL DEFAULT 'PROPUESTO',
    contracted_at TIMESTAMPTZ, delivered_at TIMESTAMPTZ, notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (campaign_id, influencer_id)
);
CREATE INDEX IF NOT EXISTS idx_campaign_influencers_campaign ON campaign_influencers(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_influencers_influencer ON campaign_influencers(influencer_id);
CREATE INDEX IF NOT EXISTS idx_campaign_influencers_status ON campaign_influencers(status);

CREATE TABLE IF NOT EXISTS campaign_links (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    link_type campaign_link_type NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL,
    description TEXT, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_campaign_links_campaign ON campaign_links(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_links_type ON campaign_links(link_type);

CREATE TABLE IF NOT EXISTS campaign_documents (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    doc_type campaign_link_type NOT NULL, title TEXT NOT NULL, storage_path TEXT, external_url TEXT,
    file_name TEXT, file_size_bytes BIGINT, mime_type TEXT,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    version INTEGER NOT NULL DEFAULT 1, is_current BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_campaign_documents_campaign ON campaign_documents(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_documents_type ON campaign_documents(doc_type);

-- Campaign status change trigger
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
END; $$;

CREATE TRIGGER trg_campaign_status_change AFTER INSERT OR UPDATE OF status ON campaigns
    FOR EACH ROW EXECUTE FUNCTION public.log_campaign_status_change();

CREATE TRIGGER trg_campaigns_updated_at BEFORE UPDATE ON campaigns FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_campaign_influencers_updated_at BEFORE UPDATE ON campaign_influencers FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_campaign_links_updated_at BEFORE UPDATE ON campaign_links FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- KPIs
CREATE TABLE IF NOT EXISTS kpi_definitions (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, description TEXT,
    category kpi_category NOT NULL, unit TEXT NOT NULL, format_hint TEXT,
    higher_is_better BOOLEAN NOT NULL DEFAULT TRUE, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS campaign_kpi_values (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    kpi_definition_id UUID NOT NULL REFERENCES kpi_definitions(id) ON DELETE RESTRICT,
    value NUMERIC(18,6) NOT NULL, period_start DATE, period_end DATE,
    source kpi_source NOT NULL DEFAULT 'MANUAL', notes TEXT,
    recorded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (campaign_id, kpi_definition_id, period_start, period_end, source)
);
CREATE INDEX IF NOT EXISTS idx_campaign_kpi_campaign ON campaign_kpi_values(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_kpi_definition ON campaign_kpi_values(kpi_definition_id);
CREATE INDEX IF NOT EXISTS idx_campaign_kpi_period ON campaign_kpi_values(period_start, period_end);

CREATE TABLE IF NOT EXISTS benchmarks (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    kpi_definition_id UUID NOT NULL REFERENCES kpi_definitions(id) ON DELETE CASCADE,
    scope_type TEXT NOT NULL, scope_id UUID,
    p25_value NUMERIC(18,6), p50_value NUMERIC(18,6), p75_value NUMERIC(18,6),
    min_value NUMERIC(18,6), max_value NUMERIC(18,6), sample_size INTEGER,
    period_start DATE, period_end DATE, is_active BOOLEAN NOT NULL DEFAULT TRUE, notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_benchmarks_kpi ON benchmarks(kpi_definition_id);
CREATE INDEX IF NOT EXISTS idx_benchmarks_scope ON benchmarks(scope_type, scope_id);

CREATE TABLE IF NOT EXISTS insights (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    insight_type TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
    supporting_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_winning_format BOOLEAN NOT NULL DEFAULT FALSE, generated_by_ai BOOLEAN NOT NULL DEFAULT FALSE,
    ai_job_id UUID, created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_insights_campaign ON insights(campaign_id);

CREATE TABLE IF NOT EXISTS winning_formats (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    format_name TEXT NOT NULL, description TEXT, performance_score NUMERIC(6,2),
    sample_data JSONB NOT NULL DEFAULT '{}'::jsonb, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_kpi_definitions_updated_at BEFORE UPDATE ON kpi_definitions FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_benchmarks_updated_at BEFORE UPDATE ON benchmarks FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Operations
CREATE TABLE IF NOT EXISTS budgets (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE UNIQUE,
    total_planned NUMERIC(15,2) NOT NULL DEFAULT 0, total_committed NUMERIC(15,2) NOT NULL DEFAULT 0,
    total_spent NUMERIC(15,2) NOT NULL DEFAULT 0, currency TEXT NOT NULL DEFAULT 'USD', notes TEXT,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL, approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS budget_items (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    budget_id UUID NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
    category TEXT NOT NULL, description TEXT NOT NULL,
    planned_amount NUMERIC(15,2) NOT NULL DEFAULT 0, committed_amount NUMERIC(15,2) NOT NULL DEFAULT 0,
    spent_amount NUMERIC(15,2) NOT NULL DEFAULT 0, vendor TEXT, notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_budget_items_budget ON budget_items(budget_id);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    business_unit_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
    title TEXT NOT NULL, description TEXT,
    status task_status NOT NULL DEFAULT 'PENDIENTE', priority task_priority NOT NULL DEFAULT 'MEDIA',
    assignee_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date TIMESTAMPTZ, completed_at TIMESTAMPTZ, trello_card_id TEXT,
    tags TEXT[] NOT NULL DEFAULT '{}', metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tasks_campaign ON tasks(campaign_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);

CREATE TABLE IF NOT EXISTS forms (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE, title TEXT NOT NULL, description TEXT,
    schema JSONB NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    target_tier influencer_tier, created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS form_submissions (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    form_id UUID NOT NULL REFERENCES forms(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    influencer_id UUID REFERENCES influencers(id) ON DELETE SET NULL,
    submitter_email TEXT, submitter_name TEXT, payload JSONB NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed BOOLEAN NOT NULL DEFAULT FALSE, processed_at TIMESTAMPTZ,
    processed_by UUID REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_form_submissions_form ON form_submissions(form_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_campaign ON form_submissions(campaign_id);

CREATE TABLE IF NOT EXISTS automations (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, description TEXT,
    trigger_type TEXT NOT NULL, trigger_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    conditions JSONB NOT NULL DEFAULT '[]'::jsonb, actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE, last_run_at TIMESTAMPTZ,
    run_count INTEGER NOT NULL DEFAULT 0, created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS automation_logs (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    trigger_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    actions_executed JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL, error TEXT, executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_automation_logs_automation ON automation_logs(automation_id, executed_at DESC);

CREATE TRIGGER trg_budgets_updated_at BEFORE UPDATE ON budgets FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_budget_items_updated_at BEFORE UPDATE ON budget_items FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_forms_updated_at BEFORE UPDATE ON forms FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_automations_updated_at BEFORE UPDATE ON automations FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
