-- =================================================================
-- LA WEB CORE - Migration 0001: Extensions
-- =================================================================

-- Required extensions for the platform
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA extensions;

-- Grant usage to standard roles
GRANT USAGE ON SCHEMA extensions TO postgres, anon, authenticated, service_role;