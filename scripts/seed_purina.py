"""
Seed script: Purina Dog Chow / Nestlé Venezuela demo data.
Creates client, brand, campaign, 20 influencers, and 50+ publicaciones.

Usage:
    python scripts/seed_purina.py

Requires DATABASE_URL env var pointing to Supabase Postgres.
Uses the service-role connection string (bypasses RLS).
"""

import os
import sys
import uuid
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional

try:
    import asyncpg
except ImportError:
    print("Install asyncpg: pip install asyncpg")
    sys.exit(1)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL env var not set")
    sys.exit(1)


# ---- Static IDs so references work ----
BUSINESS_UNIT_ID = "00000000-0000-0000-0000-000000000003"  # LWFA default
USER_ID = "00000000-0000-0000-0000-000000000001"           # default system user


# =============================================================================
# 1. CLIENT: Nestlé Venezuela
# =============================================================================
CLIENT_ID = "f0000000-0000-0000-0000-000000000001"
CLIENT_DATA = {
    "id": CLIENT_ID,
    "code": "NESTLE_VE",
    "name": "Nestlé Venezuela",
    "legal_name": "Nestlé Venezuela C.A.",
    "tax_id": "J-00045678-9",
    "industry": "Alimentos y Bebidas",
    "website": "https://www.nestle.com.ve",
    "is_active": True,
    "metadata": {"country": "Venezuela", "region": "Latam"},
    "created_by": USER_ID,
}

# =============================================================================
# 2. BRAND: Purina Dog Chow
# =============================================================================
BRAND_ID = "f0000000-0000-0000-0000-000000000002"
BRAND_DATA = {
    "id": BRAND_ID,
    "client_id": CLIENT_ID,
    "code": "DOG_CHOW",
    "name": "Purina Dog Chow",
    "category": "Alimentos para mascotas",
    "logo_url": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=200",
    "is_active": True,
    "metadata": {"product_line": "dog_food", "target_species": "perros"},
    "created_at": datetime.utcnow(),
}

# =============================================================================
# 3. CAMPAIGN: Dog Chow Awareness Julio 2026
# =============================================================================
CAMPAIGN_ID = "f0000000-0000-0000-0000-000000000003"
CAMPAIGN_DATA = {
    "id": CAMPAIGN_ID,
    "code": "CAMP-2026-DOGCHOW-001",
    "client_id": CLIENT_ID,
    "brand_id": BRAND_ID,
    "name": "#DogChowVenezuela — Amor Perruno",
    "campaign_type": "influencers",
    "objective": "AWARENESS",
    "secondary_objectives": ["CONSIDERACION"],
    "influencer_tiers": ["NANO", "MICRO", "MID"],
    "target_audience": "Dueños de perros en Venezuela, 22-45 años,ABC+, zonas urbanas",
    "start_date": datetime(2026, 7, 10).date(),
    "end_date": datetime(2026, 8, 15).date(),
    "budget_total": 15000.00,
    "budget_currency": "USD",
    "num_influencers": 20,
    "status": "CAMPAÑA_INTERNA",
    "owner_user_id": USER_ID,
    "business_unit_id": BUSINESS_UNIT_ID,
    "tags": ["pet", "dog", "venezuela", "purina", "awareness"],
    "notes": "Campaña demo para pitch Nestlé Venezuela. Hashtags: #DogChowVenezuela #AmorPerruno",
    "metadata": {"hashtags": ["#DogChowVenezuela", "#AmorPerruno", "#PurinaVE"]},
    "created_by": USER_ID,
}


# =============================================================================
# 4. 20 INFLUENCERS — realistic Venezuelan pet influencers
# =============================================================================
INFLUENCERS = [
    # NANO influencers (< 10K)
    {
        "id": str(uuid.uuid4()),
        "full_name": "María Fernanda López",
        "email": "mflopez.pet@gmail.com",
        "phone": "+58-412-123-4567",
        "country": "VE",
        "city": "Caracas",
        "primary_tier": "NANO",
        "primary_handle": "@mariafer.pets",
        "avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150",
        "bio": "Amante de los perros 🐶 Activista animal. Caracas.",
        "content_niches": ["mascotas", "perros", "rescate animal"],
        "languages": ["es"],
        "status": "active",
        "tags": ["caracas", "rescate", "adopcion"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Carlos Enrique Martínez",
        "email": "carlosmartinez@gmail.com",
        "phone": "+58-414-234-5678",
        "country": "VE",
        "city": "Maracaibo",
        "primary_tier": "NANO",
        "primary_handle": "@carlosmascotero",
        "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150",
        "bio": "Pastor Alemán owner. Entrenamiento y consejos 🐕‍🦺",
        "content_niches": ["perros", "entrenamiento", "mascotas"],
        "languages": ["es"],
        "status": "active",
        "tags": ["maracaibo", "pastoraleman", "entrenamiento"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Laura Beatriz Rodríguez",
        "email": "laurarodriguez@gmail.com",
        "phone": "+58-412-345-6789",
        "country": "VE",
        "city": "Valencia",
        "primary_tier": "NANO",
        "primary_handle": "@laura及其dogs",
        "avatar_url": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150",
        "bio": "Dos huskies y un chihuahua. Ama la vida al aire libre ❄️🐺",
        "content_niches": ["mascotas", "husky", "perros"],
        "languages": ["es"],
        "status": "active",
        "tags": ["valencia", "husky", "chihuahua"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Andreína del Valle Sucre",
        "email": "andreina@gmail.com",
        "phone": "+58-416-456-7890",
        "country": "VE",
        "city": "Caracas",
        "primary_tier": "NANO",
        "primary_handle": "@andreina.vegana",
        "avatar_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150",
        "bio": "Soyvegana y tengo un golden retriever 🏅🐶 Vida saludable con mi perro.",
        "content_niches": ["mascotas", "lifestyle", "saludable"],
        "languages": ["es"],
        "status": "active",
        "tags": ["caracas", "golden", "lifestyle"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Javier Alejandro Herrera",
        "email": "javierherrera@gmail.com",
        "phone": "+58-424-567-8901",
        "country": "VE",
        "city": "Barquisimeto",
        "primary_tier": "NANO",
        "primary_handle": "@javierelbarbucho",
        "avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150",
        "bio": "Pastor collie y un labrador. Fotos de perros bonito 🐕",
        "content_niches": ["perros", "fotos", "mascotas"],
        "languages": ["es"],
        "status": "active",
        "tags": ["barquisimeto", "collie", "labrador"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Valentina María Colmenares",
        "email": "vcolmenares@gmail.com",
        "phone": "+58-412-678-9012",
        "country": "VE",
        "city": "Maracay",
        "primary_tier": "NANO",
        "primary_handle": "@valen.colmenares",
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
        "bio": "Cocker spaniel y french poodle. Pienso que los perros mejoran vidas 🐶💛",
        "content_niches": ["mascotas", "cocker", "perros"],
        "languages": ["es"],
        "status": "active",
        "tags": ["maracay", "cocker", "frenchpoodle"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Roberto Carlos Méndez",
        "email": "rmendez@gmail.com",
        "phone": "+58-414-789-0123",
        "country": "VE",
        "city": "Puerto La Cruz",
        "primary_tier": "NANO",
        "primary_handle": "@robertoc.pets",
        "avatar_url": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150",
        "bio": "Beagle owner. Videos graciosos de mi perro 📹🐶",
        "content_niches": ["perros", "comedia", "mascotas"],
        "languages": ["es"],
        "status": "active",
        "tags": ["puertolacruz", "beagle", "videos"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Daniela Patricia Isturiz",
        "email": "dpisturiz@gmail.com",
        "phone": "+58-416-890-1234",
        "country": "CO",
        "city": "Bogotá",
        "primary_tier": "NANO",
        "primary_handle": "@daniela_pets_co",
        "avatar_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150",
        "bio": "Adopté un mestizo. Mi vida cambió 🐾🇨🇴",
        "content_niches": ["adopcion", "mascotas", "perros"],
        "languages": ["es"],
        "status": "active",
        "tags": ["bogota", "adopcion", "mestizo"],
        "source": "manual",
        "created_by": USER_ID,
    },
    # MICRO influencers (10K - 100K)
    {
        "id": str(uuid.uuid4()),
        "full_name": "Gabriela Alejandra Briceño",
        "email": "gabrielabrice@gmail.com",
        "phone": "+58-412-901-2345",
        "country": "VE",
        "city": "Caracas",
        "primary_tier": "MICRO",
        "primary_handle": "@gabrielabrice.pets",
        "avatar_url": "https://images.unsplash.com/photo-1489424731084-a5d8b219a5bb?w=150",
        "bio": "Pet blogger Caracas. Tips, productos y mucho amor perruno 🐶❤️ 45K seguidores",
        "content_niches": ["mascotas", "blogger", "perros", "tips"],
        "languages": ["es"],
        "status": "active",
        "tags": ["caracas", "petblogger", "tips"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Fernando José Aguirre",
        "email": "fjaguirre@gmail.com",
        "phone": "+58-414-012-3456",
        "country": "VE",
        "city": "Valencia",
        "primary_tier": "MICRO",
        "primary_handle": "@feraguirre.vet",
        "avatar_url": "https://images.unsplash.com/photo-1463453091185-61582044d556?w=150",
        "bio": "Veterinario y amante de los animales. Comparto consejos de salud 🩺🐕",
        "content_niches": ["veterinaria", "salud animal", "perros"],
        "languages": ["es"],
        "status": "active",
        "tags": ["veterinaria", "valencia", "salud"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Carolina Isabel Meza",
        "email": "cimeza@gmail.com",
        "phone": "+58-416-123-4567",
        "country": "VE",
        "city": "Maracaibo",
        "primary_tier": "MICRO",
        "primary_handle": "@carolinameza.pets",
        "avatar_url": "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=150",
        "bio": "Dog mom. Influencer de mascotas en Zulia 🐶💄 28K",
        "content_niches": ["mascotas", "lifestyle", "perros"],
        "languages": ["es"],
        "status": "active",
        "tags": ["maracaibo", "dogmom", "lifestyle"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Andrés Felipe Roa",
        "email": "afroa@gmail.com",
        "phone": "+58-424-234-5678",
        "country": "CO",
        "city": "Medellín",
        "primary_tier": "MICRO",
        "primary_handle": "@andresroa.pets",
        "avatar_url": "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=150",
        "bio": "Soy adiestrador canino en Medellín. Formación positiva 🐕‍🦺🎓 62K",
        "content_niches": ["perros", "adiestramiento", "formacion"],
        "languages": ["es"],
        "status": "active",
        "tags": ["medellin", "adiestramiento", "formacion"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Mariana del Carmen Pernía",
        "email": "mdcpernia@gmail.com",
        "phone": "+58-412-345-6789",
        "country": "VE",
        "city": "Caracas",
        "primary_tier": "MICRO",
        "primary_handle": "@marianapernia",
        "avatar_url": "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=150",
        "bio": "Activista animal y blogger. Doy visibilidad a perros abandonados 🐾✊ 38K",
        "content_niches": ["activismo", "adopcion", "perros"],
        "languages": ["es"],
        "status": "active",
        "tags": ["caracas", "activismo", "adopcion"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Sergio David González",
        "email": "sdgonzalez@gmail.com",
        "phone": "+58-414-456-7890",
        "country": "VE",
        "city": "Barcelona",
        "primary_tier": "MICRO",
        "primary_handle": "@sergiod.gonzalez",
        "avatar_url": "https://images.unsplash.com/photo-1519345182560-3f2917c472ef?w=150",
        "bio": "Pastor alemán y husky siberiano. Entrenamiento y aventura 🏔️🐺 19K",
        "content_niches": ["perros", "aventura", "entrenamiento"],
        "languages": ["es"],
        "status": "active",
        "tags": ["barcelona", "pastoraleman", "aventura"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Claudia Marcelina Valles",
        "email": "cmvalles@gmail.com",
        "phone": "+58-416-567-8901",
        "country": "VE",
        "city": "Barquisimeto",
        "primary_tier": "MICRO",
        "primary_handle": "@claudiavalles",
        "avatar_url": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=150",
        "bio": "Micro-influencer de mascotas. Razas pequeñas y hacks de cuidado 🐩✨ 52K",
        "content_niches": ["mascotas", "razas pequenas", "cuidado"],
        "languages": ["es"],
        "status": "active",
        "tags": ["barquisimeto", "razasperenas", "cuidado"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Ricardo José López",
        "email": "rjlopez@gmail.com",
        "phone": "+58-424-678-9012",
        "country": "VE",
        "city": "Ciudad Guayana",
        "primary_tier": "MICRO",
        "primary_handle": "@ricardolopez.pets",
        "avatar_url": "https://images.unsplash.com/photo-1560252887-6c2ea2d4c7a6?w=150",
        "bio": "Dos golden retrievers. El mejor contenido perruno del oriente 🇻🇪🐕 31K",
        "content_niches": ["perros", "golden", "contenido"],
        "languages": ["es"],
        "status": "active",
        "tags": ["ciudadguayana", "golden", "contenido"],
        "source": "manual",
        "created_by": USER_ID,
    },
    # MID influencers (100K - 500K)
    {
        "id": str(uuid.uuid4()),
        "full_name": "Paola Andrea Torres",
        "email": "patorres@gmail.com",
        "phone": "+58-412-789-0123",
        "country": "CO",
        "city": "Bogotá",
        "primary_tier": "MID",
        "primary_handle": "@paolainfluye",
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
        "bio": "Influencer de estilo de vida y mascotas 🐾 Colombia-Venezuela. 180K 💜",
        "content_niches": ["lifestyle", "mascotas", "moda"],
        "languages": ["es"],
        "status": "active",
        "tags": ["bogota", "lifestyle", "mascotas"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Miguel Ángel Bolívar",
        "email": "mabolivar@gmail.com",
        "phone": "+58-414-890-1234",
        "country": "VE",
        "city": "Caracas",
        "primary_tier": "MID",
        "primary_handle": "@miguelbolivar.oficial",
        "avatar_url": "https://images.unsplash.com/photo-1566492031773-4f4e44671857?w=150",
        "bio": "Creator de contenido animal. Documentales perrunos en Caracas 🎬🐶 250K",
        "content_niches": ["animales", "documental", "educacion"],
        "languages": ["es"],
        "status": "active",
        "tags": ["caracas", "documental", "educacion"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Tatiana Margarita Fernández",
        "email": "tmfernandez@gmail.com",
        "phone": "+58-416-901-2345",
        "country": "VE",
        "city": "Valencia",
        "primary_tier": "MID",
        "primary_handle": "@tatiana.fernandez.pets",
        "avatar_url": "https://images.unsplash.com/photo-1558898479-33c0057a5d12?w=150",
        "bio": "Veterinaria influencer. Tips de salud y nutrición para tus perros 🩺🐕 320K",
        "content_niches": ["veterinaria", "nutricion", "salud animal"],
        "languages": ["es"],
        "status": "active",
        "tags": ["valencia", "veterinaria", "nutricion"],
        "source": "manual",
        "created_by": USER_ID,
    },
    {
        "id": str(uuid.uuid4()),
        "full_name": "Juan Carlos Mendoza",
        "email": "jcmendoza@gmail.com",
        "phone": "+58-424-012-3456",
        "country": "VE",
        "city": "Maracaibo",
        "primary_tier": "MID",
        "primary_handle": "@juancarlosmendoza.oficial",
        "avatar_url": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150",
        "bio": "Conductor y creator. Amante de los animales. 150K+ de seguidores 📺🐾",
        "content_niches": ["entretenimiento", "mascotas", "perros"],
        "languages": ["es"],
        "status": "active",
        "tags": ["maracaibo", "tv", "entretenimiento"],
        "source": "manual",
        "created_by": USER_ID,
    },
]


# =============================================================================
# 5. SOCIAL ACCOUNTS per influencer
# =============================================================================
PLATFORMS = ["instagram", "tiktok", "youtube", "x"]
PLATFORM_FOLLOWERS = {
    "NANO": (1200, 9800),
    "MICRO": (15000, 95000),
    "MID": (110000, 480000),
}


def make_social_accounts(influencer_id: str, tier: str, handle: str) -> list[dict]:
    accounts = []
    base_followers = random.randint(*PLATFORM_FOLLOWERS[tier])
    for i, platform in enumerate(PLATFORMS[: random.randint(2, 4)]):
        followers = base_followers + random.randint(-2000, 5000)
        accounts.append({
            "id": str(uuid.uuid4()),
            "influencer_id": influencer_id,
            "platform": platform,
            "handle": handle.replace("@", f"@{platform[0]}") if i > 0 else handle,
            "url": f"https://{platform}.com/{handle.replace('@', '')}",
            "platform_user_id": str(random.randint(10000000, 999999999)),
            "is_verified": tier == "MID" and random.random() > 0.5,
            "is_primary": i == 0,
        })
    return accounts


# =============================================================================
# 6. METRICS SNAPSHOTS
# =============================================================================
def make_metrics(influencer_id: str, social_account_id: str, tier: str) -> dict:
    tier_ranges = {
        "NANO": {"followers": (1200, 9800), "posts": (15, 80), "er": (0.02, 0.08)},
        "MICRO": {"followers": (15000, 95000), "posts": (50, 300), "er": (0.015, 0.055)},
        "MID": {"followers": (110000, 480000), "posts": (100, 800), "er": (0.008, 0.035)},
    }
    r = tier_ranges[tier]
    followers = random.randint(*r["followers"])
    posts = random.randint(*r["posts"])
    avg_likes = int(followers * random.uniform(*r["er"]) * random.uniform(0.8, 1.2))
    avg_comments = int(avg_likes * random.uniform(0.02, 0.08))
    avg_views = int(avg_likes * random.uniform(5, 25))
    return {
        "id": str(uuid.uuid4()),
        "influencer_id": influencer_id,
        "social_account_id": social_account_id,
        "snapshot_date": datetime.utcnow().date() - timedelta(days=random.randint(1, 30)),
        "followers": followers,
        "following": random.randint(200, 3000),
        "posts_count": posts,
        "avg_likes": avg_likes,
        "avg_comments": avg_comments,
        "avg_views": avg_views,
        "engagement_rate": round(avg_likes / followers, 4) if followers > 0 else 0,
        "reach_30d": random.randint(10000, followers * 3),
        "impressions_30d": random.randint(20000, followers * 8),
        "audience_credibility": round(random.uniform(60, 98), 2),
        "audience_quality": round(random.uniform(55, 95), 2),
        "source": "MANUAL",
        "raw_payload": {},
    }


# =============================================================================
# 7. PUBLICACIONES — 50+ posts across influencers
# =============================================================================
FORMATOS = ["reel", "post", "story", "video"]
HASHTAGS = ["#DogChowVenezuela", "#AmorPerruno", "#PurinaVE", "#PerrosFelices", "#MascotasVE",
            "#DogChow", "#AlimentacionPerro", "#PuppyLove", "#DogLife", "#PetsOfInstagram"]


def make_publicaciones(influencer_id: str, campaign_id: str, count: int = 3) -> list[dict]:
    pubs = []
    base_date = datetime(2026, 7, 10)
    for i in range(count):
        dias = random.randint(0, 35)
        horas = random.randint(8, 22)
        fecha = base_date + timedelta(days=dias, hours=horas)
        formato = random.choice(FORMATOS)
        vistas = random.randint(800, 45000) if formato in ("reel", "video") else random.randint(200, 8000)
        alcance = int(vistas * random.uniform(1.2, 3.0))
        likes = int(alcance * random.uniform(0.02, 0.12))
        comentarios = int(likes * random.uniform(0.01, 0.06))
        compartidos = int(likes * random.uniform(0.005, 0.03))
        guardados = int(likes * random.uniform(0.01, 0.05))

        pubs.append({
            "id": str(uuid.uuid4()),
            "campaign_id": campaign_id,
            "influencer_id": influencer_id,
            "fecha_publicacion": fecha,
            "vistas": vistas,
            "alcance": alcance,
            "likes": likes,
            "comentarios": comentarios,
            "compartidos": compartidos,
            "guardados": guardados,
            "er_alcance": round(likes / alcance, 6) if alcance > 0 else 0,
            "er_vistas": round(likes / vistas, 6) if vistas > 0 else 0,
            "retencion": round(random.uniform(0.55, 0.92), 4),
            "sentimiento_positivo": random.randint(5, 40),
            "sentimiento_neutro": random.randint(2, 15),
            "sentimiento_negativo": random.randint(0, 5),
            "url_publicacion": f"https://instagram.com/p/{uuid.uuid4().hex[:11]}",
            "plataforma": random.choice(["instagram", "tiktok"]),
            "formato": formato,
            "source": "MANUAL",
        })
    return pubs


# =============================================================================
# 8. CAMPAIGN INFLUENCERS link
# =============================================================================
def make_campaign_influencers(influencer_id: str, campaign_id: str, tier: str) -> dict:
    tier_fee = {"NANO": 150, "MICRO": 400, "MID": 1200}
    return {
        "id": str(uuid.uuid4()),
        "campaign_id": campaign_id,
        "influencer_id": influencer_id,
        "role": "main",
        "tier": tier,
        "agreed_fee": tier_fee.get(tier, 200),
        "currency": "USD",
        "deliverables": [{"type": "reel", "qty": random.randint(1, 3)}, {"type": "story", "qty": random.randint(3, 6)}],
        "status": random.choice(["CONFIRMADO", "CONTRATADO", "CONTENIDO_ENTREGADO"]),
        "contracted_at": datetime.utcnow() - timedelta(days=random.randint(3, 15)),
        "delivered_at": datetime.utcnow() - timedelta(days=random.randint(0, 5)) if random.random() > 0.4 else None,
    }


# =============================================================================
# MAIN — async insert
# =============================================================================
async def seed():
    print("Connecting to database...")
    conn: asyncpg.Connection = await asyncpg.connect(DATABASE_URL)

    print("Seeding Client: Nestlé Venezuela...")
    await conn.execute("""
        INSERT INTO clients (id, code, name, legal_name, tax_id, industry, website, is_active, metadata, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
    """, *[CLIENT_DATA[k] for k in ["id", "code", "name", "legal_name", "tax_id", "industry", "website", "is_active", "metadata", "created_by"]])

    print("Seeding Brand: Purina Dog Chow...")
    await conn.execute("""
        INSERT INTO brands (id, client_id, code, name, category, logo_url, is_active, metadata, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
        ON CONFLICT (client_id, code) DO UPDATE SET name = EXCLUDED.name
    """, BRAND_ID, CLIENT_ID, BRAND_DATA["code"], BRAND_DATA["name"], BRAND_DATA["category"],
        BRAND_DATA["logo_url"], True, BRAND_DATA["metadata"])

    print("Seeding Campaign: #DogChowVenezuela...")
    await conn.execute("""
        INSERT INTO campaigns (
            id, code, client_id, brand_id, name, campaign_type, objective, secondary_objectives,
            influencer_tiers, target_audience, start_date, end_date, budget_total, budget_currency,
            num_influencers, status, owner_user_id, business_unit_id, tags, notes, metadata, created_by
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, status = EXCLUDED.status
    """, *[CAMPAIGN_DATA[k] for k in [
        "id", "code", "client_id", "brand_id", "name", "campaign_type", "objective",
        "secondary_objectives", "influencer_tiers", "target_audience", "start_date", "end_date",
        "budget_total", "budget_currency", "num_influencers", "status", "owner_user_id",
        "business_unit_id", "tags", "notes", "metadata", "created_by"
    ]])

    print(f"Seeding {len(INFLUENCERS)} Influencers...")
    for inf in INFLUENCERS:
        await conn.execute("""
            INSERT INTO influencers (id, full_name, email, phone, country, city, primary_tier,
                primary_handle, avatar_url, bio, content_niches, languages, status, tags, metadata, source, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            ON CONFLICT (id) DO UPDATE SET full_name = EXCLUDED.full_name
        """, *[inf[k] for k in [
            "id", "full_name", "email", "phone", "country", "city", "primary_tier",
            "primary_handle", "avatar_url", "bio", "content_niches", "languages", "status",
            "tags", "metadata", "source", "created_by"
        ]])

        social_accounts = make_social_accounts(inf["id"], inf["primary_tier"], inf["primary_handle"])
        for sa in social_accounts:
            await conn.execute("""
                INSERT INTO influencer_social_accounts
                    (id, influencer_id, platform, handle, url, platform_user_id, is_verified, is_primary)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (platform, handle) DO NOTHING
            """, sa["id"], sa["influencer_id"], sa["platform"], sa["handle"],
                sa["url"], sa["platform_user_id"], sa["is_verified"], sa["is_primary"])

            metrics = make_metrics(inf["id"], sa["id"], inf["primary_tier"])
            await conn.execute("""
                INSERT INTO influencer_metrics_snapshot (
                    id, influencer_id, social_account_id, snapshot_date, followers, following,
                    posts_count, avg_likes, avg_comments, avg_views, engagement_rate,
                    reach_30d, impressions_30d, audience_credibility, audience_quality, source, raw_payload
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (influencer_id, social_account_id, snapshot_date, source) DO NOTHING
            """, *[metrics[k] for k in [
                "id", "influencer_id", "social_account_id", "snapshot_date", "followers",
                "following", "posts_count", "avg_likes", "avg_comments", "avg_views",
                "engagement_rate", "reach_30d", "impressions_30d", "audience_credibility",
                "audience_quality", "source", "raw_payload"
            ]])

        ci = make_campaign_influencers(inf["id"], CAMPAIGN_ID, inf["primary_tier"])
        await conn.execute("""
            INSERT INTO campaign_influencers
                (id, campaign_id, influencer_id, role, tier, agreed_fee, currency, deliverables, status, contracted_at, delivered_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (campaign_id, influencer_id) DO UPDATE SET status = EXCLUDED.status
        """, ci["id"], ci["campaign_id"], ci["influencer_id"], ci["role"], ci["tier"],
            ci["agreed_fee"], ci["currency"], ci["deliverables"], ci["status"],
            ci["contracted_at"], ci["delivered_at"])

        pubs = make_publicaciones(inf["id"], CAMPAIGN_ID, count=random.randint(2, 4))
        for pub in pubs:
            await conn.execute("""
                INSERT INTO publicaciones (
                    id, campaign_id, influencer_id, fecha_publicacion, vistas, alcance, likes,
                    comentarios, compartidos, guardados, er_alcance, er_vistas, retencion,
                    sentimiento_positivo, sentimiento_neutro, sentimiento_negativo,
                    url_publicacion, plataforma, formato, source
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
            """, *[pub[k] for k in [
                "id", "campaign_id", "influencer_id", "fecha_publicacion", "vistas", "alcance",
                "likes", "comentarios", "compartidos", "guardados", "er_alcance", "er_vistas",
                "retencion", "sentimiento_positivo", "sentimiento_neutro", "sentimiento_negativo",
                "url_publicacion", "plataforma", "formato", "source"
            ]])

    await conn.close()
    print(f"\n✅ Seed complete! {len(INFLUENCERS)} influencers, ~60 publicaciones.")


if __name__ == "__main__":
    asyncio.run(seed())
