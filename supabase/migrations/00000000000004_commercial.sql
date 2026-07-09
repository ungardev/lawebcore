-- =================================================================
-- LA WEB CORE - Migration 0004: Commercial Hierarchy
-- =================================================================
-- clients (corporate), brands, contacts, contracts

-- ---------- Clients (corporate: NESTLE, PEPSICO, POLAR, etc.) ----------
CREATE TABLE clients (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  code            TEXT NOT NULL UNIQUE,        -- 'NESTLE', 'PEPSICO', 'POLAR', 'MOVILNET'
  name            TEXT NOT NULL,               -- 'Nestle Venezuela'
  legal_name      TEXT,
  tax_id          TEXT,                        -- RIF
  industry        TEXT,
  website         TEXT,
  logo_url        TEXT,
  notes           TEXT,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at      TIMESTAMPTZ                  -- soft delete
);

CREATE INDEX idx_clients_active ON clients(is_active) WHERE deleted_at IS NULL;

COMMENT ON TABLE clients IS 'Clientes corporativos. Cada cliente puede tener N marcas.';

-- ---------- Brands (por cliente: OREO, RUFFLES, DOLCE GUSTO, SOLERA...) ----------
CREATE TABLE brands (
  id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  client_id   UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
  code        TEXT NOT NULL,                   -- 'OREO', 'DOLCE_GUSTO'
  name        TEXT NOT NULL,                   -- 'Oreo Venezuela'
  category    TEXT,                            -- 'Galletas', 'Cafe', 'Cerveza'
  logo_url    TEXT,
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at  TIMESTAMPTZ,
  UNIQUE (client_id, code)
);

CREATE INDEX idx_brands_client ON brands(client_id);

COMMENT ON TABLE brands IS 'Marcas manejadas por la agencia, agrupadas por cliente corporativo.';

-- ---------- Brand Contacts (personas de contacto del cliente) ----------
CREATE TABLE brand_contacts (
  id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  brand_id    UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  full_name   TEXT NOT NULL,
  email       TEXT,
  phone       TEXT,
  job_title   TEXT,
  is_primary  BOOLEAN NOT NULL DEFAULT FALSE,
  notes       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- Client Contracts (master agreements) ----------
CREATE TABLE client_contracts (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  title           TEXT NOT NULL,
  contract_type   TEXT NOT NULL,                -- 'retainer', 'project_based', 'master'
  start_date      DATE NOT NULL,
  end_date        DATE,
  total_value     NUMERIC(15, 2),
  currency        TEXT NOT NULL DEFAULT 'USD',
  status          TEXT NOT NULL DEFAULT 'active',
  document_url    TEXT,
  notes           TEXT,
  created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_clients_updated_at BEFORE UPDATE ON clients
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_brands_updated_at BEFORE UPDATE ON brands
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_brand_contacts_updated_at BEFORE UPDATE ON brand_contacts
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_client_contracts_updated_at BEFORE UPDATE ON client_contracts
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();