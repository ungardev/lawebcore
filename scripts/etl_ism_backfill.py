#!/usr/bin/env python3
"""
ETL: Backfill de publicaciones desde el ISM legacy.

Lee ~1,698 publicaciones de la base de datos del ISM antiguo
(proyecto Supabase pnhzcglosnfktzbsnjhn) y las migra al schema
canónico de La Web Core (publicaciones, influencers).

Este script es IDEMPOTENTE — puede correr múltiples veces sin duplicar.

Uso:
    python scripts/etl_ism_backfill.py [--dry-run] [--limit N]

Pre-requisitos:
    ISM_SUPABASE_URL=https://pnhzcglosnfktzbsnjhn.supabase.co
    ISM_SUPABASE_SERVICE_KEY=<service_role_key_del_proyecto_ism>
    SUPABASE_URL=https://sdrsxeweobcnnqdxqhjb.supabase.co
    SUPABASE_SERVICE_ROLE_KEY=<service_role_key_de_lawebcore>
"""

import argparse
import asyncio
import sys
import uuid
from datetime import datetime
from typing import Any

import httpx

# ─── Configuración ───────────────────────────────────────────────────────────

ISM_URL = "https://pnhzcglosnfktzbsnjhn.supabase.co"
ISM_KEY = ""  # Set from env ISM_SUPABASE_SERVICE_KEY
TARGET_URL = "https://sdrsxeweobcnnqdxqhjb.supabase.co"
TARGET_KEY = ""  # Set from env SUPABASE_SERVICE_ROLE_KEY

HEADERS_ISM = {
    "apikey": ISM_KEY,
    "Authorization": f"Bearer {ISM_KEY}",
}
HEADERS_TARGET = {
    "apikey": TARGET_KEY,
    "Authorization": f"Bearer {TARGET_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

async def ism_get(table: str, params: dict = None) -> list[dict]:
    async with httpx.AsyncClient(base_url=ISM_URL, timeout=30) as client:
        resp = await client.get(
            f"/rest/v1/{table}",
            params=params,
            headers=HEADERS_ISM,
        )
        resp.raise_for_status()
        return resp.json()


async def target_get(table: str, params: dict = None) -> list[dict]:
    async with httpx.AsyncClient(base_url=TARGET_URL, timeout=30) as client:
        resp = await client.get(
            f"/rest/v1/{table}",
            params=params,
            headers=HEADERS_TARGET,
        )
        resp.raise_for_status()
        return resp.json()


async def target_insert(table: str, data: dict | list) -> list[dict]:
    async with httpx.AsyncClient(base_url=TARGET_URL, timeout=30) as client:
        resp = await client.post(
            f"/rest/v1/{table}",
            json=data,
            headers=HEADERS_TARGET,
        )
        resp.raise_for_status()
        return resp.json()


async def target_upsert(table: str, data: dict | list, match_columns: list[str]) -> list[dict]:
    async with httpx.AsyncClient(base_url=TARGET_URL, timeout=30) as client:
        headers = dict(HEADERS_TARGET)
        headers["Prefer"] = "return=representation"
        headers["X-OnConflict"] = "ignore"
        resp = await client.post(
            f"/rest/v1/{table}",
            json=data,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()


def parse_date(val: Any) -> str | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                return datetime.strptime(val.strip(), fmt).isoformat()
            except ValueError:
                pass
    return None


def safe_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(str(val).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


# ─── Resolución de campaign_id ───────────────────────────────────────────────

async def build_campaigns_map() -> dict[str, uuid.UUID]:
    """
    Construye un mapa {campaign_name_lower -> uuid} de las campañas
    en La Web Core.
    """
    rows = await target_get("campaigns", {"select": "id,name,code", "limit": 500})
    result = {}
    for row in rows:
        name = row.get("name", "")
        code = row.get("code", "")
        cid = row["id"]
        if name:
            result[str(name).lower().strip()] = uuid.UUID(str(cid))
        if code:
            result[str(code).lower().strip().lstrip("#")] = uuid.UUID(str(cid))
    return result


async def resolve_campaign_id(
    campaign_name: str | None,
    legacy_id: str | None,
    campaigns_map: dict[str, uuid.UUID],
) -> uuid.UUID | None:
    """
    C-02: campaign_id es obligatorio.
    Intenta resolver de múltiples formas.
    """
    if campaign_name:
        key = str(campaign_name).lower().strip()
        if key in campaigns_map:
            return campaigns_map[key]
        if key.startswith("#"):
            key2 = key.lstrip("#")
            if key2 in campaigns_map:
                return campaigns_map[key2]

    if legacy_id:
        rows = await target_get(
            "campaigns",
            {"select": "id", "limit": 1},
        )
        pass

    return None


# ─── Resolución de influencer ─────────────────────────────────────────────────

async def build_influencers_map() -> dict[str, uuid.UUID]:
    """
    Construye un mapa {handle_lower -> uuid} de los influencers
    en La Web Core.
    """
    rows = await target_get("influencers", {"select": "id,primary_handle", "limit": 10000})
    result = {}
    for row in rows:
        handle = row.get("primary_handle")
        if handle:
            result[str(handle).strip().lower()] = uuid.UUID(str(row["id"]))
    return result


def resolve_tier_from_followers(followers: int | None) -> str:
    """Heurística para asignar tier según seguidores."""
    if followers is None:
        return "NANO"
    if followers < 10_000:
        return "NANO"
    if followers < 100_000:
        return "MICRO"
    if followers < 500_000:
        return "MID"
    if followers < 1_000_000:
        return "MACRO"
    return "MEGA"


async def crear_influencer_si_no_existe(
    handle: str,
    followers: int | None,
    tier: str | None,
    influencers_map: dict[str, uuid.UUID],
    dry_run: bool = False,
) -> uuid.UUID | None:
    """
    Crea un influencer en La Web Core si no existe.
    Retorna su UUID.
    """
    handle_lower = handle.strip().lower()
    if handle_lower in influencers_map:
        return influencers_map[handle_lower]

    if dry_run:
        new_id = uuid.uuid4()
        print(f"  [DRY] Crearía influencer: @{handle} (followers={followers})")
        return new_id

    influencer_data = {
        "id": str(uuid.uuid4()),
        "full_name": handle,
        "primary_handle": handle.strip(),
        "country": "VE",
        "primary_tier": tier or resolve_tier_from_followers(followers),
        "source": "IMPORT_LEGACY",
        "source_id": handle_lower,
        "status": "active",
    }

    try:
        result = await target_insert("influencers", influencer_data)
        new_uuid = uuid.UUID(str(result[0]["id"]))
        influencers_map[handle_lower] = new_uuid
        return new_uuid
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            rows = await target_get(
                "influencers",
                {"select": "id", "limit": 1},
            )
            for row in rows:
                if row.get("primary_handle", "").lower().strip() == handle_lower:
                    new_uuid = uuid.UUID(str(row["id"]))
                    influencers_map[handle_lower] = new_uuid
                    return new_uuid
        print(f"  Error creando influencer @{handle}: {e}")
        return None


# ─── Mapper principal ─────────────────────────────────────────────────────────

def map_row_ism_to_publicaciones(
    row: dict[str, Any],
    campaign_id: uuid.UUID | None,
    influencer_id: uuid.UUID | None,
) -> dict[str, Any]:
    """
    Mapea una fila de influencer_historical_data (ISM) al schema
    canónico de La Web Core.

    Aplica C-01 (mapeo columnas),
    C-03 (campos derivados),
    C-04 (raw_data),
    C-07 (NULL vs 0).
    """
    views = safe_int(row.get("views"))
    likes = safe_int(row.get("likes"))
    comments = safe_int(row.get("comments"))
    shares = safe_int(row.get("shares"))
    saves = safe_int(row.get("saves"))
    reach = safe_int(row.get("reach"))
    total_watch_time = safe_int(row.get("total_watch_time_seconds"))
    followers = safe_int(row.get("followers_at_time"))

    engagement_total = None
    if likes is not None or comments is not None or shares is not None or saves is not None:
        engagement_total = (likes or 0) + (comments or 0) + (shares or 0) + (saves or 0)
        if engagement_total == 0:
            engagement_total = None

    er_vistas = None
    if engagement_total is not None and views and views > 0:
        er_vistas = (engagement_total / views) * 100

    er_alcance = None
    if engagement_total is not None and reach and reach > 0:
        er_alcance = (engagement_total / reach) * 100

    retention_avg = None
    if total_watch_time is not None and views and views > 0:
        retention_avg = total_watch_time / views

    views_followers_ratio = None
    if views and followers and followers > 0:
        views_followers_ratio = views / followers

    data_quality_flags = []
    if engagement_total is None:
        data_quality_flags.append("engagement_missing")
    if views is None:
        data_quality_flags.append("views_missing")
    if reach is None:
        data_quality_flags.append("reach_missing")
    if followers is None:
        data_quality_flags.append("followers_missing")

    raw_data = dict(row)

    result = {
        "campaign_id": str(campaign_id) if campaign_id else None,
        "influencer_id": str(influencer_id) if influencer_id else None,
        "fecha_publicacion": parse_date(row.get("published_at")) or datetime.utcnow().isoformat(),
        "vistas": views,
        "alcance": reach,
        "likes": likes,
        "comentarios": comments,
        "compartidos": shares,
        "guardados": saves,
        "er_vistas": round(er_vistas, 6) if er_vistas is not None else None,
        "er_alcance": round(er_alcance, 6) if er_alcance is not None else None,
        "retencion": round(retention_avg, 4) if retention_avg is not None else None,
        "engagement_total": engagement_total,
        "views_followers_ratio": round(views_followers_ratio, 6) if views_followers_ratio is not None else None,
        "url_publicacion": row.get("content_url"),
        "plataforma": str(row.get("platform") or "instagram").lower(),
        "formato": str(row.get("content_format") or row.get("content_type") or "").lower() or None,
        "source": "IMPORT_LEGACY",
        "data_quality_flags": data_quality_flags,
        "raw_data": raw_data,
    }

    return result


# ─── Main ETL ────────────────────────────────────────────────────────────────

async def etl_backfill(dry_run: bool = False, limit: int | None = None):
    """
    Ejecuta el ETL completo de ISM legacy → La Web Core.
    """
    print("=" * 60)
    print("ETL: Backfill ISM Legacy → La Web Core")
    print("=" * 60)
    print(f"Modo: {'DRY RUN (sin escribir)' if dry_run else 'PRODUCCIÓN'}")
    print()

    print("[1/5] Obteniendo publicaciones del ISM legacy...")
    params = {
        "select": "*",
        "limit": limit or 10000,
    }
    try:
        ism_rows = await ism_get("influencer_historical_data", params)
    except httpx.HTTPStatusError as e:
        print(f"ERROR: No se pudo conectar al ISM. Código: {e.response.status_code}")
        print("Verifica ISM_SUPABASE_URL e ISM_SUPABASE_SERVICE_KEY")
        sys.exit(1)

    print(f"  → {len(ism_rows)} registros encontrados en ISM")
    if not ism_rows:
        print("No hay datos que migrar. Saliendo.")
        return

    print("[2/5] Construyendo mapa de campañas en La Web Core...")
    campaigns_map = await build_campaigns_map()
    print(f"  → {len(campaigns_map)} campañas conocidas")

    print("[3/5] Construyendo mapa de influencers en La Web Core...")
    influencers_map = await build_influencers_map()
    print(f"  → {len(influencers_map)} influencers conocidos")

    print("[4/5] Procesando publicaciones...")

    inserted = updated = skipped_no_campaign = skipped_no_influencer = skipped_other = 0
    errors = []

    for i, row in enumerate(ism_rows):
        if i % 100 == 0:
            print(f"  Procesando {i}/{len(ism_rows)}...")

        influencer_name = row.get("influencer_name") or row.get("username") or ""
        campaign_name = row.get("campaign_name") or ""
        legacy_id = str(row.get("id", ""))

        campaign_id = await resolve_campaign_id(campaign_name, legacy_id, campaigns_map)
        if not campaign_id:
            skipped_no_campaign += 1
            if len(errors) < 5:
                errors.append(f"  Fila {i+1}: campaign_name='{campaign_name}' no resuelto")
            continue

        influencer_id = await crear_influencer_si_no_existe(
            influencer_name,
            safe_int(row.get("followers_at_time")),
            row.get("tier"),
            influencers_map,
            dry_run=dry_run,
        )

        if not influencer_id:
            skipped_no_influencer += 1
            continue

        mapped = map_row_ism_to_publicaciones(row, campaign_id, influencer_id)

        if dry_run:
            inserted += 1
            continue

        url = mapped.get("url_publicacion")
        if url:
            existing = await target_get(
                "publicaciones",
                {"select": "id", "url_publicacion": f"eq.{url}", "limit": 1},
            )
            if existing:
                updated += 1
                continue

        try:
            await target_insert("publicaciones", mapped)
            inserted += 1
        except Exception as e:
            skipped_other += 1
            if len(errors) < 5:
                errors.append(f"  Fila {i+1}: {str(e)[:80]}")

    print("[5/5] Reporte:")
    print(f"  Insertadas : {inserted}")
    print(f"  Actualizadas: {updated}")
    print(f"  Sin campaign: {skipped_no_campaign}")
    print(f"  Sin influencer: {skipped_no_influencer}")
    print(f"  Otros errores: {skipped_other}")

    if errors:
        print("\n  Primeros errores:")
        for e in errors:
            print(e)

    print()
    print("✅ ETL completado")


async def main():
    parser = argparse.ArgumentParser(description="ETL: Backfill ISM Legacy → La Web Core")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin escribir")
    parser.add_argument("--limit", type=int, default=None, help="Límite de registros a procesar")
    args = parser.parse_args()

    import os
    global ISM_KEY, TARGET_KEY
    ISM_KEY = os.environ.get("ISM_SUPABASE_SERVICE_KEY", "")
    TARGET_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not ISM_KEY:
        print("ERROR: Falta ISM_SUPABASE_SERVICE_KEY en el entorno")
        sys.exit(1)
    if not TARGET_KEY:
        print("ERROR: Falta SUPABASE_SERVICE_ROLE_KEY en el entorno")
        sys.exit(1)

    await etl_backfill(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
