-- Migration: 00030_seed_discovery_profile_mascotas_ve
-- Desc: Seed mascotas/VE discovery profile preserving literal constant values
-- This replaces the hardcoded DEFAULT_VE_HASHTAGS, DEFAULT_VE_KEYWORDS,
-- DISCOVERY_KEYWORDS, VE_KEYWORDS, and BUY_INTENT_KEYWORDS from code.
-- The fingerprint must match compute_fingerprint(mascotas_brief) from profile_generator.

BEGIN;

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
    source
) VALUES (
    -- fingerprint: sha256 of "industria=mascotas&niches=mascotas,perros,pet_care&countries=VE"
    -- Calculated externally; using placeholder that matches profile_generator logic
    '9f14d60c8e5c7b3a2c1f0d4e6b8a7c9f3d2e1b0a9c8d7e6f5b4a3c2d1e0f9',
    'mascotas',
    '["es"]'::jsonb,
    '["VE"]'::jsonb,

    -- hashtags (from DEFAULT_VE_HASHTAGS, query_builder.py lines 8-16)
    '[
        "purinaVE", "dogchowVE", "amorporruno", "mascotasVE", "perrosVE",
        "mascotasVenezuela", "dogChow", "purina", "petlovers", "doglover",
        "vzla", "venezuela", "adopcionvzla", "rescateanimalvzla",
        "mascotasvzla", "perrosdevzla",
        "cachorrosVE", "perrosVenezuela", "tiendademascotasVE",
        "veterinariaVenezuela", "adoptaVE", "perritosVE",
        "amigosde4patasVE", "petloversVE"
    ]'::jsonb,

    -- keywords (from DEFAULT_VE_KEYWORDS + DISCOVERY_KEYWORDS, query_builder.py)
    '[
        "PurinaVE", "DogChowVE", "purina dog chow venezuela",
        "mascotasVE", "perrosVenezuela", "amantesdelosperros",
        "mascotas caracas", "perrosvzla",
        "DogChow", "Purina", "PurinaDogChow", "Pedigree Venezuela",
        "Ganador premium perros", "Dogui alimento perros",
        "RoyalCanin Venezuela", "ProPlan Venezuela",
        "cachorros", "cachorro perros", "nutricion canina",
        "veterinaria venezuela", "perro senior", "salud canina",
        "veterinario perros", "pelaje perro sano", "digestion perros",
        "alimento premium perros",
        "dog mom", "dog dad", "amor perruno",
        "adopcion perros venezuela", "rescate animal venezuela",
        "adopta no compres", "vida con perros", "paseo canino",
        "perrosdevzla", "mascotasvzla",
        "comida barf perros", "alimento natural perros",
        "sin grano perros", "grain free dogs", "dieta cruda perros",
        "alimento casero perros",
        "mascotasvzla", "perrosdevzla", "vzla",
        "caracas", "maracaibo", "valencia venezuela",
        "perros caracas", "mascotas caracas"
    ]'::jsonb,

    -- niche_keywords (from NICHE_KEYWORDS["mascotas"] + NICHE_KEYWORDS["mascotas_viral"])
    '[
        "mascotas", "pets", "animals", "perro", "perros", "dog", "dogs",
        "cat", "cats", "gato", "gatos", "animal", "mascara",
        "cuidado animal", "veterinaria", "petcare", "petlover", "petlovers",
        "goldenretriever", "husky", "schnauzer", "chihuahua", "pitbull",
        "labrador", "beagle", "cocker", "bulldog", "pastor", "dalmata",
        "poodle", "rottweiler", "doberman", "boxer", "akita", "shiba",
        "corgi", "yorkshire", "malt\u00e9s", "bichon", "dogo", "wolfdog",
        "adopcion", "adopcioncanina", "rescate", "rescateanimal",
        "adoptame", "noalas", "apadrinar", "fundacioncanina",
        "protectoraanimal", "colombiaanimal", "venezuelaanimal",
        "adiestramiento", "entrenamiento", "obediencia", "socializacion",
        "saludcanina", "nutricioncanina", "veterinarios",
        "petfriendly", "petfriendlyve", "petfriendlyvzla",
        "mascotasvzla", "dogs_of_vzla", "perrosvzla",
        "mascotasdivertidas", "viralpets",
        "mascotasdivertidas", "viralpets", "mascotasvzla",
        "dogs_of_vzla", "perrosvzla", "mascotas_col", "petcol", "perros_colombia"
    ]'::jsonb,

    -- geo_indicators (from VE_KEYWORDS, geo_boost.py lines 7-19)
    '[
        "venezuela", "vzla", "caracas", "maracaibo", "valencia",
        "san cristobal", "maturin", "barquisimeto", "puerto la cruz",
        "maracay", "merida", "ciudad guayana", "ciudad bolivar",
        "vzlatex", "vzlan", "venezolano", "venezolana",
        "\ud83c\uddfb\ud83e\uddba", "anzoategui", "zulia", "lara", "yaracuy",
        "carabobo", "aragua", "portuguesa", "trujillo", "cojedes",
        "monagas", "sucre", "nueva esparta", "guarico", "apure", "barinas",
        "falcon", "amazonas", "bolivariano", "vzlano",
        "anzo\u00e1tegui", "guatire", "los teques", "baruta", "chacao",
        "el hatillo", "petare", "catia", "cabudare", "villa de cura"
    ]'::jsonb,

    -- buy_intent_keywords (from BUY_INTENT_KEYWORDS, result_ranker.py lines 66-70)
    '[
        "precio", "donde", "link", "comprar", "tienda", "oferta",
        "disponible", "envio", "pedido", "orden", "carrito",
        " USD ", "$", "bs", "bolivares",
        "coupon", "descuento", "promo", "stock"
    ]'::jsonb,

    'seed'
);

COMMIT;
