"""Admin router — TEMPORARY: seed data for Nestlé Venezuela demo."""

import asyncio
import random
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])

SEED_TOKEN = "nestle-seed-token-2026"

SCOPING_FIXTURES = [
    ("Nestlé Venezuela", "f0000000-0000-0000-0000-000000000001"),
    ("Purina Dog Chow",  "f0000000-0000-0000-0000-000000000002"),
    ("#DogChowVenezuela", "f0000000-0000-0000-0000-000000000003"),
]


class SeedStatusResponse(BaseModel):
    success: bool
    message: str
    details: dict | None = None


async def _run_seed_purina(db_url: str) -> dict:
    import asyncpg
    USER_ID = "00000000-0000-0000-0000-000000000001"
    BU_ID   = "00000000-0000-0000-0000-000000000003"
    CLIENT_ID  = "f0000000-0000-0000-0000-000000000001"
    BRAND_ID   = "f0000000-0000-0000-0000-000000000002"
    CAMPAIGN_ID = "f0000000-0000-0000-0000-000000000003"

    conn = await asyncpg.connect(db_url)

    # Seed client
    await conn.execute("""
        INSERT INTO clients (id, code, name, legal_name, tax_id, industry, website, is_active, metadata, created_by)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name
    """, CLIENT_ID, "NESTLE_VE", "Nestlé Venezuela", "Nestlé Venezuela C.A.",
        "J-00045678-9", "Alimentos y Bebidas", "https://www.nestle.com.ve",
        True, {"country":"Venezuela","region":"Latam"}, USER_ID)

    # Seed brand
    await conn.execute("""
        INSERT INTO brands (id, client_id, code, name, category, is_active, metadata)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT (client_id, code) DO UPDATE SET name=EXCLUDED.name
    """, BRAND_ID, CLIENT_ID, "DOG_CHOW", "Purina Dog Chow",
        "Alimentos para mascotas", True, {"product_line":"dog_food","target_species":"perros"})

    # Seed campaign
    await conn.execute("""
        INSERT INTO campaigns (id,code,client_id,brand_id,name,campaign_type,objective,influencer_tiers,
            target_audience,start_date,end_date,budget_total,budget_currency,num_influencers,
            status,owner_user_id,business_unit_id,tags,notes,metadata,created_by)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21)
        ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, status=EXCLUDED.status
    """,
        CAMPAIGN_ID, "CAMP-2026-DOGCHOW-001", CLIENT_ID, BRAND_ID,
        "#DogChowVenezuela — Amor Perruno", "influencers", "AWARENESS",
        ["NANO","MICRO","MID"],
        "Dueños de perros en Venezuela, 22-45 años,ABC+,zonas urbanas",
        datetime(2026,7,10).date(), datetime(2026,8,15).date(),
        15000.0, "USD", 20, "CAMPAÑA_INTERNA",
        USER_ID, BU_ID,
        ["pet","dog","venezuela","purina","awareness"],
        "Campaña demo para pitch Nestlé Venezuela.",
        {"hashtags":["#DogChowVenezuela","#AmorPerruno","#PurinaVE"]},
        USER_ID)

    tiers_data = [
        ("NANO",  [("María López",     "Caracas",   8500),  ("Carlos Martínez","Maracaibo", 9200), ("Laura Rodríguez","Valencia",  7800)]),
        ("MICRO", [("Gabriela Briceño","Caracas",  45000),  ("Fernando Aguirre","Valencia",  67000), ("Carolina Meza","Maracaibo", 38000)]),
        ("MID",   [("Paola Andrea","Bogotá",    215000),   ("Miguel Bolívar","Caracas",   180000), ("Tatiana Fern","Valencia",   165000)]),
    ]

    inserted_influencers = 0
    for tier, creators in tiers_data:
        for i, (name, city, followers) in enumerate(creators):
            inf_id = str(uuid.uuid4())
            handle = f"@{name.lower().replace(' ','')}"
            bio = f"Creador de contenido {tier} de mascotas. {name}."
            niches = ["mascotas","perros"] if i % 2 == 0 else ["mascotas","animales"]
            try:
                await conn.execute("""
                    INSERT INTO influencers (id,full_name,email,country,city,primary_tier,primary_handle,
                        avatar_url,bio,content_niches,languages,status,tags,metadata,source,created_by)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                    ON CONFLICT (id) DO UPDATE SET full_name=EXCLUDED.full_name
                """, inf_id, name, f"{name.lower().replace(' ','.')}@gmail.com",
                    "VE", city, tier, handle,
                    f"https://images.unsplash.com/photo-{1500000000000 + i*1000}?w=150",
                    bio, niches, ["es"], "active",
                    [city.lower(), tier.lower()],
                    {"source":"seed_demo"}, "manual", USER_ID)

                # Social account
                sa_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO influencer_social_accounts
                        (id,influencer_id,platform,handle,url,is_primary)
                    VALUES ($1,$2,$3,$4,$5,$6)
                    ON CONFLICT (platform,handle) DO NOTHING
                """, sa_id, inf_id, "instagram", handle,
                    f"https://instagram.com/{handle.replace('@','')}", True)

                # Metrics snapshot
                ms_id = str(uuid.uuid4())
                posts = random.randint(30, 200)
                er = round(random.uniform(0.02, 0.07), 4)
                avg_likes = int(followers * er)
                await conn.execute("""
                    INSERT INTO influencer_metrics_snapshot
                        (id,influencer_id,social_account_id,snapshot_date,followers,following,
                         posts_count,avg_likes,avg_comments,avg_views,engagement_rate,
                         reach_30d,impressions_30d,audience_credibility,audience_quality,source,raw_payload)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
                    ON CONFLICT (influencer_id,social_account_id,snapshot_date,source) DO NOTHING
                """, ms_id, inf_id, sa_id, datetime.utcnow().date() - timedelta(days=random.randint(1,10)),
                    followers, random.randint(200,2000), posts,
                    avg_likes, int(avg_likes*0.04), int(avg_likes*12),
                    er, random.randint(followers//2, followers*2),
                    random.randint(followers, followers*5),
                    round(random.uniform(65,95),2), round(random.uniform(60,90),2),
                    "MANUAL", {})

                # Campaign influencer
                ci_id = str(uuid.uuid4())
                tier_fee = {"NANO":150,"MICRO":400,"MID":1200}
                await conn.execute("""
                    INSERT INTO campaign_influencers
                        (id,campaign_id,influencer_id,role,tier,agreed_fee,currency,deliverables,status,contracted_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                    ON CONFLICT (campaign_id,influencer_id) DO UPDATE SET status=EXCLUDED.status
                """, ci_id, CAMPAIGN_ID, inf_id, "main", tier,
                    tier_fee.get(tier,200), "USD",
                    [{"type":"reel","qty":random.randint(1,3)},{"type":"story","qty":random.randint(3,6)}],
                    random.choice(["CONFIRMADO","CONTRATADO","CONTENIDO_ENTREGADO"]),
                    datetime.utcnow() - timedelta(days=random.randint(2,10)))

                # Publicaciones (3 per influencer)
                for j in range(3):
                    pub_id = str(uuid.uuid4())
                    dias = random.randint(0, 20)
                    horas = random.randint(8, 22)
                    fecha = datetime(2026,7,10) + timedelta(days=dias, hours=horas)
                    formato = random.choice(["reel","post","story","video"])
                    vistas = random.randint(800, 30000) if formato in ("reel","video") else random.randint(200, 6000)
                    alcance = int(vistas * random.uniform(1.2, 2.5))
                    likes = int(alcance * random.uniform(0.03, 0.10))
                    comentarios = int(likes * random.uniform(0.02, 0.06))
                    await conn.execute("""
                        INSERT INTO publicaciones
                            (id,campaign_id,influencer_id,fecha_publicacion,vistas,alcance,likes,
                             comentarios,compartidos,guardados,er_alcance,er_vistas,retencion,
                             sentimiento_positivo,sentimiento_neutro,sentimiento_negativo,
                             url_publicacion,plataforma,formato,source)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20)
                    """, pub_id, CAMPAIGN_ID, inf_id, fecha,
                        vistas, alcance, likes, comentarios,
                        int(likes*0.01), int(likes*0.02),
                        round(likes/alcance, 6) if alcance > 0 else 0,
                        round(likes/vistas, 6) if vistas > 0 else 0,
                        round(random.uniform(0.60, 0.90), 4),
                        random.randint(5,40), random.randint(2,15), random.randint(0,5),
                        f"https://instagram.com/p/{uuid.uuid4().hex[:11]}",
                        random.choice(["instagram","tiktok"]), formato, "MANUAL")

                inserted_influencers += 1
            except Exception as e:
                print(f"  Error inserting influencer {name}: {e}")

    await conn.close()
    return {"influencers": inserted_influencers, "publicaciones_per_influencer": 3}


async def _run_seed_scouting_ve(db_url: str) -> dict:
    """Seed 15 perfiles from Scouting VE docx — real handles with real alerts."""
    import asyncpg
    USER_ID = "00000000-0000-0000-0000-000000000001"

    influencers = [
        ("gabrielmendezvzla","Gabriel Méndez","MID",233000,"Caracas","mascotas,perros","",False),
        ("laikalaschnauzer","Lakai Lasch","MID",215000,"Caracas","mascotas,perros","",False),
        ("manufung","Manu Fung","MICRO",69600,"N/D","lifestyle,travel","ubicacion_no_compartida",False),
        ("maigualidav","Mai Guzman","MICRO",33000,"Venezuela","activismo,rescate","activismo_rescate",False),
        ("milageorgina_","Mila Georgina","MICRO",29700,"Venezuela","mascotas,perros","",False),
        ("mayerlingproteccionista","Mayerling","MICRO",28300,"Venezuela","activismo,rescate","activismo_rescate",False),
        ("parcerito_chihuahua","Parcerito Chihuahua","MICRO",24600,"Venezuela","mascotas,perros","",False),
        ("soybugui_","Soy Bugui","MICRO",21800,"Venezuela","mascotas,perros","",False),
        ("oriannaperezz","Orianna Perez","MICRO",20000,"Venezuela","travel,foodie,cafe","",True),
        ("pelirojasuik_","Peliroja Suik","MICRO",18700,"Venezuela","lifestyle","encuadre_sugerente",False),
        ("franye.riv","Franye RIV","MICRO",10100,"Venezuela","mascotas,perros","",False),
        ("bimboykoda","BimBoy Koda","NANO",8000,"Venezuela","mascotas,perros","",False),
        ("thedoberman.kronos","The Doberman Kronos","NANO",5860,"Venezuela","mascotas,perros","",False),
        ("barbyag","Barby AG","NANO",5770,"Venezuela","lifestyle,deporte","",True),
        ("aldeidesanchez","Aldei Sanchez","NANO",3320,"Venezuela","moda,upcycling","",True),
    ]

    conn = await asyncpg.connect(db_url)
    inserted = 0

    for handle_clean, name, tier, followers, city, niches_str, alert, is_direct in influencers:
        inf_id = str(uuid.uuid4())
        handle = f"@{handle_clean}"
        niches = [n.strip() for n in niches_str.split(",")]
        alerts_list = [alert] if alert else []

        tier_fee = {"NANO":150,"MICRO":400,"MID":1200}

        try:
            await conn.execute("""
                INSERT INTO influencers (id,full_name,email,country,city,primary_tier,primary_handle,
                    avatar_url,bio,content_niches,languages,status,tags,metadata,source,created_by)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                ON CONFLICT (id) DO UPDATE SET full_name=EXCLUDED.full_name
            """, inf_id, name, f"{handle_clean}@gmail.com", "VE" if city != "N/D" else "ND",
                city, tier, handle, "", f"Creador {tier.lower()} de {niches_str}",
                niches, ["es"], "active", [city.lower(), tier.lower()],
                {
                    "source": "solicitud_directa_ignacio" if is_direct else "scouting_ig_hashtag",
                    "alerts": alerts_list,
                    "verified_ve": city != "N/D",
                    "tier_fee_usd": tier_fee.get(tier, 200),
                    "scouting_date": "2026-07-17"
                }, "manual", USER_ID)

            # Social account
            sa_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO influencer_social_accounts (id,influencer_id,platform,handle,url,is_verified,is_primary)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (platform,handle) DO NOTHING
            """, sa_id, inf_id, "instagram", handle,
                f"https://instagram.com/{handle_clean}", tier == "MID" and not alert, True)

            # Metrics snapshot
            ms_id = str(uuid.uuid4())
            posts = min(500, max(20, followers // 500))
            er = round(random.uniform(0.02, 0.08), 4)
            import random as _r
            avg_likes = int(followers * er * _r.uniform(0.8, 1.2))
            await conn.execute("""
                INSERT INTO influencer_metrics_snapshot
                    (id,influencer_id,social_account_id,snapshot_date,followers,following,
                     posts_count,avg_likes,avg_comments,avg_views,engagement_rate,
                     reach_30d,impressions_30d,audience_credibility,audience_quality,source,raw_payload)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
                ON CONFLICT (influencer_id,social_account_id,snapshot_date,source) DO NOTHING
            """, ms_id, inf_id, sa_id, datetime.utcnow().date(),
                followers, _r.randint(100, 2000), posts,
                avg_likes, int(avg_likes*0.04), int(avg_likes*_r.uniform(8, 20)),
                er, _r.randint(followers//2, followers*2),
                _r.randint(followers, followers*4),
                round(_r.uniform(65, 95), 2), round(_r.uniform(60, 90), 2),
                "MANUAL", {})

            inserted += 1
        except Exception as e:
            print(f"  Error inserting {name}: {e}")

    await conn.close()
    return {"influencers": inserted}


async def _run_seed_matriz_dg(db_url: str) -> dict:
    """Seed 14 perfiles from Matriz Dolce Gusto — with Nestlé approval metadata."""
    import asyncpg
    USER_ID = "00000000-0000-0000-0000-000000000001"

    influencers = [
        ("armandopoyo","Armando Poyo",423000,"MID",False,"CUADRO/PAN/MALTIN-POLAR/CLUB-SOCIAL/POLAR-LIGHT","Alcance"),
        ("sognis","Sofia Saavedra",366000,"MID",False,"HYUNDAI/GAMA/BUCHANAS/PEPSI/HUGGIES/PAN","Alcance"),
        ("isaiaslandaeta","Isaias Landaeta",331000,"MID",False,"7UP/CUADRO/SANTA-TERESA/PLUMROSE/NATUCHIPS/MCDONALDS","Alcance"),
        ("dieguisimo","Diego Vallenilla",324000,"MID",False,"MINALBA/PLUMROSE/FARMATODO/OLDPAR/MOVISTAR","Alcance"),
        ("alegmassiani","Alejandra Guzman",163000,"MID",False,"POLAR-LIGHT/KFC/TECNOMOBILE/OISKOS/FLIPS","Alcance"),
        ("irinabozzone","Irina Bozzone",116000,"MID",False,"CUBITT/PAWER/H&M/SATA-TERESA/ALEO/HEINZ/AKEOS","Alcance"),
        ("anaiotero","Ana Otero",82000,"MICRO",False,"RESTAURANTES","Alcance"),
        ("patrilucia","Patricia Carreño",32800,"MICRO",True,"NATISIMA/7UP/KRAFT/MINALBA/MIGURT","Alcance"),
        ("cocinandoconlulu","Lulu Dow",6623,"NANO",True,"LA-GANGA/PAVLOVA-CARACAS-RESTAURANTES","Alcance"),
        ("gastro.no.mia","Gastro No Mia",312000,"MID",True,"PLUMROSE/RESTAURANTES/SANTA TERESA/BANCAMIGA/MYKONOS","Alcance"),
        ("isabermudezfebres","Isabel Bermudez",235000,"MID",True,"NO","Alcance"),
        ("inacocina","Ina Cocina",165000,"MID",True,"MASIA/SAN SIMON/SAVOY-NESTLE/","Alcance"),
        ("maribelpetrola","Maribel Petrola",99300,"MICRO",True,"NUTRI-CLARA/","Alcance"),
        ("mercedesgraureposteria","Mercedes Grau",99600,"MICRO",True,"CALEDONIA/DOMINOS/GRAU/NESTLE","Alcance"),
    ]

    conn = await asyncpg.connect(db_url)
    inserted = 0

    for handle_clean, name, followers, tier, primera_vez, otros_trabajos, driver in influencers:
        inf_id = str(uuid.uuid4())
        handle = f"@{handle_clean}"
        trabajos = [t.strip() for t in otros_trabajos.split("/") if t.strip() and t.strip() != "NO"]

        # Parse approval from other work column
        aprobacion_map = {
            "negocio": "aprobado",
            "comunicaciones_corporativas": "aprobado",
            "comunicaciones_comerciales": "aprobado",
            "legal": "aprobado",
        }
        if "SI" in otros_trabajos and "bien hecho" in otros_trabajos:
            aprobacion_map = {
                "negocio": "sÍ_bien_hecho",
                "comunicaciones_corporativas": "sÍ_bien_hecho",
                "comunicaciones_comerciales": "sÍ_bien_hecho",
                "legal": "aprobado",
            }
        elif otros_trabajos == "NO":
            aprobacion_map = {
                "negocio": "na",
                "comunicaciones_corporativas": "na",
                "comunicaciones_comerciales": "na",
                "legal": "na",
            }

        tier_fee = {"NANO":150,"MICRO":400,"MID":1200}

        try:
            await conn.execute("""
                INSERT INTO influencers (id,full_name,email,country,city,primary_tier,primary_handle,
                    avatar_url,bio,content_niches,languages,status,tags,metadata,source,created_by)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                ON CONFLICT (id) DO UPDATE SET full_name=EXCLUDED.full_name
            """, inf_id, name, f"{handle_clean}@gmail.com", "VE", "Venezuela", tier, handle, "",
                f"Creador {tier.lower()} — driver: {driver}",
                ["lifestyle","vlogs"], ["es"], "active", ["venezuela", tier.lower()],
                {
                    "source": "matriz_dolce_gusto",
                    "trabajo_previo_nestle": not primera_vez,
                    "primera_vez_con_nestle": primera_vez,
                    "trabajos_otras_marcas": trabajos,
                    "aprobacion_nestle": aprobacion_map,
                    "driver": driver,
                    "tier_fee_usd": tier_fee.get(tier, 200),
                }, "manual", USER_ID)

            # Social account
            sa_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO influencer_social_accounts (id,influencer_id,platform,handle,url,is_verified,is_primary)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (platform,handle) DO NOTHING
            """, sa_id, inf_id, "instagram", handle,
                f"https://instagram.com/{handle_clean}", tier == "MID", True)

            # Metrics
            ms_id = str(uuid.uuid4())
            import random as _r
            posts = min(600, max(30, followers // 400))
            er = round(_r.uniform(0.015, 0.05), 4)
            avg_likes = int(followers * er * _r.uniform(0.85, 1.15))
            await conn.execute("""
                INSERT INTO influencer_metrics_snapshot
                    (id,influencer_id,social_account_id,snapshot_date,followers,following,
                     posts_count,avg_likes,avg_comments,avg_views,engagement_rate,
                     reach_30d,impressions_30d,audience_credibility,audience_quality,source,raw_payload)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
                ON CONFLICT (influencer_id,social_account_id,snapshot_date,source) DO NOTHING
            """, ms_id, inf_id, sa_id, datetime.utcnow().date(),
                followers, _r.randint(200, 3000), posts,
                avg_likes, int(avg_likes*0.035), int(avg_likes*_r.uniform(8, 22)),
                er, _r.randint(followers//2, followers*3),
                _r.randint(followers, followers*5),
                round(_r.uniform(68, 97), 2), round(_r.uniform(62, 92), 2),
                "MANUAL", {})

            inserted += 1
        except Exception as e:
            print(f"  Error inserting {name}: {e}")

    await conn.close()
    return {"influencers": inserted}


@router.post("/seed", response_model=SeedStatusResponse)
async def seed_all(x_seed_token: str = Header(None)):
    """Run all demo seeds: Purina Dog Chow + Scouting VE + Matriz Dolce Gusto."""
    if x_seed_token != SEED_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid seed token")

    from shared_core.config import settings
    db_url = settings.DATABASE_URL
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured on server")

    results = {}
    errors = []

    try:
        r1 = await _run_seed_purina(db_url)
        results["purina"] = r1
    except Exception as e:
        errors.append(f"Purina seed error: {e}")

    try:
        r2 = await _run_seed_scouting_ve(db_url)
        results["scouting_ve"] = r2
    except Exception as e:
        errors.append(f"Scouting VE seed error: {e}")

    try:
        r3 = await _run_seed_matriz_dg(db_url)
        results["matriz_dg"] = r3
    except Exception as e:
        errors.append(f"Matriz DG seed error: {e}")

    success = len(errors) == 0
    msg = f"Seeded {sum(r.get('influencers',0) for r in results.values())} total influencers"
    if errors:
        msg += f"; {len(errors)} errors: {'; '.join(errors)}"

    return SeedStatusResponse(success=success, message=msg, details=results if results else None)
