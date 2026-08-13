-- =================================================================
-- LA WEB CORE - Migration 0012: Data Quality Issues
-- =================================================================
-- Tabla para registrar problemas detectados en la importacion de
-- datos del Excel u otras fuentes. Permite auditoria y mejora continua.

CREATE TABLE data_quality_issues (
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

CREATE INDEX idx_dqi_resource ON data_quality_issues(resource_type, resource_id);
CREATE INDEX idx_dqi_unresolved ON data_quality_issues(is_resolved) WHERE is_resolved = FALSE;
CREATE INDEX idx_dqi_issue_type ON data_quality_issues(issue_type);
CREATE INDEX idx_dqi_severity ON data_quality_issues(severity);

COMMENT ON TABLE data_quality_issues IS 'Issues detectados en la importacion de datos (Excel, integraciones, etc.)';

-- ---------- RLS ----------
ALTER TABLE data_quality_issues DISABLE ROW LEVEL SECURITY;
-- DISABLED: ALTER TABLE data_quality_issues ENABLE ROW LEVEL SECURITY; -- RLS bypassed: app connects as postgres superuser

CREATE POLICY dqi_read ON data_quality_issues FOR SELECT TO authenticated
  USING (public.is_admin_general() OR 'analista' = ANY(public.current_user_role_codes()));

CREATE POLICY dqi_write ON data_quality_issues FOR ALL TO authenticated
  USING (public.is_admin_general());

GRANT SELECT, INSERT, UPDATE, DELETE ON data_quality_issues TO authenticated;
