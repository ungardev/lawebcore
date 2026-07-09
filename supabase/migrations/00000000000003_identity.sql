-- =================================================================
-- LA WEB CORE - Migration 0003: Identity & Permissions
-- =================================================================
-- business_units, users, roles, permissions, teams

-- ---------- Business Units (departamentos / areas de la agencia) ----------
CREATE TABLE business_units (
  id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  code        TEXT NOT NULL UNIQUE,            -- e.g. 'MARKETING', 'INFLUENCERS'
  name        TEXT NOT NULL,                   -- e.g. 'Marketing & Estrategia'
  description TEXT,
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE business_units IS 'Areas/departamentos de la agencia. Usado para scopes multi-equipo (100+ usuarios).';

-- ---------- Users (mirror de auth.users con perfil extendido) ----------
CREATE TABLE users (
  id                  UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email               TEXT NOT NULL UNIQUE,
  full_name           TEXT NOT NULL,
  avatar_url          TEXT,
  phone               TEXT,
  job_title           TEXT,                            -- e.g. 'Project Manager'
  primary_bu_id       UUID REFERENCES business_units(id) ON DELETE SET NULL,
  status              user_status NOT NULL DEFAULT 'invited',
  locale              TEXT NOT NULL DEFAULT 'es-VE',
  timezone            TEXT NOT NULL DEFAULT 'America/Caracas',
  metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_login_at       TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE users IS 'Perfil extendido de usuario. FK a auth.users para auth gestionada por Supabase.';

CREATE INDEX idx_users_primary_bu ON users(primary_bu_id);
CREATE INDEX idx_users_status ON users(status);

-- ---------- Roles ----------
CREATE TABLE roles (
  id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  code        TEXT NOT NULL UNIQUE,            -- 'admin_general', 'project_manager'
  name        TEXT NOT NULL,                   -- 'Administrador General'
  description TEXT,
  is_system   BOOLEAN NOT NULL DEFAULT FALSE,  -- roles del sistema, no editables
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE roles IS 'Roles RBAC del sistema. Soportan asignacion por BU y scopes.';

-- ---------- Permissions ----------
CREATE TABLE permissions (
  id          UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  code        TEXT NOT NULL UNIQUE,            -- 'campaigns.create'
  resource    TEXT NOT NULL,                   -- 'campaigns'
  action      TEXT NOT NULL,                   -- 'create' | 'read' | 'update' | 'delete' | 'export'
  description TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE permissions IS 'Permisos granulares recurso:accion.';

-- ---------- Role <-> Permission ----------
CREATE TABLE role_permissions (
  role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (role_id, permission_id)
);

-- ---------- User <-> Role (con scope opcional por BU) ----------
CREATE TABLE user_roles (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
  business_unit_id UUID REFERENCES business_units(id) ON DELETE CASCADE, -- NULL = global
  granted_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at      TIMESTAMPTZ,
  UNIQUE (user_id, role_id, business_unit_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
CREATE INDEX idx_user_roles_bu ON user_roles(business_unit_id);

COMMENT ON TABLE user_roles IS 'Asignacion de rol a usuario, opcionalmente scoped a una Business Unit.';

-- ---------- Teams (sub-equipos dentro de un BU) ----------
CREATE TABLE teams (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  business_unit_id UUID NOT NULL REFERENCES business_units(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  description     TEXT,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE team_members (
  team_id    UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_in_team TEXT,                          -- 'lead', 'member'
  joined_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (team_id, user_id)
);

-- ---------- Updated_at trigger helper ----------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_business_units_updated_at BEFORE UPDATE ON business_units
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_roles_updated_at BEFORE UPDATE ON roles
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_teams_updated_at BEFORE UPDATE ON teams
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();