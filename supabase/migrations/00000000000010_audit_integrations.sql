-- =================================================================
-- LA WEB CORE - Migration 0010: Analytics, Dashboards, Audit, Integrations
-- =================================================================

-- ---------- Dashboards (configurables por usuario) ----------
CREATE TABLE dashboards (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
  team_id         UUID REFERENCES teams(id) ON DELETE CASCADE,
  business_unit_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
  title           TEXT NOT NULL,
  description     TEXT,
  layout          JSONB NOT NULL DEFAULT '{}'::jsonb,  -- grid layout
  is_default      BOOLEAN NOT NULL DEFAULT FALSE,
  is_shared       BOOLEAN NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- Widgets (componentes de un dashboard) ----------
CREATE TABLE widgets (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  dashboard_id    UUID NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  widget_type     TEXT NOT NULL,               -- 'kpi_card', 'bar_chart', 'line_chart', 'table', 'kanban', 'pie'
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

CREATE INDEX idx_widgets_dashboard ON widgets(dashboard_id);

-- ---------- Scheduled Reports (cron automatico) ----------
CREATE TABLE scheduled_reports (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  code            TEXT NOT NULL UNIQUE,
  name            TEXT NOT NULL,
  description     TEXT,
  report_type     TEXT NOT NULL,               -- 'campaign_summary', 'kpi_digest', 'weekly_status'
  cron_expression TEXT NOT NULL,               -- '0 9 * * MON'
  query_config    JSONB NOT NULL DEFAULT '{}'::jsonb,
  template_code   TEXT,                        -- referencia a ai_prompts o template
  delivery_channels JSONB NOT NULL DEFAULT '[]'::jsonb,  -- ['email', 'slack']
  recipients      JSONB NOT NULL DEFAULT '[]'::jsonb,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  last_run_at     TIMESTAMPTZ,
  next_run_at     TIMESTAMPTZ,
  created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- Audit Log ----------
CREATE TABLE audit_logs (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
  action          audit_action NOT NULL,
  resource_type   TEXT NOT NULL,               -- 'campaign', 'user', etc.
  resource_id     UUID,
  bu_id           UUID REFERENCES business_units(id) ON DELETE SET NULL,
  old_values      JSONB,
  new_values      JSONB,
  ip_address      INET,
  user_agent      TEXT,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

COMMENT ON TABLE audit_logs IS 'Log inmutable de toda accion del sistema. Compliance y debugging.';

-- ---------- Integrations (configs por proveedor) ----------
CREATE TABLE integrations (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  provider        integration_provider NOT NULL,
  business_unit_id UUID REFERENCES business_units(id) ON DELETE CASCADE,
  config          JSONB NOT NULL DEFAULT '{}'::jsonb,  -- credenciales encriptadas
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  last_sync_at    TIMESTAMPTZ,
  last_error      TEXT,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (provider, business_unit_id)
);

-- ---------- Webhooks ----------
CREATE TABLE webhooks (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  name            TEXT NOT NULL,
  url             TEXT NOT NULL,
  secret          TEXT,
  events          TEXT[] NOT NULL DEFAULT '{}',  -- ['campaign.created', 'kpi.threshold_exceeded']
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  last_triggered_at TIMESTAMPTZ,
  failure_count   INTEGER NOT NULL DEFAULT 0,
  created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- Exports (log de exports) ----------
CREATE TABLE exports (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
  export_type     TEXT NOT NULL,               -- 'csv', 'xlsx', 'pdf'
  resource_type   TEXT NOT NULL,
  query_config    JSONB NOT NULL DEFAULT '{}'::jsonb,
  file_path       TEXT,
  row_count       INTEGER,
  file_size_bytes BIGINT,
  expires_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_exports_user ON exports(user_id, created_at DESC);

-- ---------- Triggers ----------
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