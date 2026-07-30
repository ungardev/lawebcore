"""ResultRanker — scoring constants and helper functions for discovery candidates."""


TIER_BENCHMARKS = {
    "NANO_BAJO": {"followers_min": 500, "followers_max": 2_000, "er_min": 0.08, "er_max": 0.15},
    "NANO_ALTO": {"followers_min": 2_000, "followers_max": 10_000, "er_min": 0.06, "er_max": 0.12},
    "MICRO_BAJO": {"followers_min": 10_000, "followers_max": 30_000, "er_min": 0.04, "er_max": 0.10},
    "MICRO_MEDIO": {"followers_min": 30_000, "followers_max": 100_000, "er_min": 0.03, "er_max": 0.08},
    "MICRO_ALTO": {"followers_min": 100_000, "followers_max": 500_000, "er_min": 0.02, "er_max": 0.06},
    "MID_BAJO": {"followers_min": 500_000, "followers_max": 1_000_000, "er_min": 0.015, "er_max": 0.05},
    "MID_ALTO": {"followers_min": 1_000_000, "followers_max": 5_000_000, "er_min": 0.01, "er_max": 0.04},
    "MACRO_BAJO": {"followers_min": 5_000_000, "followers_max": 10_000_000, "er_min": 0.005, "er_max": 0.02},
    "MACRO_ALTO": {"followers_min": 10_000_000, "followers_max": 100_000_000, "er_min": 0.003, "er_max": 0.01},
}

PLATFORM_ENGAGEMENT_WEIGHTS = {
    Platform.INSTAGRAM: {"likes": 1.0, "comments": 2.0, "saves": 1.5},
    Platform.TIKTOK: {"likes": 0.5, "comments": 1.5, "views": 0.001},
    Platform.YOUTUBE: {"likes": 1.0, "comments": 3.0, "views": 0.0001},
    Platform.X: {"likes": 1.0, "comments": 2.0, "retweets": 2.5},
}

NICHE_KEYWORDS = {
    "moda": ["moda", "outfit", "style", "fashion", "vestuario", "look", "tendencias"],
    "belleza": ["belleza", "makeup", "skincare", "cosmetica", "beauty", "routine"],
    "fitness": ["fitness", "gym", "ejercicio", "trabajo", "muscle", "workout", "salud"],
    "tecnologia": ["tecnologia", "tech", "gadget", "celular", "innovacion", "digital"],
    "comida": ["comida", "recetas", "cocina", "food", "gastronomia", "chef", "eating"],
    "viajes": ["viajes", "travel", "turismo", "vacaciones", "destino", "viajar"],
    "lifestyle": ["lifestyle", "vida", "dia", "routine", "habitos", "cotidiano"],
    "mama": ["mama", "mamá", "maternity", "bebe", "niños", "familia", "hijos"],
    "negocios": ["negocios", "business", "emprendimiento", "startup", "empresa", "finanzas"],
    "entretenimiento": ["entretenimiento", "musica", "peliculas", "series", "cultura", "pop"],
    "cafe": ["cafe", "café", "coffee", "barista", "desayuno", "mañana"],
    "deportes": ["deportes", "sports", "futbol", "beisbol", "atletismo", "entrenamiento"],
    "arte": ["arte", "art", "pintura", "diseno", "creatividad", "ilustracion"],
    "gaming": ["gaming", "videojuegos", "games", "playstation", "xbox", "twitch"],
    "mascotas": [
        "mascotas", "pets", "animals", "perro", "perros", "dog", "dogs", "cat", "cats", "gato", "gatos",
        "animal", "mascara", "cuidado animal", "veterinaria", "petcare", "petlover", "petlovers",
        # Razas de perros
        "goldenretriever", "husky", "schnauzer", "chihuahua", "pitbull", "labrador", "beagle", "cocker",
        "bulldog", "pastor", "dalmata", "poodle", "rottweiler", "doberman", "boxer", "akita", "shiba",
        "corgi", "yorkshire", "maltés", "bichon", "dogo", "wolfdog",
        # Adopción y rescate
        "adopcion", "adopcioncanina", "rescate", "rescateanimal", "adoptame", "noalas", "apadrinar",
        "fundacioncanina", "protectoraanimal", "colombiaanimal", "venezuelaanimal",
        # Comportamiento y salud
        "adiestramiento", "entrenamiento", "obediencia", "socializacion", "saludcanina", "nutricioncanina",
        "veterinaria", "veterinarios", "petfriendly", "petfriendlyve", "petfriendlyvzla",
        # Anexos VE
        "mascotasvzla", "dogs_of_vzla", "perrosvzla", "mascotasdivertidas", "viralpets",
    ],
    "mascotas_viral": ["mascotasdivertidas", "viralpets", "mascotasvzla", "dogs_of_vzla", "perrosvzla", "mascotas_col", "petcol", "perros_colombia"],
    "hogar": ["hogar", "home", "casa", "decoracion", "decoration", "interior", "interiorismo", "hogarvzla"],
}

BUY_INTENT_KEYWORDS = [
    "precio", "donde", "link", "comprar", "tienda", "oferta", "disponible",
    "envio", "pedido", "orden", "carrito", " USD ", "$", "bs", "bolivares",
    "coupon", "descuento", "promo", "stock",
]

VE_GEO_INDICATORS = [
    "caracas", "venezuela", "vzla", "valencia", "maracaibo",
    "san cristobal", "barquisimeto", "merida", "puerto la cruz",
    "la guaira", "catia", "petare", "guarenas", "guatire",
]

IG_CONTENT_TYPES = ["clips", "reels", "carousel", "image", "video", "story"]


def calculate_ica(comments: list[str], views: int) -> float:
    """Index de Conversion Aparentada — comments with buy intent / views."""
    if not comments or views == 0:
        return 0.0
    matches = sum(
        1 for c in comments
        if any(kw in (c or "").lower() for kw in BUY_INTENT_KEYWORDS)
    )
    return round((matches / len(comments)) * 100, 2)


def calculate_geo_foco_real(
    geotags: list[str],
    captions: list[str],
    profile_bio: str = "",
) -> float:
    """Geo-Foco Real —交叉 geotags + idioma captions para validar audiencia VE real."""
    ve_signals = 0
    total_signals = 0

    for g in (geotags or []):
        g_lower = (g or "").lower()
        if any(indicator in g_lower for indicator in VE_GEO_INDICATORS):
            ve_signals += 1
        total_signals += 1

    for caption in (captions or []):
        cap_lower = (caption or "").lower()
        spanish_keywords = sum(1 for w in ["para ", "con ", "mi ", "los ", "las ", "del ", "una "] if w in cap_lower)
        if spanish_keywords > 2:
            ve_signals += 0.5
        total_signals += 1

    if profile_bio:
        bio_lower = profile_bio.lower()
        if any(c in bio_lower for c in ["venezuela", "vzla", "caracas", "🇻🇪"]):
            ve_signals += 2

    if total_signals == 0:
        return 0.5
    return round(min(ve_signals / total_signals, 1.0), 3)


def calculate_engagement_velocity(
    total_likes: int,
    total_comments: int,
    posts_count: int,
    days_since_first_post: int = 30,
) -> float:
    """Engagement Velocity — interacciones por dia desde publicacion."""
    if posts_count == 0 or days_since_first_post == 0:
        return 0.0
    total_interactions = (total_likes or 0) + (total_comments or 0)
    return round(total_interactions / max(posts_count, 1) / max(days_since_first_post, 1), 4)


def calculate_business_intent(profile: dict) -> float:
    """Business Intent Score — 0-1 disposicion comercial del perfil."""
    score = 0.0
    if profile.get("externalUrl"):
        score += 0.4
    about = profile.get("about") or {}
    if about.get("facebookPage"):
        score += 0.4
    if profile.get("isBusinessAccount") or profile.get("isBusiness"):
        score += 0.2
    if profile.get("isVerified"):
        score += 0.1
    return round(min(score, 1.0), 3)

