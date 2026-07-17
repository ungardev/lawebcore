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


async def _upsert_batch(table: str, rows: list[dict], on_conflict_col: str | None = None) -> int:
    """Insert or update multiple rows concurrently via Supabase REST API."""
    from shared_core import supabase_rest

    semaphore = asyncio.Semaphore(20)

    async def _do_row(row: dict) -> bool:
        async with semaphore:
            try:
                if on_conflict_col:
                    filter_val = row.get(on_conflict_col)
                    if filter_val is not None:
                        existing = await supabase_rest.select(
                            table=table, select="id",
                            filters=[f"{on_conflict_col}=eq.{filter_val}"], limit=1
                        )
                        if existing:
                            await supabase_rest.update(
                                table=table,
                                filters=[f"{on_conflict_col}=eq.{filter_val}"],
                                values=row
                            )
                            return True
                await supabase_rest.insert(table=table, values=row)
                return True
            except Exception as e:
                print(f"  Error inserting {table} row: {e}")
                return False

    results = await asyncio.gather(*[_do_row(r) for r in rows], return_exceptions=True)
    return sum(1 for r in results if r is True)


def _tier(followers: int) -> str:
    if followers < 10_000: return "NANO"
    if followers < 100_000: return "MICRO"
    if followers < 500_000: return "MID"
    return "MACRO"


# ================================================================
# 1. SEED PURINA DOG CHOW
# ================================================================
async def _seed_purina() -> dict:
    CID  = "f0000000-0000-0000-0000-000000000001"
    BID  = "f0000000-0000-0000-0000-000000000002"
    CAMPID = "f0000000-0000-0000-0000-000000000003"

    client_rows = [{
        "id": CID, "code": "NESTLE_VE", "name": "Nestlé Venezuela",
        "legal_name": "Nestlé Venezuela C.A.", "tax_id": "J-00045678-9",
        "industry": "Alimentos y Bebidas", "website": "https://www.nestle.com.ve",
        "is_active": True,
        "metadata": {"country": "Venezuela", "region": "Latam"},
    }]
    await _upsert_batch("clients", client_rows, on_conflict_col="id")

    brand_rows = [{
        "id": BID, "client_id": CID, "code": "DOG_CHOW",
        "name": "Purina Dog Chow", "category": "Alimentos para mascotas",
        "is_active": True,
        "metadata": {"product_line": "dog_food", "target_species": "perros"},
    }]
    await _upsert_batch("brands", brand_rows, on_conflict_col="id")

    campaign_rows = [{
        "id": CAMPID, "code": "CAMP-2026-DOGCHOW-001",
        "client_id": CID, "brand_id": BID,
        "name": "#DogChowVenezuela — Amor Perruno",
        "campaign_type": "influencers", "objective": "AWARENESS",
        "influencer_tiers": ["NANO", "MICRO", "MID"],
        "target_audience": "Dueños de perros en Venezuela, 22-45 años,ABC+,zonas urbanas",
        "start_date": "2026-07-10", "end_date": "2026-08-15",
        "budget_total": 15000.0, "budget_currency": "USD",
        "num_influencers": 20, "status": "CAMPAÑA_INTERNA",
        "tags": ["pet", "dog", "venezuela", "purina", "awareness"],
        "notes": "Campaña demo para pitch Nestlé Venezuela.",
        "metadata": {"hashtags": ["#DogChowVenezuela", "#AmorPerruno", "#PurinaVE"]},
    }]
    await _upsert_batch("campaigns", campaign_rows, on_conflict_col="id")

    purina_infs = [
        ("María López",     "Caracas",    8500, ["mascotas","perros"]),
        ("Carlos Martínez", "Maracaibo",  9200, ["mascotas","perros","rescate"]),
        ("Laura Rodríguez", "Valencia",   7800, ["mascotas","husky"]),
        ("Gabriela Briceño","Caracas",   45000, ["mascotas","blogger","tips"]),
        ("Fernando Aguirre", "Valencia",  67000, ["veterinaria","salud animal"]),
        ("Carolina Meza",  "Maracaibo", 38000, ["mascotas","lifestyle"]),
        ("Andrés Felipe",  "Bogotá",    62000, ["perros","adiestramiento"]),
        ("Mariana Pernía", "Caracas",   38000, ["activismo","adopcion"]),
        ("Sergio González", "Barcelona", 19000, ["perros","aventura"]),
        ("Claudia Valles", "Barquisimeto", 52000, ["mascotas","cuidado"]),
        ("Ricardo López",  "C. Guayana",31000, ["perros","golden"]),
        ("Paola Andrea",   "Bogotá",   180000, ["lifestyle","mascotas"]),
        ("Miguel Bolívar", "Caracas",   250000, ["animales","educacion"]),
        ("Tatiana Fern",  "Valencia",  165000, ["veterinaria","nutricion"]),
        ("Juan Mendoza",   "Maracaibo", 150000, ["entretenimiento","mascotas"]),
        ("Ana María",      "Maracay",   28000, ["mascotas","cocker"]),
        ("Roberto Méndez", "Pto. La Cruz", 14000, ["perros","comedia"]),
        ("Valentina C.",   "Maracay",   22000, ["mascotas","frenchpoodle"]),
        ("Daniela Ist.",   "Bogotá",   33000, ["adopcion","mascotas"]),
        ("Javier Herrera", "Barquisimeto", 21800, ["perros","fotos"]),
    ]

    tier_fee = {"NANO": 150, "MICRO": 400, "MID": 1200}
    inf_rows, ci_rows, pub_rows = [], [], []

    for name, city, followers, niches in purina_infs:
        tier = _tier(followers)
        inf_id = str(uuid.uuid4())
        handle = f"@{name.lower().replace(' ','')}"

        inf_rows.append({
            "id": inf_id, "full_name": name,
            "email": f"{name.lower().replace(' ','')}@gmail.com",
            "country": "VE", "city": city, "primary_tier": tier,
            "primary_handle": handle,
            "bio": f"Creador {tier.lower()} de {','.join(niches)}",
            "content_niches": niches, "languages": ["es"],
            "status": "active", "tags": [city.lower(), tier.lower()],
            "metadata": {"source": "seed_demo"},
            "source": "manual",
        })

        for j in range(3):
            dias = random.randint(0, 20)
            horas = random.randint(8, 22)
            fecha = (datetime(2026, 7, 10) + timedelta(days=dias, hours=horas)).isoformat()
            formato = random.choice(["reel", "post", "story", "video"])
            vistas = random.randint(800, 30000) if formato in ("reel", "video") else random.randint(200, 6000)
            alcance = int(vistas * random.uniform(1.2, 2.5))
            likes = int(alcance * random.uniform(0.03, 0.10))
            comentarios = int(likes * random.uniform(0.02, 0.06))
            pub_rows.append({
                "id": str(uuid.uuid4()),
                "campaign_id": CAMPID, "influencer_id": inf_id,
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
            })

        ci_rows.append({
            "id": str(uuid.uuid4()),
            "campaign_id": CAMPID, "influencer_id": inf_id,
            "role": "main", "tier": tier,
            "agreed_fee": tier_fee.get(tier, 200),
            "currency": "USD",
            "deliverables": [{"type": "reel", "qty": random.randint(1, 3)}],
            "status": random.choice(["CONFIRMADO", "CONTRATADO", "CONTENIDO_ENTREGADO"]),
            "contracted_at": (datetime.utcnow() - timedelta(days=random.randint(2, 10))).isoformat(),
        })

    n_infs = await _upsert_batch("influencers", inf_rows, on_conflict_col="id")
    n_cis  = await _upsert_batch("campaign_influencers", ci_rows)
    n_pubs = await _upsert_batch("publicaciones", pub_rows)
    return {"influencers": n_infs, "campaign_influencers": n_cis, "publicaciones": n_pubs}


# ================================================================
# 2. SEED SCOUTING VE — 15 perfiles de Ignacio
# ================================================================
async def _seed_scouting_ve() -> dict:
    tier_fee = {"NANO": 150, "MICRO": 400, "MID": 1200}
    influencers = [
        ("gabrielmendezvzla",    "Gabriel Méndez",        233000,"Caracas",   ["mascotas","perros"],              [],            False),
        ("laikalaschnauzer",     "Lakai Lasch",           215000,"Caracas",   ["mascotas","perros"],              [],            False),
        ("manufung",             "Manu Fung",              69600, "N/D",      ["lifestyle","travel"],             ["ubicacion_no_compartida"], True),
        ("maigualidav",          "Mai Guzman",             33000, "Venezuela",["activismo","rescate"],           ["activismo_rescate"],     False),
        ("milageorgina_",        "Mila Georgina",          29700, "Venezuela",["mascotas","perros"],              [],            False),
        ("mayerlingproteccionista","Mayerling",             28300, "Venezuela",["activismo","rescate"],           ["activismo_rescate"],     False),
        ("parcerito_chihuahua",  "Parcerito Chihuahua",    24600, "Venezuela",["mascotas","perros"],              [],            False),
        ("soybugui_",            "Soy Bugui",               21800, "Venezuela",["mascotas","perros"],              [],            False),
        ("oriannaperezz",        "Orianna Perez",           20000, "Venezuela",["travel","foodie","cafe"],        [],            True),
        ("pelirojasuik_",        "Peliroja Suik",          18700, "Venezuela",["lifestyle"],                  ["encuadre_sugerente"],    True),
        ("franye.riv",           "Franye RIV",              10100, "Venezuela",["mascotas","perros"],              [],            False),
        ("bimboykoda",           "BimBoy Koda",              8000, "Venezuela",["mascotas","perros"],              [],            False),
        ("thedoberman.kronos",   "The Doberman Kronos",      5860, "Venezuela",["mascotas","perros"],              [],            False),
        ("barbyag",              "Barby AG",                 5770, "Venezuela",["lifestyle","deporte"],           [],            True),
        ("aldeidesanchez",       "Aldei Sanchez",            3320, "Venezuela",["moda","upcycling"],              [],            True),
    ]

    rows = []
    for handle_clean, name, followers, city, niches, alerts, is_direct in influencers:
        tier = _tier(followers)
        rows.append({
            "id": str(uuid.uuid4()), "full_name": name,
            "email": f"{handle_clean}@gmail.com",
            "country": "VE" if city != "N/D" else "ND",
            "city": city, "primary_tier": tier,
            "primary_handle": f"@{handle_clean}",
            "bio": f"Creador {tier.lower()} de {','.join(niches)}",
            "content_niches": niches, "languages": ["es"],
            "status": "active",
            "tags": [city.lower(), tier.lower()] if city != "N/D" else [tier.lower()],
            "metadata": {
                "source": "solicitud_directa_ignacio" if is_direct else "scouting_ig_hashtag",
                "alerts": alerts,
                "verified_ve": city != "N/D",
                "tier_fee_usd": tier_fee.get(tier, 200),
                "scouting_date": "2026-07-17",
            },
            "source": "manual",
        })

    n = await _upsert_batch("influencers", rows, on_conflict_col="id")
    return {"influencers": n}


# ================================================================
# 3. SEED MATRIZ DOLCE GUSTO — 14 perfiles Nestlé
# ================================================================
async def _seed_matriz_dg() -> dict:
    tier_fee = {"NANO": 150, "MICRO": 400, "MID": 1200, "MACRO": 3000}
    influencers = [
        ("armandopoyo",           "Armando Poyo",         423000,["lifestyle","vlogs"],               False,"CUADRO/PAN/MALTIN-POLAR/CLUB-SOCIAL","Alcance"),
        ("sognis",                "Sofia Saavedra",        366000,["lifestyle","mamá","vlogs"],          False,"HYUNDAI/GAMA/BUCHANAS/PEPSI/HUGGIES","Alcance"),
        ("isaiaslandaeta",        "Isaias Landaeta",      331000,["naturaleza","vlogs","travel"],      False,"7UP/CUADRO/SANTA-TERESA/PLUMROSE","Alcance"),
        ("dieguisimo",            "Diego Vallenilla",      324000,["fotografia","turismo","historia"],   False,"MINALBA/PLUMROSE/FARMATODO/OLDPAR","Alcance"),
        ("alegmassiani",          "Alejandra Guzman",      163000,["lifestyle","vlogs"],               False,"POLAR-LIGHT/KFC/TECNOMOBILE/OISKOS/FLIPS","Alcance"),
        ("irinabozzone",         "Irina Bozzone",        116000,["lifestyle","vlogs","moda"],         False,"CUBITT/PAWER/H&M/SATA-TERESA/ALEO/HEINZ","Alcance"),
        ("anaiotero",             "Ana Otero",             82000, ["lifestyle","mamá"],                 False,"RESTAURANTES","Alcance"),
        ("patrilucia",            "Patricia Carreño",      32800, ["lifestyle","mamá"],                 True, "NATISIMA/7UP/KRAFT/MINALBA/MIGURT","Alcance"),
        ("cocinandoconlulu",     "Lulu Dow",              6623,  ["cocina"],                            True, "LA-GANGA/PAVLOVA-CARACAS-RESTAURANTES","Alcance"),
        ("gastro.no.mia",        "Gastro No Mia",        312000,["cocina","restaurantes"],            True, "PLUMROSE/RESTAURANTES/SANTA TERESA/BANCAMIGA/MYKONOS","Alcance"),
        ("isabermudezfebres",     "Isabel Bermudez",      235000,["finanzas"],                        True, "NO","Alcance"),
        ("inacocina",             "Ina Cocina",           165000,["cocina"],                           True, "MASIA/SAN SIMON/SAVOY-NESTLE/","Alcance"),
        ("maribelpetrola",        "Maribel Petrola",       99300, ["lifestyle","mamá","cocina"],        True, "NUTRI-CLARA/","Alcance"),
        ("mercedesgraureposteria","Mercedes Grau",         99600, ["lifestyle","mamá","cocina"],        True, "CALEDONIA/DOMINOS/GRAU/NESTLE","Alcance"),
    ]

    rows = []
    for handle_clean, name, followers, content_niches, primera_vez, otros_trabajos, driver in influencers:
        tier = _tier(followers)
        trabajos = [t.strip() for t in otros_trabajos.split("/") if t.strip() and t.strip() != "NO"]
        es_bien = "SI" in otros_trabajos and "bien hecho" in otros_trabajos
        es_no   = otros_trabajos.strip() == "NO"

        if es_no:
            aprobacion = {"negocio": "na", "comunicaciones_corporativas": "na", "comunicaciones_comerciales": "na", "legal": "na"}
        elif es_bien:
            aprobacion = {"negocio": "sí_bien_hecho", "comunicaciones_corporativas": "sí_bien_hecho", "comunicaciones_comerciales": "sí_bien_hecho", "legal": "aprobado"}
        else:
            aprobacion = {"negocio": "aprobado", "comunicaciones_corporativas": "aprobado", "comunicaciones_comerciales": "aprobado", "legal": "aprobado"}

        rows.append({
            "id": str(uuid.uuid4()), "full_name": name,
            "email": f"{handle_clean}@gmail.com",
            "country": "VE", "city": "Venezuela", "primary_tier": tier,
            "primary_handle": f"@{handle_clean}",
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
            "source": "manual",
        })

    n = await _upsert_batch("influencers", rows, on_conflict_col="id")
    return {"influencers": n}


# ================================================================
# ENDPOINT
# ================================================================
@router.post("/seed", response_model=SeedStatusResponse)
async def seed_all(x_seed_token: str = Header(None)):
    if x_seed_token != SEED_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid seed token")

    results, errors = {}, []

    try:
        r1 = await _seed_purina()
        results["purina"] = r1
    except Exception as e:
        errors.append(f"Purina: {e}")

    try:
        r2 = await _seed_scouting_ve()
        results["scouting_ve"] = r2
    except Exception as e:
        errors.append(f"Scouting VE: {e}")

    try:
        r3 = await _seed_matriz_dg()
        results["matriz_dg"] = r3
    except Exception as e:
        errors.append(f"Matriz DG: {e}")

    total = sum(r.get("influencers", 0) for r in results.values())
    success = len(errors) == 0
    msg = f"Seeded {total} influencers" + (f"; errors: {'; '.join(errors)}" if errors else "")
    return SeedStatusResponse(success=success, message=msg, details=results)
