-- =================================================================
-- LA WEB CORE - Migration 0005: Influencers
-- =================================================================

-- ---------- Influencers (DB maestra) ----------
CREATE TABLE influencers (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  full_name       TEXT NOT NULL,
  email           TEXT,
  phone           TEXT,
  country         TEXT NOT NULL DEFAULT 'VE',
  city            TEXT,
  primary_tier    influencer_tier NOT NULL DEFAULT 'NANO',
  primary_handle  TEXT,                        -- @usuario principal (IG)
  avatar_url      TEXT,
  bio             TEXT,
  content_niches  TEXT[] NOT NULL DEFAULT '{}',-- ['lifestyle','food','fitness']
  languages       TEXT[] NOT NULL DEFAULT ARRAY['es'],
  status          TEXT NOT NULL DEFAULT 'active',
  tags            TEXT[] NOT NULL DEFAULT '{}',
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  source          TEXT,                        -- 'organic', 'hypeauditor', 'manual', 'import'
  source_id       TEXT,                        -- ID en la fuente original
  created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_influencers_primary_tier ON influencers(primary_tier);
CREATE INDEX idx_influencers_status ON influencers(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_influencers_niches ON influencers USING GIN(content_niches);
CREATE INDEX idx_influencers_tags ON influencers USING GIN(tags);

COMMENT ON TABLE influencers IS 'Base de datos maestra de influencers. Snapshot de metricas en otra tabla.';

-- ---------- Social Accounts por influencer (IG, TT, YT, X) ----------
CREATE TABLE influencer_social_accounts (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  influencer_id   UUID NOT NULL REFERENCES influencers(id) ON DELETE CASCADE,
  platform        TEXT NOT NULL,               -- 'instagram' | 'tiktok' | 'youtube' | 'x' | 'facebook'
  handle          TEXT NOT NULL,               -- '@usuario'
  url             TEXT,                        -- URL completa del perfil
  platform_user_id TEXT,                       -- ID en la plataforma
  is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
  is_primary      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (platform, handle)
);

CREATE INDEX idx_social_accounts_influencer ON influencer_social_accounts(influencer_id);

-- ---------- Metrics snapshot (historico de metricas por fecha) ----------
CREATE TABLE influencer_metrics_snapshot (
  id                      UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  influencer_id           UUID NOT NULL REFERENCES influencers(id) ON DELETE CASCADE,
  social_account_id       UUID REFERENCES influencer_social_accounts(id) ON DELETE CASCADE,
  snapshot_date           DATE NOT NULL,
  followers               BIGINT,
  following               BIGINT,
  posts_count             INTEGER,
  avg_likes               NUMERIC(12, 2),
  avg_comments            NUMERIC(12, 2),
  avg_views               NUMERIC(12, 2),
  engagement_rate         NUMERIC(6, 4),        -- 0.0542 = 5.42%
  reach_30d               BIGINT,
  impressions_30d         BIGINT,
  audience_credibility    NUMERIC(5, 2),        -- HypeAuditor score
  audience_quality        NUMERIC(5, 2),
  source                  kpi_source NOT NULL DEFAULT 'MANUAL',
  raw_payload             JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (influencer_id, social_account_id, snapshot_date, source)
);

CREATE INDEX idx_metrics_snapshot_influencer ON influencer_metrics_snapshot(influencer_id);
CREATE INDEX idx_metrics_snapshot_date ON influencer_metrics_snapshot(snapshot_date DESC);

CREATE TRIGGER trg_influencers_updated_at BEFORE UPDATE ON influencers
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_social_accounts_updated_at BEFORE UPDATE ON influencer_social_accounts
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();