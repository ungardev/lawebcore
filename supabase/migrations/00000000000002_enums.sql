-- =================================================================
-- LA WEB CORE - Migration 0002: Enum Types
-- =================================================================
-- All enums are kept in a central place to avoid drift across tables.

-- ---------- Identity & Permissions ----------
CREATE TYPE user_status AS ENUM ('active', 'invited', 'suspended', 'deactivated');

-- ---------- Campaign Lifecycle ----------
-- Lifecycle status aligned with the Excel workflow observed:
-- BRIEF -> CONTACTANDO -> PLAN_DE_CUENTAS -> PULL -> CAMPAÑA_INTERNA -> REPORTE -> TERMINADA
CREATE TYPE campaign_status AS ENUM (
  'BRIEF',
  'CONTACTANDO',
  'PLAN_DE_CUENTAS',
  'PULL',
  'CAMPAÑA_INTERNA',
  'REPORTE',
  'TERMINADA',
  'CANCELADA',
  'PAUSADA'
);

CREATE TYPE campaign_objective AS ENUM (
  'AWARENESS',
  'CONSIDERACION',
  'CONVERSION',
  'GESTION_DE_CRISIS',
  'BRANDING',
  'LANZAMIENTO',
  'RETENCION'
);

CREATE TYPE influencer_tier AS ENUM (
  'NANO',    -- < 10K followers
  'MICRO',   -- 10K - 100K
  'MID',     -- 100K - 500K
  'MACRO',   -- > 500K
  'MEGA',    -- celebrities
  'MIX'      -- multiple tiers combined in one campaign
);

CREATE TYPE campaign_influencer_status AS ENUM (
  'PROPUESTO',
  'CONTACTADO',
  'CONFIRMADO',
  'CONTRATADO',
  'CONTENIDO_ENTREGADO',
  'PAGADO',
  'RECHAZADO',
  'CANCELADO'
);

CREATE TYPE campaign_link_type AS ENUM (
  'BRIEF',
  'DOCUMENTO_INDUCCION',
  'CONTRATO',
  'HOOK',
  'AUTOMATIZACION',
  'FORMULARIO',
  'PULL',
  'PLAN_DE_CUENTAS',
  'CAMPANA_INTERNA',
  'DRIVE',
  'REPORTE',
  'CANVA',
  'TRELLO',
  'HYPEAUDITOR',
  'OTRO'
);

-- ---------- KPIs ----------
CREATE TYPE kpi_category AS ENUM (
  'ALCANCE',
  'ENGAGEMENT',
  'CONVERSION',
  'RETENCION',
  'AWARENESS',
  'SENTIMIENTO',
  'BRAND_HEALTH'
);

CREATE TYPE kpi_source AS ENUM (
  'MANUAL',
  'HYPEAUDITOR',
  'PLATAFORMA_NATIVA',
  'FORMULARIO',
  'IMPORTADO',
  'IA'
);

-- ---------- Workflow & Tasks ----------
CREATE TYPE task_status AS ENUM ('PENDIENTE', 'EN_PROGRESO', 'BLOQUEADA', 'COMPLETADA', 'CANCELADA');
CREATE TYPE task_priority AS ENUM ('BAJA', 'MEDIA', 'ALTA', 'URGENTE');

-- ---------- Integrations ----------
CREATE TYPE integration_provider AS ENUM (
  'HYPEAUDITOR',
  'CANVA',
  'GOOGLE_DRIVE',
  'TRELLO',
  'SLACK',
  'META',
  'TIKTOK',
  'YOUTUBE',
  'OPENAI',
  'ANTHROPIC'
);

-- ---------- AI ----------
CREATE TYPE ai_job_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE ai_job_type AS ENUM (
  'EMBEDDING',
  'RAG_QUERY',
  'BRIEF_GENERATION',
  'POST_MORTEM_GENERATION',
  'INSIGHT_GENERATION',
  'FORECAST',
  'MATCHMAKING',
  'SENTIMENT_ANALYSIS'
);

-- ---------- Audit ----------
CREATE TYPE audit_action AS ENUM (
  'CREATE', 'UPDATE', 'DELETE', 'RESTORE',
  'LOGIN', 'LOGOUT', 'EXPORT', 'IMPORT',
  'STATUS_CHANGE', 'PERMISSION_CHANGE', 'ROLE_CHANGE'
);