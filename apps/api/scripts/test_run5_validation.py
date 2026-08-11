"""
Run 5 pre-flight validation for HikerAPI.

Validates:
1. Balance has enough requests for Run 5 (~50 needed)
2. Enrichment returns real profile data for handles from Run 4
3. Geo-filter rejects Spain/RD/USA handles
4. Tienda filter rejects commercial accounts

Run from Railway shell:
    cd /app
    export HIKERAPI_API_KEY=wr6l9jyb469nwtwzpk19j25o9wsjyq6b
    python -m scripts.test_run5_validation
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from discovery.tools.hikerapi_client import HikerAPIClient


NON_VE_SIGNALS = (
    "españa", "spain", "salamanca", "madrid", "barcelona", "valencia es",
    "dominicana", "santo domingo", "santiago rd", "rd 🇩🇴",
    "méxico", "colombia", "argentina", "chile", "perú",
    "estados unidos", "usa ", "miami", "nyc", "texas",
    "kenwood españa", "embajador kenwood",
)

TIENDA_KEYWORDS = (
    "tienda", "shop", "store", "petshop", "pet shop", "pets shop",
    "ventas", "vendemos", "pedidos", "envíos", "delivery", "deliveries",
    "catálogo", "precios", "oferta", "descuento", "promoción",
    "comprar", "compras", "adquirir", "whatsapp", "escríbenos", "contáctanos",
    "horario", "sucursal", "local", "tienda física",
    "pago en dólares", "pago en euros", "transferencia", "zelle", "paypal",
    "marca oficial", "distribuidor", "distribuidora", "agente autorizado",
    "mayor y detal", "menudeo", "por mayor", "al mayor",
    "stock", "inventario", "bodega", "almacén",
    "cápsulas", "capsulas", "granos", "molido", "seleccionamos a mano",
    "selección a mano", "nuestro café", "nuestra marca",
    "cursos online", "curso de repostería", "clases de cocina", "aprende repostería",
    "haz click aquí", "link en bio", "clic abajo enlace",
    "embajador kenwood", "embajador officiel",
    "fabricamos", "elaboramos", "producimos",
    "nuestra tienda", "punto de venta", "pdv",
    "delivery propio", "envío gratis", "envío a domicilio",
    "productos artesanales", "artesanal",
    "panadería profesional", "pastelería profesional",
)


async def main():
    api_key = os.getenv("HIKERAPI_API_KEY", "wr6l9jyb469nwtwzpk19j25o9wsjyq6b")
    client = HikerAPIClient(api_key=api_key)

    print("=" * 60)
    print("RUN 5 PRE-FLIGHT VALIDATION")
    print("=" * 60)

    print("\n[1/4] Checking balance...")
    resp, _ = await client._get_debug("/sys/balance")
    if not resp:
        print("FAIL: Could not fetch balance")
        return 1
    balance = resp.get("requests", 0)
    print(f"  Balance: {balance} requests remaining")
    if balance < 50:
        print(f"  WARNING: Only {balance} requests. Run 5 needs ~50.")
    else:
        print(f"  OK: Sufficient for Run 5")

    print("\n[2/4] Enrichment test (5 handles from Run 4)...")
    test_handles = [
        "paola_cocina_",
        "cocinavenezolana",
        "sarasellos",
        "onlypans.rd",
        "mamaloncheras",
    ]
    enriched = {}
    for handle in test_handles:
        try:
            profile = await client.enrich_profile(handle)
            if profile:
                enriched[handle] = profile
                followers = profile.get("followersCount", 0)
                biz = profile.get("isBusinessAccount", False)
                print(f"  @{handle}: {followers:,} followers, business={biz}")
            else:
                print(f"  @{handle}: NOT FOUND")
            await asyncio.sleep(1.1)
        except Exception as e:
            print(f"  @{handle}: ERROR - {e}")

    if not enriched:
        print("  FAIL: No profiles enriched. Check API key and rate limit.")
        return 1

    print("\n[3/4] Geo-filter test (reject non-VE)...")
    geo_pass = 0
    geo_fail = 0
    for handle, profile in enriched.items():
        bio = (profile.get("biography") or profile.get("bio") or "").lower()
        full_name = (profile.get("fullName") or profile.get("full_name") or "").lower()
        combined = f"{bio} {handle.lower()} {full_name}"
        rejected = any(sig in combined for sig in NON_VE_SIGNALS)
        status = "REJECT" if rejected else "PASS"
        print(f"  @{handle}: {status} (bio snippet: {bio[:60]!r})")
        if rejected:
            geo_fail += 1
        else:
            geo_pass += 1

    print(f"\n  Geo filter: {geo_pass} passed, {geo_fail} rejected")

    print("\n[4/4] Tienda-filter test (reject commercial/B2B)...")
    tienda_pass = 0
    tienda_fail = 0
    for handle, profile in enriched.items():
        bio = (profile.get("biography") or profile.get("bio") or "").lower()
        rejected = any(kw in bio for kw in TIENDA_KEYWORDS)
        status = "REJECT" if rejected else "PASS"
        print(f"  @{handle}: {status}")
        if rejected:
            tienda_fail += 1
        else:
            tienda_pass += 1

    print(f"\n  Tienda filter: {tienda_pass} passed, {tienda_fail} rejected")

    print("\n[Final] Balance check after enrichment...")
    resp, _ = await client._get_debug("/sys/balance")
    if resp:
        final_balance = resp.get("requests", 0)
        used = balance - final_balance
        print(f"  Started: {balance}, Used: {used}, Remaining: {final_balance}")

    await client.close()

    print("\n" + "=" * 60)
    if balance >= 50 and geo_fail >= 2 and tienda_fail >= 1 and enriched:
        print("RESULT: VALIDATION PASSED — Ready for Run 5")
        print("  - Sufficient balance")
        print("  - Geo-filter working (rejects Spain/RD)")
        print("  - Tienda-filter working (rejects commercial)")
        return 0
    elif balance < 50:
        print("RESULT: LOW BALANCE — Need to top up HikerAPI")
        return 2
    else:
        print("RESULT: CHECK OUTPUTS ABOVE")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
