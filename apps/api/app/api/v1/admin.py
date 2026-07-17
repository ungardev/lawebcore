"""Admin router — TEMPORARY: seed data for Nestlé Venezuela demo via Supabase REST API."""

import uuid, random, asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])
SEED_TOKEN = "nestle-seed-token-2026"


class SeedStatusResponse(BaseModel):
    success: bool
    message: str
    details: dict | None = None


async def _upsert(table: str, row: dict, on_conflict_col: str | None = None) -> dict:
    """Insert or update a row via Supabase REST API (service role)."""
    from shared_core import supabase_rest
    filters = [f"{on_conflict_col}=eq.{row[on_conflict_col]}"] if on_conflict_col else None
    result = await supabase_rest.select(table=table, select="id", filters=filters, limit=1)
    if result:
        await supabase_rest.update(table=table, filters=[f"id=eq.{result[0]['id']}"], data=row)
    else:
        await supabase_rest.insert(table=table, data=row)
    return row


def _tier_by_followers(followers: int) -> str:
    if followers < 10_000: return "NANO"
    if followers < 100_000: return "MICRO"
    if followers < 500_000: return "MID"
    return "MACRO"


# ============================================================
# 1. SEED PURINA DOG CHOW
# ============================================================
async def _seed_purina() -> dict:
    USER_ID = "00000000-0000-0000-0000-000000000001"
    BU_ID   = "00000000-0000-0000-0000-000000000003"
    CLIENT_ID   = "f0000000-0000-0000-0000-000000000001"
    BRAND_ID    = "f0000000-0000-0000-0000-000000000002"
    CAMPAIGN_ID = "f0000000-0000-0000-0000-000000000003"

    # Client
    await _upsert("clients", {
        "id": CLIENT_ID, "code": "NESTLE_VE", "name": "Nestlé Venezuela",
        "legal_name": "Nestlé Venezuela C.A.", "tax_id": "J-00045678-9",
        "industry": "Alimentos y Bebidas", "website": "https://www.nestle.com.ve",
        "is_active": True, "metadata": {"country": "Venezuela", "region": "Latam"},
        "created_by": USER_ID,
    }, on_conflict_col="id")

    # Brand
    await _upsert("brands", {
        "id": BRAND_ID, "client_id": CLIENT_ID, "code": "DOG_CHOW",
        "name": "Purina Dog Chow", "category": "Alimentos para mascotas",
        "is_active": True, "metadata": {"product_line": "dog_food", "target_species": "perros"},
    }, on_conflict_col="id")

    # Campaign
    await _upsert("campaigns", {
        "id": CAMPAIGN_ID, "code": "CAMP-2026-DOGCHOW-001",
        "client_id": CLIENT_ID, "brand_id": BRAND_ID,
        "name": "#DogChowVenezuela — Amor Perruno",
        "campaign_type": "influencers", "objective": "AWARENESS",
        "influencer_tiers": ["NANO", "MICRO", "MID"],
        "target_audience": "Dueños de perros en Venezuela, 22-45 años,ABC+,zonas urbanas",
        "start_date": datetime(2026, 7, 10).date(),
        "end_date": datetime(2026, 8, 15).date(),
        "budget_total": 15000.0, "budget_currency": "USD",
        "num_influencers": 20, "status": "CAMPAÑA_INTERNA",
        "owner_user_id": USER_ID, "business_unit_id": BU_ID,
        "tags": ["pet", "dog", "venezuela", "purina", "awareness"],
        "notes": "Campaña demo para pitch Nestlé Venezuela.",
        "metadata": {"hashtags": ["#DogChowVenezuela", "#AmorPerruno", "#PurinaVE"]},
        "created_by": USER_ID,
    }, on_conflict_col="id")

    # 20 Influencers (Purina demo)
    purina_infs = [
        ("María López",     "Caracas",   8500, ["mascotas","perros"]),
        ("Carlos Martínez", "Maracaibo", 9200, ["mascotas","perros","rescate"]),
        ("Laura Rodríguez",  "Valencia",   7800, ["mascotas","husky"]),
        ("Gabriela Briceño","Caracas",  45000, ["mascotas","blogger","tips"]),
        ("Fernando Aguirre", "Valencia",  67000, ["veterinaria","salud animal"]),
        ("Carolina Meza",   "Maracaibo", 38000, ["mascotas","lifestyle"]),
        ("Andrés Felipe",   "Bogotá",   62000, ["perros","adiestramiento"]),
        ("Mariana Pernía", "Caracas",   38000, ["activismo","adopcion"]),
        ("Sergio González", "Barcelona", 19000, ["perros","aventura"]),
        ("Claudia Valles", "Barquisimeto",52000,["mascotas","cuidado"]),
        ("Ricardo López",  "C. Guayana",31000, ["perros","golden"]),
        ("Paola Andrea",   "Bogotá",   180000, ["lifestyle","mascotas"]),
        ("Miguel Bolívar", "Caracas",   250000, ["animales","educacion"]),
        ("Tatiana Fern",   "Valencia",  165000, ["veterinaria","nutricion"]),
        ("Juan Mendoza",   "Maracaibo", 150000, ["entretenimiento","mascotas"]),
        ("Ana María",      "Maracay",   28000, ["mascotas","cocker"]),
        ("Roberto Méndez", "Pto. La Cruz",14000,["perros","comedia"]),
        ("Valentina C.",   "Maracay",   22000, ["mascotas","frenchpoodle"]),
        ("Daniela Ist.",   "Bogotá",    33000, ["adopcion","mascotas"]),
        ("Javier Herrera", "Barquisimeto",21800,["perros","fotos"]),
    ]

    tier_fee = {"NANO": 150, "MICRO": 400, "MID": 1200}
    inserted = 0

    for name, city, followers, niches in purina_infs:
        tier = _tier_by_followers(followers)
        inf_id = str(uuid.uuid4())
        handle = f"@{name.lower().replace(' ','')}"

        await _upsert("influencers", {
            "id": inf_id, "full_name": name,
            "email": f"{name.lower().replace(' ','')}@gmail.com",
            "country": "VE", "city": city, "primary_tier": tier,
            "primary_handle": handle,
            "bio": f"Creador {tier.lower()} de {','.join(niches)}",
            "content_niches": niches, "languages": ["es"],
            "status": "active", "tags": [city.lower(), tier.lower()],
            "metadata": {"source": "seed_demo"},
            "source": "manual", "created_by": USER_ID,
        }, on_conflict_col="id")

        # Social account
        sa_id = str(uuid.uuid4())
        try:
            await _upsert("influencer_social_accounts", {
                "id": sa_id, "influencer_id": inf_id, "platform": "instagram",
                "handle": handle, "url": f"https://instagram.com/{handle.replace('@','')}",
                "is_primary": True,
            }, on_conflict_col="id")
        except Exception:
            pass

        # Metrics
        ms_id = str(uuid.uuid4())
        posts = random.randint(30, 200)
        er = round(random.uniform(0.02, 0.07), 4)
        avg_likes = int(followers * er)
        try:
            await _upsert("influencer_metrics_snapshot", {
                "id": ms_id, "influencer_id": inf_id, "social_account_id": sa_id,
                "snapshot_date": (datetime.utcnow() - timedelta(days=random.randint(1, 20))).date(),
                "followers": followers, "following": random.randint(200, 2000),
                "posts_count": posts, "avg_likes": avg_likes,
                "avg_comments": int(avg_likes * 0.04),
                "avg_views": int(avg_likes * 12),
                "engagement_rate": er,
                "reach_30d": random.randint(followers // 2, followers * 2),
                "impressions_30d": random.randint(followers, followers * 4),
                "audience_credibility": round(random.uniform(65, 95), 2),
                "audience_quality": round(random.uniform(60, 90), 2),
                "source": "MANUAL", "raw_payload": {},
            }, on_conflict_col="id")
        except Exception:
            pass

        # Campaign influencer
        try:
            await _upsert("campaign_influencers", {
                "id": str(uuid.uuid4()),
                "campaign_id": CAMPAIGN_ID, "influencer_id": inf_id,
                "role": "main", "tier": tier,
                "agreed_fee": tier_fee.get(tier, 200),
                "currency": "USD",
                "deliverables": [{"type": "reel", "qty": random.randint(1, 3)}],
                "status": random.choice(["CONFIRMADO", "CONTRATADO", "CONTENIDO_ENTREGADO"]),
                "contracted_at": datetime.utcnow() - timedelta(days=random.randint(2, 10)),
            }, on_conflict_col=None)
        except Exception:
            pass

        # 3 publicaciones per influencer
        for j in range(3):
            dias = random.randint(0, 20)
            horas = random.randint(8, 22)
            fecha = datetime(2026, 7, 10) + timedelta(days=dias, hours=horas)
            formato = random.choice(["reel", "post", "story", "video"])
            vistas = random.randint(800, 30000) if formato in ("reel", "video") else random.randint(200, 6000)
            alcance = int(vistas * random.uniform(1.2, 2.5))
            likes = int(alcance * random.uniform(0.03, 0.10))
            comentarios = int(likes * random.uniform(0.02, 0.06))
            try:
                await _upsert("publicaciones", {
                    "id": str(uuid.uuid4()),
                    "campaign_id": CAMPAIGN_ID, "influencer_id": inf_id,
                    "fecha_publicacion": fecha,
                    "vistas": vistas, "alcance": alcance, "likes": likes,
                    "comentarios": comentarios,
                    "compartidos": int(likes * 0.01),
                    "guardados": int(likes * 0.02),
                    "er_alcance": round(likes / alcance, 6) if alcance > 0 else 0,
                    "er_vistas": round(likes / vistas, 6) if vistas > 0 else 0,
                    "retencion": round(random.uniform(0.60, 0.90), 4),
                    "sentimiento_positivo": random.randint(5, 40),
                    "sentimiento_neutro": random.randint(2, 15),
                    "sentimiento_negativo": random.randint(0, 5),
                    "url_publicacion": f"https://instagram.com/p/{uuid.uuid4().hex[:11]}",
                    "plataforma": random.choice(["instagram", "tiktok"]),
                    "formato": formato, "source": "MANUAL",
                }, on_conflict_col=None)
            except Exception:
                pass

        inserted += 1

    return {"influencers": inserted}


# ============================================================
# 2. SEED SCOUTING VE — 15 perfiles de Ignacio
# ============================================================
async def _seed_scouting_ve() -> dict:
    USER_ID = "00000000-0000-0000-0000-000000000001"
    tier_fee = {"NANO": 150, "MICRO": 400, "MID": 1200}

    influencers = [
        ("gabrielmendezvzla",   "Gabriel Méndez",       233000, "Caracas",   ["mascotas","perros"],              [],                                    False),
        ("laikalaschnauzer",     "Lakai Lasch",          215000, "Caracas",   ["mascotas","perros"],              [],                                    False),
        ("manufung",             "Manu Fung",             69600, "N/D",      ["lifestyle","travel"],             ["ubicacion_no_compartida"],           True),
        ("maigualidav",           "Mai Guzman",            33000, "Venezuela", ["activismo","rescate"],           ["activismo_rescate"],                False),
        ("milageorgina_",         "Mila Georgina",         29700, "Venezuela", ["mascotas","perros"],              [],                                    False),
        ("mayerlingproteccionista","Mayerling",            28300, "Venezuela", ["activismo","rescate"],           ["activismo_rescate"],                False),
        ("parcerito_chihuahua",   "Parcerito Chihuahua",   24600, "Venezuela", ["mascotas","perros"],              [],                                    False),
        ("soybugui_",             "Soy Bugui",             21800, "Venezuela", ["mascotas","perros"],              [],                                    False),
        ("oriannaperezz",         "Orianna Perez",         20000, "Venezuela", ["travel","foodie","cafe"],         [],                                    True),
        ("pelirojasuik_",         "Peliroja Suik",         18700, "Venezuela", ["lifestyle"],                     ["encuadre_sugerente"],               True),
        ("franye.riv",            "Franye RIV",            10100, "Venezuela", ["mascotas","perros"],              [],                                    False),
        ("bimboykoda",            "BimBoy Koda",            8000, "Venezuela", ["mascotas","perros"],              [],                                    False),
        ("thedoberman.kronos",    "The Doberman Kronos",     5860, "Venezuela", ["mascotas","perros"],              [],                                    False),
        ("barbyag",               "Barby AG",               5770, "Venezuela", ["lifestyle","deporte"],           [],                                    True),
        ("aldeidesanchez",        "Aldei Sanchez",          3320, "Venezuela", ["moda","upcycling"],              [],                                    True),
    ]

    inserted = 0
    for handle_clean, name, followers, city, niches, alerts, is_direct in influencers:
        tier = _tier_by_followers(followers)
        inf_id = str(uuid.uuid4())
        handle = f"@{handle_clean}"
        country = "VE" if city != "N/D" else "ND"

        await _upsert("influencers", {
            "id": inf_id, "full_name": name,
            "email": f"{handle_clean}@gmail.com",
            "country": country, "city": city, "primary_tier": tier,
            "primary_handle": handle,
            "bio": f"Creador {tier.lower()} de {','.join(niches)}",
            "content_niches": niches, "languages": ["es"],
            "status": "active", "tags": [city.lower(), tier.lower()] if city != "N/D" else [tier.lower()],
            "metadata": {
                "source": "solicitud_directa_ignacio" if is_direct else "scouting_ig_hashtag",
                "alerts": alerts,
                "verified_ve": city != "N/D",
                "tier_fee_usd": tier_fee.get(tier, 200),
                "scouting_date": "2026-07-17",
            },
            "source": "manual", "created_by": USER_ID,
        }, on_conflict_col="id")

        try:
            await _upsert("influencer_social_accounts", {
                "id": str(uuid.uuid4()), "influencer_id": inf_id,
                "platform": "instagram", "handle": handle,
                "url": f"https://instagram.com/{handle_clean}",
                "is_verified": tier == "MID" and not alerts,
                "is_primary": True,
            }, on_conflict_col=None)
        except Exception:
            pass

        posts = min(500, max(20, followers // 500))
        er = round(random.uniform(0.02, 0.08), 4)
        avg_likes = int(followers * er * random.uniform(0.8, 1.2))
        try:
            await _upsert("influencer_metrics_snapshot", {
                "id": str(uuid.uuid4()), "influencer_id": inf_id, "social_account_id": None,
                "snapshot_date": datetime.utcnow().date(),
                "followers": followers, "following": random.randint(100, 2000),
                "posts_count": posts, "avg_likes": avg_likes,
                "avg_comments": int(avg_likes * 0.04),
                "avg_views": int(avg_likes * random.uniform(8, 20)),
                "engagement_rate": er,
                "reach_30d": random.randint(followers // 2, followers * 2),
                "impressions_30d": random.randint(followers, followers * 4),
                "audience_credibility": round(random.uniform(65, 95), 2),
                "audience_quality": round(random.uniform(60, 90), 2),
                "source": "MANUAL", "raw_payload": {},
            }, on_conflict_col=None)
        except Exception:
            pass

        inserted += 1

    return {"influencers": inserted}


# ============================================================
# 3. SEED MATRIZ DOLCE GUSTO — 14 perfiles Nestlé
# ============================================================
async def _seed_matriz_dg() -> dict:
    USER_ID = "00000000-0000-0000-0000-000000000001"
    tier_fee = {"NANO": 150, "MICRO": 400, "MID": 1200, "MACRO": 3000}

    influencers = [
        ("armandopoyo",          "Armando Poyo",        423000, ["lifestyle","vlogs"],              False, "CUADRO/PAN/MALTIN-POLAR/CLUB-SOCIAL","Alcance"),
        ("sognis",               "Sofia Saavedra",       366000, ["lifestyle","mamá","vlogs"],       False, "HYUNDAI/GAMA/BUCHANAS/PEPSI/HUGGIES","Alcance"),
        ("isaiaslandaeta",       "Isaias Landaeta",     331000, ["naturaleza","vlogs","travel"],     False, "7UP/CUADRO/SANTA-TERESA/PLUMROSE","Alcance"),
        ("dieguisimo",           "Diego Vallenilla",     324000, ["fotografia","turismo","historia"],  False, "MINALBA/PLUMROSE/FARMATODO/OLDPAR","Alcance"),
        ("alegmassiani",         "Alejandra Guzman",     163000, ["lifestyle","vlogs"],              False, "POLAR-LIGHT/KFC/TECNOMOBILE/OISKOS/FLIPS","Alcance"),
        ("irinabozzone",         "Irina Bozzone",       116000, ["lifestyle","vlogs","moda"],        False, "CUBITT/PAWER/H&M/SATA-TERESA/ALEO/HEINZ","Alcance"),
        ("anaiotero",            "Ana Otero",            82000, ["lifestyle","mamá"],                False, "RESTAURANTES","Alcance"),
        ("patrilucia",           "Patricia Carreño",      32800, ["lifestyle","mamá"],                True,  "NATISIMA/7UP/KRAFT/MINALBA/MIGURT","Alcance"),
        ("cocinandoconlulu",     "Lulu Dow",             6623, ["cocina"],                          True,  "LA-GANGA/PAVLOVA-CARACAS-RESTAURANTES","Alcance"),
        ("gastro.no.mia",        "Gastro No Mia",       312000, ["cocina","restaurantes"],           True,  "PLUMROSE/RESTAURANTES/SANTA TERESA/BANCAMIGA/MYKONOS","Alcance"),
        ("isabermudezfebres",    "Isabel Bermudez",     235000, ["finanzas"],                       True,  "NO","Alcance"),
        ("inacocina",            "Ina Cocina",          165000, ["cocina"],                          True,  "MASIA/SAN SIMON/SAVOY-NESTLE/","Alcance"),
        ("maribelpetrola",       "Maribel Petrola",      99300, ["lifestyle","mamá","cocina"],        True,  "NUTRI-CLARA/","Alcance"),
        ("mercedesgraureposteria","Mercedes Grau",       99600, ["lifestyle","mamá","cocina"],        True,  "CALEDONIA/DOMINOS/GRAU/NESTLE","Alcance"),
    ]

    inserted = 0
    for handle_clean, name, followers, content_niches, primera_vez, otros_trabajos, driver in influencers:
        tier = _tier_by_followers(followers)
        inf_id = str(uuid.uuid4())
        handle = f"@{handle_clean}"

        trabajos = [t.strip() for t in otros_trabajos.split("/") if t.strip() and t.strip() != "NO"]
        es_bien_hecho = "SI" in otros_trabajos and "bien hecho" in otros_trabajos
        otros_trabajos_no = otros_trabajos.strip() == "NO"

        if otros_trabajos_no:
            aprobacion = {"negocio": "na", "comunicaciones_corporativas": "na", "comunicaciones_comerciales": "na", "legal": "na"}
        elif es_bien_hecho:
            aprobacion = {"negocio": "sí_bien_hecho", "comunicaciones_corporativas": "sí_bien_hecho", "comunicaciones_comerciales": "sí_bien_hecho", "legal": "aprobado"}
        else:
            aprobacion = {"negocio": "aprobado", "comunicaciones_corporativas": "aprobado", "comunicaciones_comerciales": "aprobado", "legal": "aprobado"}

        await _upsert("influencers", {
            "id": inf_id, "full_name": name,
            "email": f"{handle_clean}@gmail.com",
            "country": "VE", "city": "Venezuela", "primary_tier": tier,
            "primary_handle": handle,
            "bio": f"Creador {tier.lower()} — driver: {driver}",
            "content_niches": content_niches, "languages": ["es"],
            "status": "active", "tags": ["venezuela", tier.lower()],
            "metadata": {
                "source": "matriz_dolce_gusto",
                "trabajo_previo_nestle": not primera_vez,
                "primera_vez_con_nestle": primera_vez,
                "trabajos_otras_marcas": trabajos,
                "aprobacion_nestle": aprobacion,
                "driver": driver,
                "tier_fee_usd": tier_fee.get(tier, 200),
            },
            "source": "manual", "created_by": USER_ID,
        }, on_conflict_col="id")

        posts = min(600, max(30, followers // 400))
        er = round(random.uniform(0.015, 0.05), 4)
        avg_likes = int(followers * er * random.uniform(0.85, 1.15))
        try:
            await _upsert("influencer_metrics_snapshot", {
                "id": str(uuid.uuid4()), "influencer_id": inf_id, "social_account_id": None,
                "snapshot_date": datetime.utcnow().date(),
                "followers": followers, "following": random.randint(200, 3000),
                "posts_count": posts, "avg_likes": avg_likes,
                "avg_comments": int(avg_likes * 0.035),
                "avg_views": int(avg_likes * random.uniform(8, 22)),
                "engagement_rate": er,
                "reach_30d": random.randint(followers // 2, followers * 3),
                "impressions_30d": random.randint(followers, followers * 5),
                "audience_credibility": round(random.uniform(68, 97), 2),
                "audience_quality": round(random.uniform(62, 92), 2),
                "source": "MANUAL", "raw_payload": {},
            }, on_conflict_col=None)
        except Exception:
            pass

        inserted += 1

    return {"influencers": inserted}


# ============================================================
# ENDPOINT
# ============================================================
@router.post("/seed", response_model=SeedStatusResponse)
async def seed_all(x_seed_token: str = Header(None)):
    """Run all demo seeds: Purina Dog Chow + Scouting VE + Matriz Dolce Gusto."""
    if x_seed_token != SEED_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid seed token")

    results, errors = {}, []

    try:
        r1 = await _seed_purina()
        results["purina"] = r1
    except Exception as e:
        errors.append(f"Purina seed error: {e}")

    try:
        r2 = await _seed_scouting_ve()
        results["scouting_ve"] = r2
    except Exception as e:
        errors.append(f"Scouting VE seed error: {e}")

    try:
        r3 = await _seed_matriz_dg()
        results["matriz_dg"] = r3
    except Exception as e:
        errors.append(f"Matriz DG seed error: {e}")

    success = len(errors) == 0
    total = sum(r.get("influencers", 0) for r in results.values())
    msg = f"Seeded {total} total influencers"
    if errors:
        msg += f"; {len(errors)} errors: {'; '.join(errors)}"

    return SeedStatusResponse(success=success, message=msg, details=results if results else None)
