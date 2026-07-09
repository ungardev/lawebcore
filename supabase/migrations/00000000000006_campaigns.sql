-- =================================================================
-- LA WEB CORE - Migration 0006: Campaigns (entidad principal)
-- =================================================================

-- ---------- Campaigns ----------
CREATE TABLE campaigns (
  id                  UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  code                TEXT NOT NULL UNIQUE,        -- codigo interno unico, e.g. CAMP-2026-001
  client_id           UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
  brand_id            UUID NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
  name                TEXT NOT NULL,               -- '#PorFinIlimitados', 'CAZERIA DE OREOS'
  campaign_type       TEXT,                        -- 'influencers', 'paid_media', 'evento', 'mixto'
  objective           campaign_objective NOT NULL,
  secondary_objectives campaign_objective[] NOT NULL DEFAULT '{}',
  influencer_tiers    influencer_tier[] NOT NULL DEFAULT '{}',  -- mix de tiers usados
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

CREATE INDEX idx_campaigns_client ON campaigns(client_id);
CREATE INDEX idx_campaigns_brand ON campaigns(brand_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_objective ON campaigns(objective);
CREATE INDEX idx_campaigns_dates ON campaigns(start_date, end_date);
CREATE INDEX idx_campaigns_owner ON campaigns(owner_user_id);
CREATE INDEX idx_campaigns_bu ON campaigns(business_unit_id);
CREATE INDEX idx_campaigns_tags ON campaigns USING GIN(tags);
CREATE INDEX idx_campaigns_active ON campaigns(deleted_at) WHERE deleted_at IS NULL;

COMMENT ON TABLE campaigns IS 'Entidad central. Cada campana tiene cliente, marca, objetivo, status, KPIs, influencers asignados, etc.';

-- ---------- Campaign Status History (auditoria de cambios de status) ----------
CREATE TABLE campaign_status_history (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  from_status     campaign_status,
  to_status       campaign_status NOT NULL,
  changed_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  reason          TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_status_history_campaign ON campaign_status_history(campaign_id, created_at DESC);

COMMENT ON TABLE campaign_status_history IS 'Auditoria de cada cambio de status de una campana. Alimenta analytics de ciclo de vida.';

-- ---------- Campaign Influencers (M:N con metadata) ----------
CREATE TABLE campaign_influencers (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  influencer_id   UUID NOT NULL REFERENCES influencers(id) ON DELETE RESTRICT,
  role            TEXT,                          -- 'main', 'support', 'ambassador'
  tier            influencer_tier NOT NULL,
  agreed_fee      NUMERIC(12, 2),
  currency        TEXT NOT NULL DEFAULT 'USD',
  deliverables    JSONB NOT NULL DEFAULT '[]'::jsonb,   -- [{type:'reel',qty:1}, ...]
  status          campaign_influencer_status NOT NULL DEFAULT 'PROPUESTO',
  contracted_at   TIMESTAMPTZ,
  delivered_at    TIMESTAMPTZ,
  notes           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (campaign_id, influencer_id)
);

CREATE INDEX idx_campaign_influencers_campaign ON campaign_influencers(campaign_id);
CREATE INDEX idx_campaign_influencers_influencer ON campaign_influencers(influencer_id);
CREATE INDEX idx_campaign_influencers_status ON campaign_influencers(status);

-- ---------- Campaign Links (URLs externas: Canva, Drive, HypeAuditor, Trello) ----------
CREATE TABLE campaign_links (
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

CREATE INDEX idx_campaign_links_campaign ON campaign_links(campaign_id);
CREATE INDEX idx_campaign_links_type ON campaign_links(link_type);

-- ---------- Campaign Documents (metadata de archivos) ----------
CREATE TABLE campaign_documents (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  doc_type        campaign_link_type NOT NULL,
  title           TEXT NOT NULL,
  storage_path    TEXT,                          -- path en Supabase Storage
  external_url    TEXT,                          -- o URL externa
  file_name       TEXT,
  file_size_bytes BIGINT,
  mime_type       TEXT,
  uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
  version         INTEGER NOT NULL DEFAULT 1,
  is_current      BOOLEAN NOT NULL DEFAULT TRUE,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_campaign_documents_campaign ON campaign_documents(campaign_id);
CREATE INDEX idx_campaign_documents_type ON campaign_documents(doc_type);

-- ---------- Triggers ----------
CREATE TRIGGER trg_campaigns_updated_at BEFORE UPDATE ON campaigns
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_campaign_influencers_updated_at BEFORE UPDATE ON campaign_influencers
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_campaign_links_updated_at BEFORE UPDATE ON campaign_links
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------- Trigger: log status changes ----------
CREATE OR REPLACE FUNCTION public.log_campaign_status_change()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO campaign_status_history (campaign_id, from_status, to_status, changed_by)
    VALUES (NEW.id, NULL, NEW.status, NEW.created_by);
  ELSIF (TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status) THEN
    INSERT INTO campaign_status_history (campaign_id, from_status, to_status, changed_by)
    VALUES (NEW.id, OLD.status, NEW.status, auth.uid());
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_campaign_status_change
  AFTER INSERT OR UPDATE OF status ON campaigns
  FOR EACH ROW EXECUTE FUNCTION public.log_campaign_status_change();