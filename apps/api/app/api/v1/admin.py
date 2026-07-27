"""Admin router — TEMPORARY: seed data for Nestlé Venezuela demo via Supabase REST API."""

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from shared_core import supabase_rest
from shared_core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])
SEED_TOKEN = "nestle-seed-token-2026"


class SeedStatusResponse(BaseModel):
    success: bool
    message: str
    details: dict | None = None


class EnrichRequest(BaseModel):
    influencer_ids: list[str] | None = None
    all_active: bool = False


class EnrichResult(BaseModel):
    influencer_id: str
    handle: str
    success: bool
    followers: int | None = None
    engagement_rate: float | None = None
    error: str | None = None


class EnrichResponse(BaseModel):
    total: int
    enriched: int
    failed: int
    cost_usd: float
    results: list[EnrichResult]


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
            "contracted_at": (datetime.utcnow() - timedelta(days=random.randint(2, 10))),
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


# ================================================================
# 4. ENRICH INFLUENCERS VIA APIFY
# ================================================================
@router.post("/enrich-influencers", response_model=EnrichResponse)
async def enrich_influencers(
    body: EnrichRequest | None = None,
    x_admin_token: str | None = Header(None),
):
    """Enriquece perfiles de influencers con datos reales de Instagram via Apify."""
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    from discovery.tools import apify_client as apify_client_module

    body = body or EnrichRequest()
    filters = ["status=eq.active"]
    if body.influencer_ids:
        id_list = ",".join(f'"{i}"' for i in body.influencer_ids)
        filters.append(f"id=in.({id_list})")

    influencers = await supabase_rest.select(
        table="influencers",
        select="id,full_name,primary_handle",
        filters=filters,
        limit=100,
    )

    if not influencers:
        return EnrichResponse(total=0, enriched=0, failed=0, cost_usd=0.0, results=[])

    handles = [
        {"id": str(inf["id"]), "handle": str(inf.get("primary_handle", "")).lstrip("@")}
        for inf in influencers
        if inf.get("primary_handle")
    ]

    if not handles:
        return EnrichResponse(total=len(influencers), enriched=0, failed=len(influencers), cost_usd=0.0, results=[])

    enriched_map: dict[str, dict] = {}
    results_list: list[EnrichResult] = []
    enriched_count = 0
    failed_count = 0
    apify_cost = 0.0

    import logging
    logger = logging.getLogger(__name__)

    batch_size = 10
    for i in range(0, len(handles), batch_size):
        batch = handles[i:i + batch_size]
        usernames = [h["handle"] for h in batch]

        try:
            profiles = await apify_client_module.search_instagram_profiles_batch(usernames)
            if profiles is None:
                logger.warning(f"Apify returned None for batch {usernames}, skipping")
                for h in batch:
                    results_list.append(EnrichResult(
                        influencer_id=h["id"], handle=h["handle"],
                        success=False, error="Apify returned no data (profile not found or API unavailable)",
                    ))
                    failed_count += 1
                continue
            for profile in profiles:
                username = profile.get("username", "")
                matched = next((h for h in batch if h["handle"].lower() == username.lower()), None)
                if not matched:
                    matched = next((h for h in handles if h["handle"].lower() == username.lower()), None)
                if matched:
                    followers = profile.get("followersCount") or profile.get("followers_count")
                    following = profile.get("followsCount") or profile.get("follows_count")
                    posts_count = profile.get("postsCount") or profile.get("posts_count")
                    avg_likes = profile.get("avgLikes") or profile.get("avg_likes")
                    avg_comments = profile.get("avgComments") or profile.get("avg_comments")
                    er = profile.get("avgLikesPercent") or profile.get("avg_likes_percent")

                    if followers and followers > 0 and er is None:
                        if avg_likes and avg_comments:
                            er = (avg_likes + avg_comments) / followers
                        elif avg_likes:
                            er = avg_likes / followers

                    enriched_map[matched["id"]] = {
                        "followers": followers,
                        "following": following,
                        "posts_count": posts_count,
                        "avg_likes": avg_likes,
                        "avg_comments": avg_comments,
                        "engagement_rate": round(er, 6) if er is not None else None,
                        "audience_credibility": (
                            50 + (20 if profile.get("isVerified") else 0) + (15 if profile.get("isBusinessAccount") else 0)
                        ),
                        "profile_pic_url": profile.get("profilePicUrl") or profile.get("profile_pic_url"),
                        "bio": profile.get("biography") or profile.get("bio", ""),
                        "platform": "instagram",
                    }
                    apify_cost += 0.0002
        except Exception as e:
            for h in batch:
                results_list.append(EnrichResult(
                    influencer_id=h["id"], handle=h["handle"],
                    success=False, error=str(e),
                ))
                failed_count += 1

    for inf in influencers:
        inf_id = str(inf["id"])
        if inf_id in enriched_map:
            updates = enriched_map[inf_id]
            updates["enriched_at"] = datetime.now(timezone.utc)
            try:
                await supabase_rest.update(
                    table="influencers",
                    filters=[f"id=eq.{inf_id}"],
                    values=updates,
                )
                results_list.append(EnrichResult(
                    influencer_id=inf_id,
                    handle=str(inf.get("primary_handle", "")),
                    success=True,
                    followers=updates.get("followers"),
                    engagement_rate=updates.get("engagement_rate"),
                ))
                enriched_count += 1
            except Exception as e:
                results_list.append(EnrichResult(
                    influencer_id=inf_id, handle=str(inf.get("primary_handle", "")),
                    success=False, error=str(e),
                ))
                failed_count += 1
        else:
            if not any(r.influencer_id == inf_id for r in results_list):
                results_list.append(EnrichResult(
                    influencer_id=inf_id, handle=str(inf.get("primary_handle", "")),
                    success=False, error="No se encontraron datos en Apify",
                ))
                failed_count += 1

    try:
        await supabase_rest.insert("api_costs", {
            "provider": "apify",
            "cost_usd": apify_cost,
            "request_count": enriched_count,
            "description": f"enrich_influencers: {enriched_count} profiles",
        })
    except Exception:
        pass

    return EnrichResponse(
        total=len(influencers),
        enriched=enriched_count,
        failed=failed_count,
        cost_usd=round(apify_cost, 6),
        results=results_list,
    )


# ================================================================
# 5. PRELOAD DEMO CONVERSATIONS FOR PITCH
# ================================================================
@router.post("/preload-demo")
async def preload_demo_conversations(x_admin_token: str | None = Header(None)):
    """Pre-carga 3 conversaciones demo para el pitch de La Web Figital Agency."""
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    import logging
    logger = logging.getLogger(__name__)

    user_id = "00000000-0000-0000-0000-000000000000"
    bu_id = "00000000-0000-0000-0000-000000000001"

    try:
        users = await supabase_rest.select("users", select="id", limit=1)
        if users and len(users) > 0:
            user_id = str(users[0]["id"])
            logger.info(f"Using real user_id from DB: {user_id}")
    except Exception as e:
        logger.warning(f"Could not fetch real user_id, using fallback: {e}")

    demo_conversations = [
        {
            "title": "Brief Purina Dog Chow — Amor Perruno",
            "accumulated_brief": "Scouting de influencers para nicho mascotas/perros en Venezuela. El sistema descubre perfiles desde hashtags reales, enriquece con datos de Apify, y rankea por engagement + relevancia geográfica VE.",
            "step": "brief",
            "messages": [
                {
                    "role": "user",
                    "content": "Busca influencers de mascotas en Venezuela para campaña Purina Dog Chow",
                },
                {
                    "role": "assistant",
                    "content": "Perfecto. Estoy ejecutando el discovery en Instagram Venezuela para el nicho mascotas/perros. El sistema va a buscar desde hashtags de nicho VE, enriquecer los perfiles con Apify, y rankear por engagement y relevancia geográfica.\n\nEl proceso toma 30 segundos a 2 minutos. Te muestro los candidatos automáticamente cuando estén listos.",
                    "reasoning": "Brief de nicho mascotas/perros en VE. El pipeline discovery va a: 1) buscar posts desde hashtags de nicho VE (mascotasvzla, perrosdevzla, adopcion, etc), 2) extraer handles únicos, 3) enriquecer con Apify (followers, latestPosts, ER), 4) rankear por match_score + geo_relevance.",
                    "tool_calls": [
                        {"id": "tc1", "name": "search_influencers", "arguments": json.dumps({"niche": "mascotas", "country": "VE"})}
                    ],
                    "tool_results": [
                        {"tool_call_id": "tc1", "success": True, "output": {"count": 0, "filters_applied": {"country": "VE", "tiers": ["NANO", "MICRO", "MID"]}}}
                    ],
                    "cost_usd": 0.0012,
                    "latency_ms": 1847,
                },
                {
                    "role": "assistant",
                    "content": "El discovery está corriendo. Apenas tenga los candidatos te los muestro con scores, engagement y ranking completo.",
                    "cost_usd": 0.0008,
                    "latency_ms": 2341,
                },
            ],
        },
        {
            "title": "Analisis Campaña Activa — #DogChowVenezuela",
            "accumulated_brief": "Analiza el rendimiento de la campaña Purina Dog Chow en Instagram Venezuela",
            "step": "candidates_review",
            "messages": [
                {
                    "role": "user",
                    "content": "Dame un resumen del rendimiento de la campaña Purina Dog Chow hasta ahora",
                },
                {
                    "role": "assistant",
                    "content": "El brief es claro: campaña de awareness para Purina Dog Chow en el mercado venezolano. El tono emocional de 'Amor Perruno' conecta bien con dueños de perros en VE. Voy a priorizar Nano y Micro influencers para autenticidad.",
                    "reasoning": "El usuario pide analisis de la campaña activa. Tengo que consultar las metricas de la campana #DogChowVenezuela, agregando publicaciones, engagement y sentimiento.",
                    "tool_calls": [
                        {"id": "tc2", "name": "get_campaign_metrics", "arguments": json.dumps({"campaign_id": "f0000000-0000-0000-0000-000000000003"})}
                    ],
                    "tool_results": [
                        {"tool_call_id": "tc2", "success": True, "output": {"publications": 47, "avg_er": 0.054, "sentiment_positive": 82}}
                    ],
                    "cost_usd": 0.0006,
                    "latency_ms": 1203,
                },
            ],
        },
        {
            "title": "Proyeccion Q4 — Nueva Campana",
            "accumulated_brief": "Proyecta escenarios para nueva campaña de cafe en Colombia",
            "step": "brief",
            "messages": [
                {
                    "role": "user",
                    "content": "Cuéntame qué pasaría si lanzamos una campaña de café en Colombia",
                },
                {
                    "role": "assistant",
                    "content": "Interesante. Una campaña de café en Colombia tiene buen potencial. Aquí están los 3 escenarios:\n\nESCENARIO CONSERVADOR: 3 Nano influencers (5-10K) · Alcance estimado: 45K\nESCENARIO MODERADO: 6 Micro influencers (10-50K) + 1 Nano · Alcance: 120K\nESCENARIO OPTIMISTA: 3 Micro + 2 Mid Tier · Alcance: 310K\n\nMi recomendación: el escenario MODERADO. Balance ideal entre alcance y autenticidad.",
                    "reasoning": "Solicitud de proyeccion. El usuario quiere ver 3 escenarios (conservador, moderado, optimista) con diferentes configuraciones de influencers para una campana de cafe en Colombia.",
                    "tool_calls": [
                        {"id": "tc3", "name": "project_scenarios", "arguments": json.dumps({"country": "CO", "niche": "cafe"})}
                    ],
                    "tool_results": [
                        {"tool_call_id": "tc3", "success": True, "output": {"conservador": {"alcance": 45000}, "moderado": {"alcance": 120000}, "optimista": {"alcance": 310000}}}
                    ],
                    "cost_usd": 0.0009,
                    "latency_ms": 3012,
                },
            ],
        },
    ]

    created = 0
    for demo in demo_conversations:
        conv_id = uuid.uuid4()
        messages = demo.pop("messages", [])
        step = demo.pop("step", "brief")

        try:
            conv_record = await supabase_rest.insert(
                table="discovery_conversations",
                values={
                    "id": str(conv_id),
                    "user_id": user_id,
                    "bu_id": bu_id,
                    "current_step": step,
                    "accumulated_brief": demo.get("accumulated_brief", ""),
                    "message_count": len(messages),
                    "status": "active",
                    "started_at": datetime.now(timezone.utc),
                    "last_message_at": datetime.now(timezone.utc),
                },
            )
        except Exception as e:
            logger.exception(f"Failed to insert conversation {demo.get('title')}: {e}")
            continue

        for msg in messages:
            try:
                await supabase_rest.insert(
                    table="discovery_messages",
                    values={
                        "id": str(uuid.uuid4()),
                        "conversation_id": str(conv_id),
                        "role": msg["role"],
                        "content": msg["content"],
                        "reasoning": msg.get("reasoning"),
                        "tool_calls": json.dumps(msg.get("tool_calls")) if msg.get("tool_calls") else None,
                        "tool_results": json.dumps(msg.get("tool_results")) if msg.get("tool_results") else None,
                        "cost_usd": msg.get("cost_usd", 0),
                        "latency_ms": msg.get("latency_ms", 0),
                        "created_at": datetime.now(timezone.utc),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to insert message for conv {conv_id}: {e}")
                continue
        created += 1

    return {"success": True, "message": f"{created} conversaciones demo creadas", "conversations": created}


# ================================================================
# 6. SEED RAG KNOWLEDGE BASE
# ================================================================
RAG_DOCUMENTS = [
    {
        "title": "Caso de Éxito — Campaña Purina Dog Chow VE (Histórico)",
        "document_type": "case_study",
        "content": (
            "La Web Figital Agency ejecutó la campaña 'Amor Perruno' para Purina Dog Chow Venezuela. "
            "La campaña usó influencers Nano y Micro en ciudades principales de Venezuela. "
            "El tono emocional ('tu perro te ama') combinado con creators auténticos (no macro influencers) "
            "generó alto engagement. "
            "El engagement rate de los nano (<10K) tiende a ser 2x el de mid tier. "
            "Recomendación para VE: priorizar Nano + Micro en ciudades principales para campañas de awareness."
        ),
        "metadata": {"brand": "Purina", "industry": "pet_food", "country": "VE", "document_type": "case_study"},
    },
    {
        "title": "Guía de Engagement Rate — Mercado Venezuela",
        "document_type": "market_research",
        "content": (
            "Benchmarks de engagement rate por tier en Venezuela (Instagram): "
            "MACRO (>500K): 1.5-3.5% ER promedio. "
            "MID (100K-500K): 2.5-5% ER promedio. "
            "MICRO (10K-100K): 4-8% ER promedio. "
            "NANO (<10K): 6-12% ER promedio. "
            "El nicho de mascotas en VE tiene ER 1.5-2x más alto que lifestyle general. "
            "Las cuentas de rescué animal tienen ER 2x el promedio del nicho mascotas. "
            "Las marcas que usan tono emocional en VE tienen más engagement que tono aspiracional. "
            "Nota: estos benchmarks se recalculan automáticamente con datos reales de cada campaña."
        ),
        "metadata": {"brand": "general", "industry": "all", "country": "VE", "document_type": "benchmark"},
    },
    {
        "title": "Best Practices — Influencer Marketing Venezuela",
        "document_type": "best_practices",
        "content": (
            "Reglas de oro para campañas de influencers en Venezuela: "
            "1. Autenticidad > reach. Un nano creator con 8K seguidores y 8% ER vale más que un mid con 200K y 2% ER. "
            "2. Tono local. Los venezolanos responden mejor a contenido en español neutro-latino, con referencias culturales locales. "
            "3. Formato story/reel > post static. El algoritmo de IG favorece reels con caption corto. "
            "4. Timing: mejores horas posting VE son 7-9am y 7-10pm VET. "
            "5. Filtro de calidad: excluir cuentas con discrepancy alta entre engagement publicado y real. "
            "6. Brief estructurado: siempre incluir tono, key messages, hashtags obligatorios y prohibidos. "
            "7. El sistema P.I.A.R. de La Web Core rastrea y reporta engagement real de cada campaña."
        ),
        "metadata": {"brand": "general", "industry": "influencer_marketing", "country": "VE", "document_type": "best_practices"},
    },
    {
        "title": "Purina Dog Chow — Perfil de Marca y Audiencias",
        "document_type": "brand_brief",
        "content": (
            "Purina Dog Chow es una marca de alimento premium para perros de Nestlé Venezuela. "
            "Target primario: dueños de perros en Venezuela, 22-45 años, zonas urbanas principales. "
            "Tono de marca: emocional, cercano, familiar. No aspiracional. "
            "Key messages: 'Amor Perruno' (conexión emocional dueño-perro), salud canina, responsabilidad como dueño. "
            "Hashtags oficiales: #DogChowVenezuela #AmorPerruno. "
            "Competidores: Pedigree VE, Whiskas (gatos), Royal Canin (premium). "
            "Campaña: buscar influencers Nano/Micro especializados en mascotas, tono educativo+emocional. "
            "NO usar influencers con contenido conflictivo o controversias públicas."
        ),
        "metadata": {"brand": "Purina", "industry": "pet_food", "country": "VE", "document_type": "brand_brief"},
    },
    {
        "title": "Análisis Competitivo — Nestlé vs Colgate-Palmolive VE",
        "document_type": "competitive_analysis",
        "content": (
            "Nestlé Venezuela vs Colgate-Palmolive VE en influencer marketing: "
            "Nestlé prefiere creators Nano/Micro vs Colgate que usa más mid/macro. "
            "Nestlé tiende a ganar en engagement rate con estrategia 'autenticidad primero' vs 'alcance primero'. "
            "Para Purina Dog Chow: continuar estrategia Nano/Micro, enfatizar comunidad y creators recurrentes."
        ),
        "metadata": {"brand": "Nestlé", "industry": "competitive", "country": "VE", "document_type": "competitive_analysis"},
    },
    {
        "title": "Caso de Éxito — Dolce Gusto VE (Histórico)",
        "document_type": "case_study",
        "content": (
            "La campaña Dolce Gusto VE usó influencers Mid/Macro en Caracas y Valencia. "
            "Drivers más efectivos: 'momentos de café' (mañana, oficina, pausa) y 'recetas con café'. "
            "Lesson learned: incluir cláusulas de exclusividad en contratos para categorías relacionadas."
        ),
        "metadata": {"brand": "Dolce Gusto", "industry": "beverage", "country": "VE", "document_type": "case_study"},
    },
    {
        "title": "Tendencias Influencer Marketing Latam 2026",
        "document_type": "trend_report",
        "content": (
            "Tendencias 2026 para influencer marketing en Latam: "
            "1. AI-first strategy: usar herramientas de IA para scoring, briefing y tracking (como La Web Core). "
            "2. Long-term partnerships > one-off posts: creators que usan productos consistentemente tienen 3x mejor ROAS. "
            "3. Audio-social: penetration de podcasts y audio messaging en VE creció 40% en 2025. "
            "4. 'Quiet luxury': tono aspiracional pero sutil, sin ostentación. "
            "5. Micro-communities: marcas que construyen comunidades de <500 miembros tienen 5x más engagement. "
            "6. Short-form video-first: 80% del budget debe ir a formato reel/short-video. "
            "7. UGC amplification: repurposing contenido de usuarios reales en ads es 4x más barato que influencers puros. "
            "8. Authenticity premium: creators que muestran procesos reales (no solo resultados) tienen 2x más saves."
        ),
        "metadata": {"brand": "general", "industry": "all", "country": "LATAM", "year": 2026, "document_type": "trends"},
    },
]


@router.post("/seed-rag")
async def seed_rag_knowledge(x_admin_token: str | None = Header(None)):
    """Inserta documentos de conocimiento modelo en la base RAG para el demo."""
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    from shared_core import supabase_rest

    def _chunk_text(text: str, max_len: int = 400) -> list[str]:
        words = text.split()
        chunks, current, current_len = [], [], 0
        for word in words:
            if current_len + len(word) + 1 <= max_len:
                current.append(word)
                current_len += len(word) + 1
            else:
                if current:
                    chunks.append(" ".join(current))
                current, current_len = [word], len(word)
        if current:
            chunks.append(" ".join(current))
        return chunks

    results = []
    for doc in RAG_DOCUMENTS:
        doc_id = str(uuid.uuid4())
        try:
            await supabase_rest.insert(table="documents", values={
                "id": doc_id,
                "title": doc["title"],
                "doc_type": doc.get("document_type", "other"),
                "source": "seed",
                "status": "indexed",
                "metadata": doc.get("metadata", {}),
            })
        except Exception as e:
            results.append({"title": doc["title"], "status": "error", "error": f"doc: {e}"})
            continue

        chunks_text = _chunk_text(doc["content"])
        for idx, chunk_text in enumerate(chunks_text):
            try:
                await supabase_rest.insert(table="document_chunks", values={
                    "document_id": doc_id,
                    "content": chunk_text,
                    "metadata": doc.get("metadata", {}),
                    "chunk_index": idx,
                    "embedding": None,
                })
                results.append({"title": doc["title"], "chunk": idx, "status": "ok"})
            except Exception as e:
                results.append({"title": doc["title"], "chunk": idx, "status": "error", "error": str(e)})

    ok_count = sum(1 for r in results if r["status"] == "ok")
    return {
        "success": True,
        "message": f"Seeded {ok_count}/{len(results)} chunks from {len(RAG_DOCUMENTS)} documents",
        "documents": len(RAG_DOCUMENTS),
        "chunks": len(results),
        "ok": ok_count,
        "failed": len(results) - ok_count,
    }
