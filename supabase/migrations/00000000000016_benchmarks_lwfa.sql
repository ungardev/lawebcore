-- =================================================================
-- Migration 0016: Benchmarks LWFA — Tier Benchmarks
-- Sistema de benchmarks propios de LWFA para el mercado venezolano/LATAM.
-- Basado en: 06_informe_tecnico_audit_ism.md §6
-- 9 categorías reales (NANO_BAJO hasta MACRO_ALTO) con rangos
-- de seguidores, V/F, ER%, y CPV ideal.
-- =================================================================

-- Enum para las 9 subcategorías
CREATE TYPE influencer_subtier AS ENUM (
    'NANO_BAJO',
    'NANO_ALTO',
    'MICRO_BAJO',
    'MICRO_MEDIO',
    'MICRO_ALTO',
    'MID_BAJO',
    'MID_ALTO',
    'MACRO_BAJO',
    'MACRO_ALTO'
);

-- Tabla de benchmarks LWFA
CREATE TABLE tier_benchmarks (
    id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    subtier         influencer_subtier NOT NULL UNIQUE,
    -- Seguidores
    followers_min   BIGINT NOT NULL,
    followers_max   BIGINT NOT NULL,
    -- Viralidad (V/F ratio)
    vf_min          NUMERIC(5, 3) NOT NULL,
    vf_max          NUMERIC(5, 3) NOT NULL,
    -- Engagement Rate sobre vistas (%)
    er_min          NUMERIC(5, 2) NOT NULL,
    er_max          NUMERIC(5, 2) NOT NULL,
    -- CPV ideal en USD
    cpv_ideal       NUMERIC(8, 4) NOT NULL,
    -- Descripción del rol en campaña
    role_description TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tier_benchmarks_subtier ON tier_benchmarks(subtier);

-- Trigger updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at_benchmarks()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_tier_benchmarks_updated_at
    BEFORE UPDATE ON tier_benchmarks
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_benchmarks();

-- Poblar benchmarks LWFA (datos del audit §6)
INSERT INTO tier_benchmarks (subtier, followers_min, followers_max, vf_min, vf_max, er_min, er_max, cpv_ideal, role_description) VALUES
    ('NANO_BAJO',      500,      4999,   1.200, 2.500, 10.00, 15.00, 0.0050, 'Volumen + viralidad orgánica'),
    ('NANO_ALTO',      5000,     9999,   0.900, 1.500,  8.00, 12.00, 0.0080, 'Distribución orgánica'),
    ('MICRO_BAJO',     10000,    29999,  0.900, 1.800,  8.00, 13.00, 0.0100, 'Engagement + conversión'),
    ('MICRO_MEDIO',    30000,    59999,  0.800, 1.800,  6.00, 11.00, 0.0110, 'Balance performance'),
    ('MICRO_ALTO',     60000,    99999,  0.700, 1.500,  5.00, 10.00, 0.0120, 'Escala + validación'),
    ('MID_BAJO',       100000,   249999, 0.500, 1.000,  4.00,  8.00, 0.0150, 'Credibilidad'),
    ('MID_ALTO',       250000,   499999, 0.300, 0.800,  3.00,  7.00, 0.0170, 'Awareness + branding'),
    ('MACRO_BAJO',     500000,   749999, 0.400, 1.500,  3.00,  6.00, 0.0210, 'Amplificación masiva'),
    ('MACRO_ALTO',     750000,   1000000,0.200, 0.900,  2.00,  5.00, 0.0240, 'Top awareness');

-- Agregar columna sub_tier a influencers (opcional, derivada de followers)
ALTER TABLE influencers ADD COLUMN sub_tier influencer_subtier;
CREATE INDEX idx_influencers_sub_tier ON influencers(sub_tier) WHERE sub_tier IS NOT NULL;

-- Agregar columnas de scoring a publicaciones (para cacheo de scores por post)
ALTER TABLE publicaciones ADD COLUMN score_retention NUMERIC(3, 2);
ALTER TABLE publicaciones ADD COLUMN score_engagement NUMERIC(3, 2);
ALTER TABLE publicaciones ADD COLUMN score_viralidad NUMERIC(3, 2);
ALTER TABLE publicaciones ADD COLUMN score_final NUMERIC(3, 2);
ALTER TABLE publicaciones ADD COLUMN score_decision TEXT;
ALTER TABLE publicaciones ADD COLUMN score_decision_mode TEXT;  -- 'BY_POST' | 'BY_WAVE' | 'BY_PROFILE'
ALTER TABLE publicaciones ADD COLUMN scored_at TIMESTAMPTZ;

CREATE INDEX idx_publicaciones_score ON publicaciones(score_final) WHERE score_final IS NOT NULL;
CREATE INDEX idx_publicaciones_decision ON publicaciones(score_decision) WHERE score_decision IS NOT NULL;

-- Función helper para resolver sub_tier desde followers
CREATE OR REPLACE FUNCTION public.resolve_subtier(p_followers BIGINT)
RETURNS influencer_subtier LANGUAGE plpgsql AS $$
DECLARE
    result influencer_subtier;
BEGIN
    SELECT subtier INTO result
    FROM tier_benchmarks
    WHERE p_followers >= followers_min AND p_followers <= followers_max
    LIMIT 1;
    RETURN result;
END;
$$;

-- Trigger para auto-resolver sub_tier en influencers cuando cambian followers
CREATE OR REPLACE FUNCTION public.set_influencer_subtier()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.sub_tier IS NULL THEN
        NEW.sub_tier := public.resolve_subtier(
            (NEW.metadata_ ->> 'last_known_followers')::BIGINT
        );
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON TABLE tier_benchmarks IS 'Benchmarks propios de LWFA para el mercado venezolano/LATAM. 9 categorías (NANO_BAJO a MACRO_ALTO) con rangos de seguidores, V/F, ER% y CPV ideal.';
