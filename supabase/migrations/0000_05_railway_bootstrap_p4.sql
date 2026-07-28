-- =================================================================
-- LA WEB CORE — Railway Bootstrap Part 4 of 5
-- AI/RAG + Dashboards/Audit + Data Quality + PIAR + Benchmarks + Sentiment
-- Run in Railway Query Editor FOURTH
-- =================================================================

-- AI/RAG (conditional on pgvector)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN

        CREATE TABLE IF NOT EXISTS ai_prompts (
            id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            code TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, name TEXT NOT NULL, description TEXT,
            system_prompt TEXT NOT NULL, user_template TEXT NOT NULL,
            model_provider TEXT NOT NULL DEFAULT 'openai', model_name TEXT NOT NULL DEFAULT 'gpt-4o-mini',
            temperature NUMERIC(3,2) NOT NULL DEFAULT 0.7, max_tokens INTEGER NOT NULL DEFAULT 2000,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (code, version)
        );

        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
            brand_id UUID REFERENCES brands(id) ON DELETE SET NULL, client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
            title TEXT NOT NULL, description TEXT, doc_type TEXT NOT NULL, source TEXT NOT NULL, source_url TEXT,
            storage_path TEXT, file_name TEXT, mime_type TEXT, file_size_bytes BIGINT,
            status TEXT NOT NULL DEFAULT 'pending', chunk_count INTEGER NOT NULL DEFAULT 0,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb, uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
            indexed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_documents_campaign ON documents(campaign_id);
        CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
        CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type);

        CREATE TABLE IF NOT EXISTS document_chunks (
            id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL, content TEXT NOT NULL, content_tokens INTEGER,
            embedding extensions.vector(1536), metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (document_id, chunk_index)
        );
        CREATE INDEX IF NOT EXISTS idx_document_chunks_doc ON document_chunks(document_id);

        CREATE TABLE IF NOT EXISTS ai_conversations (
            id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT, context_type TEXT, context_id UUID, system_prompt_code TEXT,
            is_archived BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_ai_conversations_user ON ai_conversations(user_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS ai_messages (
            id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL, content TEXT NOT NULL, model_provider TEXT, model_name TEXT,
            tokens_input INTEGER, tokens_output INTEGER, cost_usd NUMERIC(10,6),
            latency_ms INTEGER, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation ON ai_messages(conversation_id, created_at);

        CREATE TABLE IF NOT EXISTS ai_jobs (
            id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            job_type ai_job_type NOT NULL, status ai_job_status NOT NULL DEFAULT 'PENDING',
            payload JSONB NOT NULL DEFAULT '{}'::jsonb, result JSONB, error TEXT,
            attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
            scheduled_for TIMESTAMPTZ NOT NULL DEFAULT NOW(), started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_ai_jobs_status ON ai_jobs(status, scheduled_for);
        CREATE INDEX IF NOT EXISTS idx_ai_jobs_campaign ON ai_jobs(campaign_id);

        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL, body TEXT, category TEXT,
            severity TEXT NOT NULL DEFAULT 'info', link TEXT,
            is_read BOOLEAN NOT NULL DEFAULT FALSE, read_at TIMESTAMPTZ,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC);

        CREATE OR REPLACE FUNCTION public.match_document_chunks(
            query_embedding extensions.vector(1536), match_threshold FLOAT DEFAULT 0.7,
            match_count INT DEFAULT 10, filter_campaign_id UUID DEFAULT NULL
        )
        RETURNS TABLE (id UUID, document_id UUID, content TEXT, similarity FLOAT, metadata JSONB)
        LANGUAGE plpgsql AS $$
        BEGIN RETURN QUERY
            SELECT dc.id, dc.document_id, dc.content,
                   1 - (dc.embedding <=> query_embedding) AS similarity, dc.metadata
            FROM document_chunks dc JOIN documents d ON d.id = dc.document_id
            WHERE dc.embedding IS NOT NULL
              AND 1 - (dc.embedding <=> query_embedding) > match_threshold
              AND (filter_campaign_id IS NULL OR d.campaign_id = filter_campaign_id)
            ORDER BY dc.embedding <=> query_embedding LIMIT match_count;
        END; $$;

        CREATE TRIGGER trg_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        CREATE TRIGGER trg_ai_conversations_updated_at BEFORE UPDATE ON ai_conversations FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        CREATE TRIGGER trg_ai_jobs_updated_at BEFORE UPDATE ON ai_jobs FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        CREATE TRIGGER trg_ai_prompts_updated_at BEFORE UPDATE ON ai_prompts FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    END IF;
END $$;

-- Dashboards, Audit, Integrations
CREATE TABLE IF NOT EXISTS dashboards (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE, team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    business_unit_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
    title TEXT NOT NULL, description TEXT, layout JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_default BOOLEAN NOT NULL DEFAULT FALSE, is_shared BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS widgets (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    dashboard_id UUID NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    widget_type TEXT NOT NULL, title TEXT NOT NULL, config JSONB NOT NULL DEFAULT '{}'::jsonb,
    position_x INTEGER NOT NULL DEFAULT 0, position_y INTEGER NOT NULL DEFAULT 0,
    width INTEGER NOT NULL DEFAULT 4, height INTEGER NOT NULL DEFAULT 3,
    refresh_interval_seconds INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_widgets_dashboard ON widgets(dashboard_id);

CREATE TABLE IF NOT EXISTS scheduled_reports (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, description TEXT, report_type TEXT NOT NULL,
    cron_expression TEXT NOT NULL, query_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    template_code TEXT, delivery_channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    recipients JSONB NOT NULL DEFAULT '[]'::jsonb, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at TIMESTAMPTZ, next_run_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, action audit_action NOT NULL,
    resource_type TEXT NOT NULL, resource_id UUID,
    bu_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
    old_values JSONB, new_values JSONB, ip_address INET, user_agent TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);

CREATE TABLE IF NOT EXISTS integrations (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    provider integration_provider NOT NULL, business_unit_id UUID REFERENCES business_units(id) ON DELETE CASCADE,
    config JSONB NOT NULL DEFAULT '{}'::jsonb, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ, last_error TEXT, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, business_unit_id)
);

CREATE TABLE IF NOT EXISTS webhooks (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    name TEXT NOT NULL, url TEXT NOT NULL, secret TEXT,
    events TEXT[] NOT NULL DEFAULT '{}', is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered_at TIMESTAMPTZ, failure_count INTEGER NOT NULL DEFAULT 0,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exports (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, export_type TEXT NOT NULL,
    resource_type TEXT NOT NULL, query_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    file_path TEXT, row_count INTEGER, file_size_bytes BIGINT, expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_exports_user ON exports(user_id, created_at DESC);

CREATE TRIGGER trg_dashboards_updated_at BEFORE UPDATE ON dashboards FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_widgets_updated_at BEFORE UPDATE ON widgets FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_scheduled_reports_updated_at BEFORE UPDATE ON scheduled_reports FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_integrations_updated_at BEFORE UPDATE ON integrations FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_webhooks_updated_at BEFORE UPDATE ON webhooks FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Data Quality
CREATE TABLE IF NOT EXISTS data_quality_issues (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    resource_type TEXT NOT NULL, resource_id UUID, issue_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'warning', description TEXT, raw_value TEXT,
    source TEXT NOT NULL DEFAULT 'excel_migration', metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE, resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL, resolved_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dqi_resource ON data_quality_issues(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_dqi_unresolved ON data_quality_issues(is_resolved) WHERE is_resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_dqi_issue_type ON data_quality_issues(issue_type);
CREATE INDEX IF NOT EXISTS idx_dqi_severity ON data_quality_issues(severity);

-- PIAR: Publicaciones
CREATE TABLE IF NOT EXISTS publicaciones (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    influencer_id UUID REFERENCES influencers(id) ON DELETE SET NULL,
    fecha_publicacion TIMESTAMPTZ NOT NULL, vistas BIGINT, alcance BIGINT,
    likes INTEGER, comentarios INTEGER, compartidos INTEGER, guardados INTEGER,
    er_alcance NUMERIC(8,6), er_vistas NUMERIC(8,6), retencion NUMERIC(6,4),
    sentimiento_positivo INTEGER DEFAULT 0, sentimiento_neutro INTEGER DEFAULT 0, sentimiento_negativo INTEGER DEFAULT 0,
    url_publicacion TEXT, plataforma TEXT NOT NULL DEFAULT 'instagram', formato TEXT,
    source TEXT NOT NULL DEFAULT 'SHEETS',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_publicaciones_campaign ON publicaciones(campaign_id);
CREATE INDEX IF NOT EXISTS idx_publicaciones_influencer ON publicaciones(influencer_id);
CREATE INDEX IF NOT EXISTS idx_publicaciones_fecha ON publicaciones(fecha_publicacion DESC);
CREATE INDEX IF NOT EXISTS idx_publicaciones_campaign_fecha ON publicaciones(campaign_id, fecha_publicacion DESC);
CREATE INDEX IF NOT EXISTS idx_publicaciones_source ON publicaciones(source);

CREATE TABLE IF NOT EXISTS comentarios (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    publicacion_id UUID NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    autor_handle TEXT, texto TEXT NOT NULL, sentimiento TEXT, confianza NUMERIC(3,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_comentarios_publicacion ON comentarios(publicacion_id);
CREATE INDEX IF NOT EXISTS idx_comentarios_sentimiento ON comentarios(sentimiento) WHERE sentimiento IS NOT NULL;

CREATE OR REPLACE FUNCTION public.set_updated_at_piar()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

CREATE TRIGGER trg_publicaciones_updated_at BEFORE UPDATE ON publicaciones
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_piar();

-- Benchmarks
DO $$ BEGIN CREATE TYPE influencer_subtier AS ENUM ('NANO_BAJO','NANO_ALTO','MICRO_BAJO','MICRO_MEDIO','MICRO_ALTO','MID_BAJO','MID_ALTO','MACRO_BAJO','MACRO_ALTO'); EXCEPTION WHEN OTHERS THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS tier_benchmarks (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    subtier influencer_subtier NOT NULL UNIQUE,
    followers_min BIGINT NOT NULL, followers_max BIGINT NOT NULL,
    vf_min NUMERIC(5,3) NOT NULL, vf_max NUMERIC(5,3) NOT NULL,
    er_min NUMERIC(5,2) NOT NULL, er_max NUMERIC(5,2) NOT NULL,
    cpv_ideal NUMERIC(8,4) NOT NULL, role_description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tier_benchmarks_subtier ON tier_benchmarks(subtier);

CREATE OR REPLACE FUNCTION public.set_updated_at_benchmarks()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

CREATE TRIGGER trg_tier_benchmarks_updated_at BEFORE UPDATE ON tier_benchmarks
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_benchmarks();

INSERT INTO tier_benchmarks (subtier, followers_min, followers_max, vf_min, vf_max, er_min, er_max, cpv_ideal, role_description) VALUES
    ('NANO_BAJO',500,4999,1.200,2.500,10.00,15.00,0.0050,'Volumen + viralidad orgánica'),
    ('NANO_ALTO',5000,9999,0.900,1.500,8.00,12.00,0.0080,'Distribución orgánica'),
    ('MICRO_BAJO',10000,29999,0.900,1.800,8.00,13.00,0.0100,'Engagement + conversión'),
    ('MICRO_MEDIO',30000,59999,0.800,1.800,6.00,11.00,0.0110,'Balance performance'),
    ('MICRO_ALTO',60000,99999,0.700,1.500,5.00,10.00,0.0120,'Escala + validación'),
    ('MID_BAJO',100000,249999,0.500,1.000,4.00,8.00,0.0150,'Credibilidad'),
    ('MID_ALTO',250000,499999,0.300,0.800,3.00,7.00,0.0170,'Awareness + branding'),
    ('MACRO_BAJO',500000,749999,0.400,1.500,3.00,6.00,0.0210,'Amplificación masiva'),
    ('MACRO_ALTO',750000,1000000,0.200,0.900,2.00,5.00,0.0240,'Top awareness')
ON CONFLICT (subtier) DO NOTHING;

-- Score columns on publicaciones
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_retention NUMERIC(3,2);
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_engagement NUMERIC(3,2);
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_viralidad NUMERIC(3,2);
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_final NUMERIC(3,2);
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_decision TEXT;
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS score_decision_mode TEXT;
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_publicaciones_score ON publicaciones(score_final) WHERE score_final IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_publicaciones_decision ON publicaciones(score_decision) WHERE score_decision IS NOT NULL;

-- Sentiment columns on publicaciones/comentarios
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS comentarios_analizados JSONB;
ALTER TABLE publicaciones ADD COLUMN IF NOT EXISTS sentimiento_analizado_at TIMESTAMPTZ;
ALTER TABLE comentarios ADD COLUMN IF NOT EXISTS analyzed_sentiment TEXT;
ALTER TABLE comentarios ADD COLUMN IF NOT EXISTS analyzed_confidence NUMERIC(3,2);
ALTER TABLE comentarios ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ;

-- Helper functions
CREATE OR REPLACE FUNCTION public.resolve_subtier(p_followers BIGINT)
RETURNS influencer_subtier LANGUAGE plpgsql AS $$
DECLARE result influencer_subtier;
BEGIN
    SELECT subtier INTO result FROM tier_benchmarks
    WHERE p_followers >= followers_min AND p_followers <= followers_max LIMIT 1;
    RETURN result;
END; $$;

CREATE OR REPLACE FUNCTION public.set_influencer_subtier()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.sub_tier IS NULL THEN
        NEW.sub_tier := public.resolve_subtier((NEW.metadata_->>'last_known_followers')::BIGINT);
    END IF;
    RETURN NEW;
END; $$;
