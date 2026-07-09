-- =================================================================
-- LA WEB CORE - Migration 0007: KPIs, Benchmarks, Insights
-- =================================================================

-- ---------- KPI Definitions (catalogo reutilizable) ----------
CREATE TABLE kpi_definitions (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  code            TEXT NOT NULL UNIQUE,        -- 'reach', 'engagement_rate', 'retention_pct'
  name            TEXT NOT NULL,               -- 'Reach total'
  description     TEXT,
  category        kpi_category NOT NULL,
  unit            TEXT NOT NULL,               -- 'count', 'percent', 'number', 'ratio', 'usd'
  format_hint     TEXT,                        -- 'integer', 'decimal2', 'percent'
  higher_is_better BOOLEAN NOT NULL DEFAULT TRUE,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Valores observados en el Excel:
-- VIDEOS, REACH, ENGAGEMENT, ER X, VIEWS X, RETENCION X, Insight, FORMATO GANADOR

-- ---------- Campaign KPI Values (valores concretos por campana) ----------
CREATE TABLE campaign_kpi_values (
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

CREATE INDEX idx_campaign_kpi_campaign ON campaign_kpi_values(campaign_id);
CREATE INDEX idx_campaign_kpi_definition ON campaign_kpi_values(kpi_definition_id);
CREATE INDEX idx_campaign_kpi_period ON campaign_kpi_values(period_start, period_end);

-- ---------- Benchmarks (valores esperados por segmento) ----------
CREATE TABLE benchmarks (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  kpi_definition_id UUID NOT NULL REFERENCES kpi_definitions(id) ON DELETE CASCADE,
  scope_type      TEXT NOT NULL,               -- 'global', 'industry', 'brand', 'tier', 'objective'
  scope_id        UUID,                        -- id del objeto al que aplica (brand_id, etc.)
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

CREATE INDEX idx_benchmarks_kpi ON benchmarks(kpi_definition_id);
CREATE INDEX idx_benchmarks_scope ON benchmarks(scope_type, scope_id);

COMMENT ON TABLE benchmarks IS 'Benchmarks esperados. Calculados automaticamente desde historico o definidos manualmente.';

-- ---------- Insights (manuales o generados por IA) ----------
CREATE TABLE insights (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  insight_type    TEXT NOT NULL,               -- 'qualitative', 'quantitative', 'format_winner'
  title           TEXT NOT NULL,
  description     TEXT NOT NULL,
  supporting_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_winning_format BOOLEAN NOT NULL DEFAULT FALSE,
  generated_by_ai BOOLEAN NOT NULL DEFAULT FALSE,
  ai_job_id       UUID,
  created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_insights_campaign ON insights(campaign_id);

-- ---------- Winning Formats (formato ganador por campana) ----------
CREATE TABLE winning_formats (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  format_name     TEXT NOT NULL,               -- 'POV', 'storytelling', 'tutorial', 'trend'
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