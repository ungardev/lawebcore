"""
Run 5 pre-flight validation for HikerAPI.

Validates:
1. Balance has enough requests for Run 5 (~50 needed)
2. Enrichment returns real profile data for VE handles
3. Geo-filter rejects RD/MX/ES/CO/AR handles (TLD + signals)
4. Tienda filter rejects commercial accounts

Run from Railway shell:
    cd /app/apps/api
    python3 scripts/test_run5_validation.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from discovery.tools.hikerapi_client import HikerAPIClient


NON_VE_SIGNALS = (
    "españa", "spain", "salamanca", "madrid", "barcelona", "valencia es",
    "dominicana", "santo domingo", "santiago rd",
    "méxico", "colombia", "argentina", "chile", "perú",
    "estados unidos", "usa ", "miami", "nyc", "texas",
    "kenwood españa", "embajador kenwood",
)

NON_VE_HANDLE_TLDS = (
    ".rd", ".do", ".mx", ".ar", ".co", ".cl", ".pe",
    ".ec", ".pa", ".uy", ".py", ".bo", ".cr",
    "_rd", "_do", "_mx", "_ar", "_co", "_cl", "_pe",
    "_ec", "_pa", "_uy", "_py", "_bo", "_cr",
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
    api_key = os.getenv("HIKERAPI_API_KEY", "")
    if not api_key:
        print("ERROR: HIKERAPI_API_KEY not set. Set the env var before running.")
        return 1
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

    print("\n[2/4] Enrichment test (5 handles: 2 VE + 3 non-VE for filter validation)...")
    test_handles = [
        "paola_cocina_",       # VE - should PASS geo filter
        "cocinavenezolana",    # VE - should PASS geo filter
        "onlypans.rd",         # RD - should REJECT (TLD check)
        "mamiferosmx",         # MX - should REJECT (TLD + signal)
        "cocinaespanola",      # ES - should REJECT (signal)
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

    print("\n[3/4] Geo-filter test (reject non-VE via signals + handle TLD)...")
    geo_pass = 0
    geo_fail = 0
    for handle, profile in enriched.items():
        bio = (profile.get("biography") or profile.get("bio") or "").lower()
        full_name = (profile.get("fullName") or profile.get("full_name") or "").lower()
        combined = f"{bio} {handle.lower()} {full_name}"
        signal_rejected = any(sig in combined for sig in NON_VE_SIGNALS)
        handle_lower = handle.lower()
        tld_rejected = any(handle_lower.endswith(tld) for tld in NON_VE_HANDLE_TLDS)
        rejected = signal_rejected or tld_rejected
        reason = []
        if tld_rejected:
            reason.append("TLD")
        if signal_rejected:
            reason.append("signal")
        status = "REJECT" if rejected else "PASS"
        print(f"  @{handle}: {status} ({', '.join(reason) if reason else 'OK'}) - bio: {bio[:50]!r}")
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
    if balance >= 50 and geo_fail >= 3 and tienda_fail >= 1 and enriched:
        print("RESULT: VALIDATION PASSED — Ready for Run 5")
        print("  - Sufficient balance")
        print("  - Geo-filter working (rejects RD/MX/ES via TLD + signals)")
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
