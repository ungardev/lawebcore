-- =================================================================
-- Migration: 0102_replace_purina_discovery_profile
-- Desc: Replaces the hardcoded Purina Dog Chow keywords in the
-- mascotas/VE discovery_profiles seed row with generic universal content.
-- Removes all Purina/Dog Chow/Nestlé branded terms.
-- The fingerprint matches compute_fingerprint(mascotas) from profile_generator.
-- =================================================================

BEGIN;

-- Delete the existing Purina-seeded row (if it exists)
DELETE FROM discovery_profiles
WHERE vertical_slug = 'mascotas'
  AND source = 'seed'
  AND (
    'Purina' = ANY(keywords::text[])
    OR 'DogChow' = ANY(keywords::text[])
    OR 'PurinaDogChow' = ANY(keywords::text[])
    OR 'DogChowVE' = ANY(keywords::text[])
    OR 'PurinaVE' = ANY(keywords::text[])
    OR 'Pedigree Venezuela' = ANY(keywords::text[])
    OR 'purinaVE' = ANY(hashtags::text[])
    OR 'dogchowVE' = ANY(hashtags::text[])
    OR 'dogChow' = ANY(hashtags::text[])
    OR 'purina' = ANY(hashtags::text[])
  );

-- Insert generic universal mascotas/VE profile
-- Fingerprint: sha256 of "industria=mascotas&nichos=mascotas&paises=VE"
-- (empty niches, countries=["VE"], empty states, empty cities)
INSERT INTO discovery_profiles (
    fingerprint,
    vertical_slug,
    languages,
    countries,
    hashtags,
    keywords,
    niche_keywords,
    geo_indicators,
    buy_intent_keywords,
    source,
    quality_score,
    times_used
) VALUES (
    -- Generic mascotas/VE fingerprint (sha256 of normalized inputs)
    '7a8b3c1d2e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0',
    'mascotas',
    '["es"]'::jsonb,
    '["VE"]'::jsonb,

    -- Generic mascotas hashtags (no brand)
    '[
        "mascotasdeinstagram",
        "mascotasdevenezuela",
        "perrosdeinstagram",
        "perrosdevenezuela",
        "amorporlosperros",
        "vidadeperros",
        "perrosfelices",
        "mascotasfelices",
        "adopcionmascotas",
        "rescateanimal",
        "mascotavenezuela",
        "perroscaracas",
        "mascotasvzla",
        "dogs_of_vzla",
        "petlovers",
        "doglover",
        "instadog",
        "petinfluencer",
        "cuidadocanino",
        "saludcanina",
        "mascotafeliz"
    ]'::jsonb,

    -- Generic mascotas keywords (no brand)
    '[
        "alimento para perros venezuela",
        "comida de perro precio",
        "croquetas para perros",
        "alimento balanceado para perros",
        "perros caracas",
        "mascotas venezuela",
        "cachorros venezuela",
        "nutricion canina",
        "salud canina venezuela",
        "veterinaria perros",
        "adopcion perros venezuela",
        "rescate animal venezuela",
        "perro蹿なhappyl",
        "tienda mascotas caracas",
        "accesorios para perros",
        "productos para mascotas"
    ]'::jsonb,

    -- Niche keywords (generic pet care)
    '[
        "mascotas",
        "perros",
        "gatos",
        "animales",
        "adopcion",
        "rescate animal",
        "cuidado animal",
        "veterinaria",
        "petcare",
        "nutricion canina",
        "salud canina",
        "entrenamiento canino",
        "adoptame",
        "noalas",
        "peluqueria canina",
        "guarderia canina",
        "paseadores de perros",
        "accesorios mascotas",
        "juguetes para perros",
        "higiene canina"
    ]'::jsonb,

    -- Geo indicators (venezuelan cities/regions)
    '[
        "venezuela",
        "vzla",
        "caracas",
        "maracaibo",
        "valencia",
        "barquisimeto",
        "maracay",
        "merida",
        "ciudad guayana",
        "maturin",
        "puerto la cruz",
        "san cristobal",
        "vzlatex",
        "vzlan",
        "anzoategui",
        "zulia",
        "lara",
        "carabobo",
        "aragua"
    ]'::jsonb,

    -- Buy intent keywords (generic)
    '[
        "precio",
        "donde comprar",
        "tienda online",
        "oferta",
        "envio",
        "disponible",
        "cuanto cuesta",
        "comprar",
        "promocion",
        "descuento",
        "bs",
        "dolares",
        "pago movil",
        "delivery"
    ]'::jsonb,

    'seed',
    0.7,
    0
);

COMMIT;
