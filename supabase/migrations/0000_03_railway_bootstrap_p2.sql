-- =================================================================
-- LA WEB CORE — Railway Bootstrap Part 2 of 5
-- Identity & Permissions + Commercial Hierarchy
-- Run in Railway Query Editor SECOND
-- =================================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

-- Identity tables
CREATE TABLE IF NOT EXISTS business_units (
    id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code        TEXT NOT NULL UNIQUE, name        TEXT NOT NULL,
    description TEXT, is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    email TEXT NOT NULL UNIQUE, full_name TEXT NOT NULL, avatar_url TEXT, phone TEXT, job_title TEXT,
    primary_bu_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
    status user_status NOT NULL DEFAULT 'invited',
    locale TEXT NOT NULL DEFAULT 'es-VE', timezone TEXT NOT NULL DEFAULT 'America/Caracas',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb, last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_primary_bu ON users(primary_bu_id);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT FALSE, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE, resource TEXT NOT NULL, action TEXT NOT NULL, description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    business_unit_id UUID REFERENCES business_units(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), expires_at TIMESTAMPTZ,
    UNIQUE (user_id, role_id, business_unit_id)
);
CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_bu ON user_roles(business_unit_id);

CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    business_unit_id UUID NOT NULL REFERENCES business_units(id) ON DELETE CASCADE,
    name TEXT NOT NULL, description TEXT, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_in_team TEXT, joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY (team_id, user_id)
);

CREATE TRIGGER trg_business_units_updated_at BEFORE UPDATE ON business_units FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_roles_updated_at BEFORE UPDATE ON roles FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_teams_updated_at BEFORE UPDATE ON teams FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Commercial tables
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, legal_name TEXT, tax_id TEXT, industry TEXT,
    website TEXT, logo_url TEXT, notes TEXT, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_clients_active ON clients(is_active) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS brands (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    code TEXT NOT NULL, name TEXT NOT NULL, category TEXT, logo_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), deleted_at TIMESTAMPTZ,
    UNIQUE (client_id, code)
);
CREATE INDEX IF NOT EXISTS idx_brands_client ON brands(client_id);

CREATE TABLE IF NOT EXISTS brand_contacts (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL, email TEXT, phone TEXT, job_title TEXT,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE, notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS client_contracts (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    title TEXT NOT NULL, contract_type TEXT NOT NULL,
    start_date DATE NOT NULL, end_date DATE, total_value NUMERIC(15,2),
    currency TEXT NOT NULL DEFAULT 'USD', status TEXT NOT NULL DEFAULT 'active',
    document_url TEXT, notes TEXT, created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_clients_updated_at BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_brands_updated_at BEFORE UPDATE ON brands FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_brand_contacts_updated_at BEFORE UPDATE ON brand_contacts FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_client_contracts_updated_at BEFORE UPDATE ON client_contracts FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
