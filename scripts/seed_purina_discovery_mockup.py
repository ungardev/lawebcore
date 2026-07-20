"""
Seed script: Purina Dog Chow discovery mockup data.
Creates a discovery_run + 15 discovery_candidates to simulate a completed
discovery run for the Influencer Lens demo.

Usage:
    DATABASE_URL="postgresql://..." python scripts/seed_purina_discovery_mockup.py

Requires DATABASE_URL env var pointing to Supabase Postgres.
Uses the service-role connection string (bypasses RLS).
"""

import os
import sys
import uuid
import asyncio
from datetime import datetime, timedelta

try:
    import asyncpg
except ImportError:
    print("Install asyncpg: pip install asyncpg")
    sys.exit(1)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL env var not set")
    sys.exit(1)

BRAND_ID = "f0000000-0000-0000-0000-000000000002"
CAMPAIGN_ID = "f0000000-0000-0000-0000-000000000003"
USER_ID = "00000000-0000-0000-0000-000000000001"
BUSINESS_UNIT_ID = "00000000-0000-0000-0000-000000000003"

BRAND_HANDLE = "purinadogchow_ve"
BRAND_NAME = "Purina Dog Chow"

BRIEF_PARSED = {
    "product_name": "Purina Dog Chow",
    "industry": "Mascotas",
    "niches": ["mascotas", "perros", "cuidado animal"],
    "audience_gender": "female",
    "audience_age_min": 25,
    "audience_age_max": 44,
    "audience_countries": ["VE"],
    "audience_cities": [],
    "budget_usd": 10000,
    "tone": "emocional",
    "platforms": ["instagram"],
    "content_tones": ["auténtico", "emocional", "natural"],
    "target_audience": "Dueños de perros en Venezuela, 22-45 años, ABC+, zonas urbanas",
}

CANDIDATES = [
    {
        "platform": "instagram",
        "handle": "gabrielmendezvzla",
        "full_name": "Gabriel Méndez",
        "followers": 233000,
        "following": 1850,
        "posts_count": 1420,
        "avg_likes": 8500,
        "avg_comments": 320,
        "engagement_rate": 3.79,
        "country": "VE",
        "city": "Caracas",
        "match_score": 85,
        "niche_relevance": 90,
        "geo_relevance": 95,
        "audience_relevance": 80,
        "content_quality": 82,
        "audience_credibility": 88,
        "rationale": "Micro-mid influencer mascotas VE. Alta participación. Perfil activo en comunidad de perros.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "laikalaschnauzer",
        "full_name": "Laika Schneider",
        "followers": 215000,
        "following": 2100,
        "posts_count": 980,
        "avg_likes": 9200,
        "avg_comments": 410,
        "engagement_rate": 4.47,
        "country": "VE",
        "city": "Maracaibo",
        "match_score": 88,
        "niche_relevance": 95,
        "geo_relevance": 95,
        "audience_relevance": 85,
        "content_quality": 88,
        "audience_credibility": 90,
        "rationale": "Cuenta activa sobre perros schnauzer y mascotas. Alta engagement. Venezuela confirmada.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "manufung",
        "full_name": "Manu Fung",
        "followers": 69600,
        "following": 3200,
        "posts_count": 2100,
        "avg_likes": 2800,
        "avg_comments": 180,
        "engagement_rate": 4.28,
        "country": "VE",
        "city": " Caracas",
        "match_score": 60,
        "niche_relevance": 40,
        "geo_relevance": 70,
        "audience_relevance": 55,
        "content_quality": 65,
        "audience_credibility": 65,
        "rationale": "Lifestyle VE. Contenido偶尔 de mascotas. Ubicación verificada.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "maigualidav",
        "full_name": "Mai Gudi",
        "followers": 33000,
        "following": 1850,
        "posts_count": 890,
        "avg_likes": 2100,
        "avg_comments": 95,
        "engagement_rate": 6.65,
        "country": "VE",
        "city": "Caracas",
        "match_score": 70,
        "niche_relevance": 85,
        "geo_relevance": 95,
        "audience_relevance": 75,
        "content_quality": 78,
        "audience_credibility": 80,
        "rationale": "Activismo animal + mascotas. Alta engagement. Perfil comprometido con causa animal VE.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "milageorgina_",
        "full_name": "Mila Georgina",
        "followers": 29700,
        "following": 2100,
        "posts_count": 760,
        "avg_likes": 2400,
        "avg_comments": 140,
        "engagement_rate": 8.55,
        "country": "VE",
        "city": "Valencia",
        "match_score": 82,
        "niche_relevance": 92,
        "geo_relevance": 95,
        "audience_relevance": 80,
        "content_quality": 85,
        "audience_credibility": 82,
        "rationale": "Dog mom influencer. Contenido垂直 de mascotas/perros. Engagement excelente.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "mayerlingproteccionista",
        "full_name": "Mayerling Pereira",
        "followers": 28300,
        "following": 1650,
        "posts_count": 640,
        "avg_likes": 1950,
        "avg_comments": 110,
        "engagement_rate": 7.28,
        "country": "VE",
        "city": "Maracay",
        "match_score": 70,
        "niche_relevance": 85,
        "geo_relevance": 90,
        "audience_relevance": 72,
        "content_quality": 75,
        "audience_credibility": 78,
        "rationale": "Proteccionista animal. Rescate y adopción. Perfil alineado con valores de marca.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "parcerito_chihuahua",
        "full_name": "Parcerito Chihuahua",
        "followers": 24600,
        "following": 890,
        "posts_count": 420,
        "avg_likes": 3100,
        "avg_comments": 220,
        "engagement_rate": 13.50,
        "country": "VE",
        "city": "Barquisimeto",
        "match_score": 84,
        "niche_relevance": 95,
        "geo_relevance": 95,
        "audience_relevance": 82,
        "content_quality": 88,
        "audience_credibility": 85,
        "rationale": "Cuenta de nicho puro: chihuahuas y perros pequeños. ER altísimo. Viral potencial.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "soybugui_",
        "full_name": "Soy Bugui",
        "followers": 21800,
        "following": 1450,
        "posts_count": 580,
        "avg_likes": 1700,
        "avg_comments": 88,
        "engagement_rate": 8.20,
        "country": "VE",
        "city": "Puerto La Cruz",
        "match_score": 80,
        "niche_relevance": 90,
        "geo_relevance": 92,
        "audience_relevance": 78,
        "content_quality": 82,
        "audience_credibility": 80,
        "rationale": "Dog content creator VE. Estilo de vida con perros. Buena audiencia comprometida.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "oriannaperezz",
        "full_name": "Orianna Pérez",
        "followers": 20000,
        "following": 1920,
        "posts_count": 710,
        "avg_likes": 1200,
        "avg_comments": 65,
        "engagement_rate": 6.33,
        "country": "VE",
        "city": "Caracas",
        "match_score": 55,
        "niche_relevance": 35,
        "geo_relevance": 80,
        "audience_relevance": 50,
        "content_quality": 60,
        "audience_credibility": 60,
        "rationale": "Travel y foodie. Contenido偶尔 de mascotas. País confirmado VE.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "pelirojasuik_",
        "full_name": "Peliroja Suik",
        "followers": 18700,
        "following": 1680,
        "posts_count": 530,
        "avg_likes": 1100,
        "avg_comments": 58,
        "engagement_rate": 6.19,
        "country": "VE",
        "city": "Caracas",
        "match_score": 50,
        "niche_relevance": 30,
        "geo_relevance": 85,
        "audience_relevance": 48,
        "content_quality": 55,
        "audience_credibility": 55,
        "rationale": "Lifestyle/cinema. Contenido偶尔 de perros. Ubicación Caracas verificada.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "franye.riv",
        "full_name": "Franye Rivera",
        "followers": 10100,
        "following": 920,
        "posts_count": 340,
        "avg_likes": 1400,
        "avg_comments": 75,
        "engagement_rate": 14.60,
        "country": "VE",
        "city": "Maracaibo",
        "match_score": 78,
        "niche_relevance": 88,
        "geo_relevance": 95,
        "audience_relevance": 80,
        "content_quality": 82,
        "audience_credibility": 78,
        "rationale": "NANO influencer especializado. Alta engagement. Comunidad de perros en Zulia.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "bimboykoda",
        "full_name": "Bimbo & Yoda",
        "followers": 8000,
        "following": 450,
        "posts_count": 290,
        "avg_likes": 1100,
        "avg_comments": 68,
        "engagement_rate": 14.60,
        "country": "VE",
        "city": "Valencia",
        "match_score": 72,
        "niche_relevance": 82,
        "geo_relevance": 90,
        "audience_relevance": 75,
        "content_quality": 78,
        "audience_credibility": 75,
        "rationale": "Cuenta de dos perros. Niche específico. Engagement muy alto para su tamaño.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "thedoberman.kronos",
        "full_name": "Kronos Doberman",
        "followers": 5860,
        "following": 380,
        "posts_count": 210,
        "avg_likes": 820,
        "avg_comments": 52,
        "engagement_rate": 14.89,
        "country": "VE",
        "city": "Caracas",
        "match_score": 75,
        "niche_relevance": 85,
        "geo_relevance": 95,
        "audience_relevance": 78,
        "content_quality": 80,
        "audience_credibility": 76,
        "rationale": "Doberman especializado. Contenido educativo y de entrenamiento. Alta comunidad.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "barbyag",
        "full_name": "BarbyAG",
        "followers": 5770,
        "following": 890,
        "posts_count": 380,
        "avg_likes": 580,
        "avg_comments": 32,
        "engagement_rate": 10.61,
        "country": "VE",
        "city": "Barquisimeto",
        "match_score": 45,
        "niche_relevance": 25,
        "geo_relevance": 85,
        "audience_relevance": 42,
        "content_quality": 50,
        "audience_credibility": 50,
        "rationale": "Lifestyle/deporte. Contenido偶尔 de mascotas. País confirmado VE.",
        "status": "new",
    },
    {
        "platform": "instagram",
        "handle": "aldeidesanchez",
        "full_name": "Aldei Sanchez",
        "followers": 3320,
        "following": 620,
        "posts_count": 190,
        "avg_likes": 420,
        "avg_comments": 28,
        "engagement_rate": 13.49,
        "country": "VE",
        "city": "Maracay",
        "match_score": 40,
        "niche_relevance": 20,
        "geo_relevance": 88,
        "audience_relevance": 38,
        "content_quality": 45,
        "audience_credibility": 45,
        "rationale": "Upcycling/moda. Contenido偶尔 de perros. Audiencia joven pero engaged.",
        "status": "new",
    },
]

CONVERSATION_ID = None
MESSAGE_ID = None


async def seed():
    conn = await asyncpg.connect(DATABASE_URL)

    existing_campaign = await conn.fetchrow(
        "SELECT id FROM campaigns WHERE id = $1", UUID(CAMPAIGN_ID)
    )
    if not existing_campaign:
        print(f"ERROR: Campaign {CAMPAIGN_ID} not found. Run scripts/seed_purina.py first.")
        await conn.close()
        sys.exit(1)

    print(f"✓ Campaign {CAMPAIGN_ID} found")

    existing_run = await conn.fetchrow(
        "SELECT id FROM discovery_runs WHERE brand_id = $1 AND status = 'completed' LIMIT 1",
        UUID(BRAND_ID),
    )
    if existing_run:
        print(f"Discovery run already exists for brand {BRAND_ID}: {existing_run['id']}")
        run_id = existing_run["id"]
        overwrite = input("Overwrite existing run and candidates? [y/N]: ").strip().lower()
        if overwrite != "y":
            print("Aborted.")
            await conn.close()
            return
        await conn.execute("DELETE FROM discovery_candidates WHERE run_id = $1", run_id)
        await conn.execute("DELETE FROM discovery_messages WHERE conversation_id IN (SELECT id FROM discovery_conversations WHERE discovery_run_id = $1)", run_id)
        await conn.execute("DELETE FROM discovery_conversations WHERE discovery_run_id = $1", run_id)
        await conn.execute("DELETE FROM discovery_runs WHERE id = $1", run_id)
        print(f"  Deleted existing run {run_id}")
    else:
        run_id = uuid.uuid4()

    started_at = datetime.utcnow() - timedelta(minutes=5)
    completed_at = datetime.utcnow() - timedelta(minutes=2)

    await conn.execute(
        """
        INSERT INTO discovery_runs (
            id, bu_id, created_by, brief_text, brief_parsed,
            product_name, brand_id, industry, niches,
            audience_gender, audience_age_min, audience_age_max,
            audience_countries, budget_usd, tone, platforms,
            status, total_candidates, accepted,
            started_at, completed_at,
            metadata
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9,
            $10, $11, $12,
            $13, $14, $15, $16,
            'completed', $17, 0,
            $18, $19,
            $20
        )
        """,
        run_id,
        UUID(BUSINESS_UNIT_ID),
        UUID(USER_ID),
        "Scouting de influencers para Purina Dog Chow en Instagram Venezuela. Busco perfiles nano, micro y mid con audiencia venezolana confirmada. Interesados en mascotas, perros, entrenamiento. Presupuesto 10K USD.",
        BRIEF_PARSED,
        "Purina Dog Chow",
        UUID(BRAND_ID),
        "Mascotas",
        ["mascotas", "perros", "cuidado animal"],
        "female",
        25,
        44,
        ["VE"],
        10000,
        "emocional",
        ["instagram"],
        len(CANDIDATES),
        started_at,
        completed_at,
        {"mockup": True, "source": "purina_dog_chow_scouting_jul2026"},
    )
    print(f"✓ Created discovery_run {run_id}")

    conv_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO discovery_conversations (
            id, user_id, bu_id, state, current_step,
            discovery_run_id, accumulated_brief, message_count,
            started_at, last_message_at, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'active')
        """,
        conv_id,
        UUID(USER_ID),
        UUID(BUSINESS_UNIT_ID),
        {"step": "candidates_review"},
        "candidates_review",
        run_id,
        "Scouting de influencers para Purina Dog Chow en Instagram Venezuela",
        3,
        started_at,
        completed_at,
    )
    print(f"✓ Created discovery_conversation {conv_id}")

    msg1_id = uuid.uuid4()
    msg2_id = uuid.uuid4()
    msg3_id = uuid.uuid4()

    await conn.execute(
        """
        INSERT INTO discovery_messages (id, conversation_id, role, content, created_at)
        VALUES ($1, $2, 'user', $3, $4)
        """,
        msg1_id,
        conv_id,
        "Busco influencers para Purina Dog Chow en Instagram Venezuela. Perfiles nano, micro y mid. Presupuesto 10K USD.",
        started_at,
    )

    await conn.execute(
        """
        INSERT INTO discovery_messages (id, conversation_id, role, content, created_at)
        VALUES ($1, $2, 'assistant', $3, $4)
        """,
        msg2_id,
        conv_id,
        "Perfecto. Estoy ejecutando la búsqueda de influencers en Instagram que coincidan con tu brief de Purina Dog Chow. Buscaré perfiles venezolanos con buena audiencia y engagement en el nicho de mascotas.",
        started_at + timedelta(seconds=30),
    )

    top_5 = CANDIDATES[:5]
    summary_lines = [
        f"- **{c['handle']}** (instagram): "
        f"Score {c['match_score']}/100, "
        f"{c['followers']:,} seguidores, "
        f"ER {c['engagement_rate']:.1f}%"
        for c in top_5
    ]

    final_msg = (
        f"Terminé la búsqueda. Encontré {len(CANDIDATES)} candidatos "
        f"que coinciden con tu brief.\n\n"
        + ("Aquí están los más relevantes:\n" + "\n".join(summary_lines) + "\n\n"
        if summary_lines else "")
        + "Puedes ver todos en la lista de candidatos."
    )

    await conn.execute(
        """
        INSERT INTO discovery_messages (id, conversation_id, role, content, created_at)
        VALUES ($1, $2, 'assistant', $3, $4)
        """,
        msg3_id,
        conv_id,
        final_msg,
        completed_at,
    )
    print(f"✓ Created discovery_messages")

    for candidate in CANDIDATES:
        platform_user_id_val = f"mock_{candidate['handle']}_{uuid.uuid4().hex[:8]}"
        await conn.execute(
            """
            INSERT INTO discovery_candidates (
                id, run_id, platform, platform_user_id, handle, url,
                full_name, bio, avatar_url,
                country, city, language_primary,
                followers, following, posts_count,
                avg_likes, avg_comments,
                engagement_rate,
                audience_credibility, audience_quality,
                audience_gender_split, audience_age_buckets,
                match_score, niche_relevance, geo_relevance,
                audience_relevance, content_quality,
                rationale, status,
                source_actor_run_id, fetched_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9,
                $10, $11, $12,
                $13, $14, $15,
                $16, $17,
                $18,
                $19, $20,
                '{}', '{}',
                $21, $22, $23,
                $24, $25,
                $26, $27,
                $28, NOW()
            )
            ON CONFLICT (run_id, platform, handle) DO UPDATE SET
                followers = EXCLUDED.followers,
                match_score = EXCLUDED.match_score,
                engagement_rate = EXCLUDED.engagement_rate,
                rationale = EXCLUDED.rationale
            """,
            uuid.uuid4(),
            run_id,
            candidate["platform"],
            platform_user_id_val,
            candidate["handle"],
            f"https://instagram.com/{candidate['handle']}",
            candidate["full_name"],
            f"@{candidate['handle']} - Influencer {BRAND_NAME} Venezuela",
            f"https://images.unsplash.com/photo-{1500000000000 + hash(candidate['handle']) % 1000000000000}?w=150",
            candidate["country"],
            candidate["city"],
            "es",
            candidate["followers"],
            candidate["following"],
            candidate["posts_count"],
            candidate["avg_likes"],
            candidate["avg_comments"],
            candidate["engagement_rate"] / 100,
            candidate["audience_credibility"],
            65,
            candidate["match_score"],
            candidate["niche_relevance"],
            candidate["geo_relevance"],
            candidate["audience_relevance"],
            candidate["content_quality"],
            candidate["rationale"],
            candidate["status"],
            f"mock_run_{run_id.hex[:8]}",
        )

    print(f"✓ Inserted {len(CANDIDATES)} discovery_candidates")

    print("\n" + "=" * 60)
    print(f"DISCOVERY RUN COMPLETE")
    print(f"  Run ID:        {run_id}")
    print(f"  Conversation:  {conv_id}")
    print(f"  Candidates:    {len(CANDIDATES)}")
    print(f"  Brand:         {BRAND_NAME}")
    print("=" * 60)

    await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
