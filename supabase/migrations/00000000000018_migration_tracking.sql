-- =================================================================
-- Migration 0018: Schema migrations tracking
-- Tracking table para evitar re-ejecutar migraciones en cada deploy
-- =================================================================

-- Tabla de tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
  version     TEXT PRIMARY KEY,
  filename    TEXT NOT NULL,
  applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  checksum    TEXT
);

-- Backfill: marcar todas las migraciones existentes como aplicadas
-- Esto evita que el script intente re-aplicar migraciones ya existentes
INSERT INTO schema_migrations (version, filename, applied_at)
SELECT
  regexp_replace(filename, '^0*(\d+)_.*\.sql$', '\1'),
  filename,
  NOW()
FROM (VALUES
  ('00000000000001_extensions.sql'),
  ('00000000000002_enums.sql'),
  ('00000000000003_identity.sql'),
  ('00000000000004_commercial.sql'),
  ('00000000000005_influencers.sql'),
  ('00000000000006_campaigns.sql'),
  ('00000000000007_kpis.sql'),
  ('00000000000008_operations.sql'),
  ('00000000000009_ai.sql'),
  ('00000000000010_audit_integrations.sql'),
  ('00000000000011_rls.sql'),
  ('00000000000012_data_quality.sql'),
  ('00000000000015_piar_foundation.sql'),
  ('00000000000016_benchmarks_lwfa.sql'),
  ('00000000000017_sentiment_analysis.sql'),
  ('00000000000018_migration_tracking.sql')
) AS m(filename)
ON CONFLICT (version) DO NOTHING;
