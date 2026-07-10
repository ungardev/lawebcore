-- =================================================================
-- Migration 0017: Sentiment Analysis — DeepSeek pipeline
-- - Agrega comentarios_analizados (jsonb) a publicaciones
-- - Agrega sentimiento_analizado_at (timestamptz) a publicaciones
-- - Adds analyzed_comments (jsonb) to comentarios table
-- =================================================================

ALTER TABLE publicaciones
  ADD COLUMN comentarios_analizados JSONB,
  ADD COLUMN sentimiento_analizado_at TIMESTAMPTZ;

COMMENT ON COLUMN publicaciones.comentarios_analizados IS
  'Resultado del análisis de sentimiento: {positivo, neutro, negativo, total, confianza_promedio, comentarios: [{index, sentiment, confidence}]}';
COMMENT ON COLUMN publicaciones.sentimiento_analizado_at IS
  'Timestamp del último análisis de sentimiento con DeepSeek';

ALTER TABLE comentarios
  ADD COLUMN analyzed_sentiment TEXT,
  ADD COLUMN analyzed_confidence NUMERIC(3, 2),
  ADD COLUMN analyzed_at TIMESTAMPTZ;

COMMENT ON COLUMN comentarios.analyzed_sentiment IS
  'Sentimiento clasificado por DeepSeek: POSITIVO | NEUTRO | NEGATIVO | SIN_DATOS';
COMMENT ON COLUMN comentarios.analyzed_confidence IS
  'Confianza de la clasificación 0.00 - 1.00';
COMMENT ON COLUMN comentarios.analyzed_at IS
  'Timestamp del análisis';
