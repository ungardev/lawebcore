-- =================================================================
-- LA WEB CORE - Migration 0015: P.I.A.R Foundation
-- Publicaciones (métricas por creador/publicación)
-- Comentarios (para análisis de sentimiento futuro)
-- Poblar industry de los 14 clientes
-- =================================================================

-- ---------- Publicaciones (métricas por publicacion de influencer) ----------
CREATE TABLE publicaciones (
  id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  campaign_id             UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  influencer_id           UUID REFERENCES influencers(id) ON DELETE SET NULL,
  -- Métricas de la publicación
  fecha_publicacion       TIMESTAMPTZ NOT NULL,
  vistas                  BIGINT,
  alcance                 BIGINT,
  likes                   INTEGER,
  comentarios             INTEGER,
  compartidos             INTEGER,
  guardados               INTEGER,
  -- Métricas derivadas (precalculadas desde Sheets o API)
  er_alcance              NUMERIC(8, 6),    -- 0.0542 = 5.42% de quienes vieron convirtieron en engagement
  er_vistas               NUMERIC(8, 6),    -- engagement / vistas
  retencion               NUMERIC(6, 4),    -- 0.85 = 85%
  -- Sentimiento (futuro — clasificado via Claude API cuando haya comentarios)
  sentimiento_positivo     INTEGER DEFAULT 0,
  sentimiento_neutro      INTEGER DEFAULT 0,
  sentimiento_negativo    INTEGER DEFAULT 0,
  -- Metadata
  url_publicacion         TEXT,
  plataforma             TEXT NOT NULL DEFAULT 'instagram',
  formato                TEXT,              -- 'reel' | 'story' | 'post' | 'video'
  source                 TEXT NOT NULL DEFAULT 'SHEETS',  -- 'SHEETS' | 'API_IG' | 'MANUAL'
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_publicaciones_campaign ON publicaciones(campaign_id);
CREATE INDEX idx_publicaciones_influencer ON publicaciones(influencer_id);
CREATE INDEX idx_publicaciones_fecha ON publicaciones(fecha_publicacion DESC);
CREATE INDEX idx_publicaciones_campaign_fecha ON publicaciones(campaign_id, fecha_publicacion DESC);
CREATE INDEX idx_publicaciones_source ON publicaciones(source);

COMMENT ON TABLE publicaciones IS 'Métricas por publicación de influencer. Alimenta el motor de proyección P.I.A.R. Fuente: Sheets históricas (SHEETS) o Meta Graph API (API_IG).';

-- ---------- Comentarios (para clasificación de sentimiento) ----------
CREATE TABLE comentarios (
  id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  publicacion_id          UUID NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
  autor_handle            TEXT,
  texto                   TEXT NOT NULL,
  sentimiento             TEXT,              -- 'positivo' | 'neutro' | 'negativo' | null (pendiente)
  confianza              NUMERIC(3, 2),    -- 0.00 - 1.00
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_comentarios_publicacion ON comentarios(publicacion_id);
CREATE INDEX idx_comentarios_sentimiento ON comentarios(sentimiento) WHERE sentimiento IS NOT NULL;

COMMENT ON TABLE comentarios IS 'Texto de comentarios para análisis de sentimiento. Clasificado via Claude API cuando esté disponible acceso a comentarios.';

-- ---------- Poblar industry de los 14 clientes ----------
-- Taxonomía según proyecto P.I.A.R.

UPDATE clients SET industry = 'Telecomunicaciones'
  WHERE code = 'MOVILNET';

UPDATE clients SET industry = 'Alimentos'
  WHERE code = 'OREO';

UPDATE clients SET industry = 'Bebidas / Cervecería'
  WHERE code IN ('CERVEZERIA', 'SOLERA', 'POLAR');

UPDATE clients SET industry = 'Alimentos'
  WHERE code IN ('PEPSICO', 'FLIPS');

UPDATE clients SET industry = 'Alimentos'
  WHERE code = 'LA_MONTSERRATINA';

UPDATE clients SET industry = 'Alimentos y Bebidas'
  WHERE code IN ('NESCAF', 'NESTL', 'NESTL_PROFESIONAL');

UPDATE clients SET industry = 'Bebidas'
  WHERE code = 'NESTEA';

UPDATE clients SET industry = 'Alimentos'
  WHERE code = 'CHORIPANAS';

UPDATE clients SET industry = NULL
  WHERE code = 'NEW_BUISNESS';

-- ---------- Trigger para updated_at ----------
CREATE OR REPLACE FUNCTION public.set_updated_at_piar()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_publicaciones_updated_at
  BEFORE UPDATE ON publicaciones
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_piar();
