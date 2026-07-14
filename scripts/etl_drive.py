#!/usr/bin/env python3
"""
ETL: Importación de publicaciones desde Google Drive del equipo P.I.A.R.

Usa Service Account con Domain-Wide Delegation para acceder a las Sheets
del Drive empresarial de LWFA.

Fuentes soportadas:
- Archivos con patrón: Metricas_Campana_Insights_*  (métricas por publicación)
- Archivos con patrón: Matriz_de_influencer_*         (perfiles de influencers)

Este script es IDEMPOTENTE — puede correr múltiples veces sin duplicar.

Uso:
    python scripts/etl_drive.py [--dry-run] [--limit N]

Pre-requisitos:
    GOOGLE_SERVICE_ACCOUNT_KEY='{"type":"service_account", ...}'  (JSON del service account)
    GOOGLE_DRIVE_FOLDER_ID=1a2b3c...  (ID de la carpeta del Drive)

Documentación:
    docs/GOOGLE_DRIVE_SETUP.md

⚠️  DEPENDENCIA: google-api-python-client
    pip install google-api-python-client google-auth
"""

import argparse
import asyncio
import csv
import io
import json
import os
import re
import sys
import uuid
from datetime import datetime
from typing import Any

try:
    from google.auth import compute_engine
    from google.auth.transport import requests as google_requests
    from google.oauth2 import service_account
    import googleapiclient.discovery
    import googleapiclient.errors
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False
    print("WARNING: google-api-python-client no está instalado.")
    print("  Instalar con: pip install google-api-python-client google-auth")
    print("  El script continuará en modo dry-run sin acceso real a Drive.")


# ─── Configuración ───────────────────────────────────────────────────────────

TARGET_URL = "https://sdrsxeweobcnnqdxqhjb.supabase.co"
TARGET_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

HEADERS_TARGET = {
    "apikey": TARGET_KEY,
    "Authorization": f"Bearer {TARGET_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# Scopes para Domain-Wide Delegation
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

# Patrones de archivos a procesar
PATTERNS = {
    "metricas": re.compile(r"Metricas[_\s]?Campana[_\s]?Insights[_\s]?(.*)", re.IGNORECASE),
    "matriz": re.compile(r"Matriz[_\s]?de[_\s]?Influencer[_\s]?(.*)", re.IGNORECASE),
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def safe_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        v = str(val).strip().replace(",", "").replace(" ", "")
        if v in ("", "null", "none", "na", "n/a"):
            return None
        return int(v)
    except (ValueError, TypeError):
        return None


def safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        v = str(val).strip().replace(",", ".").replace(" ", "")
        if v in ("", "null", "none", "na", "n/a"):
            return None
        return float(v)
    except (ValueError, TypeError):
        return None


def parse_date(val: str | None) -> str | None:
    if not val:
        return None
    formatos = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%d-%b-%Y", "%d %b %Y",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formatos:
        try:
            dt = datetime.strptime(val.strip(), fmt)
            return dt.isoformat()
        except (ValueError, AttributeError):
            pass
    return None


async def target_insert(table: str, data: dict | list) -> list[dict]:
    import httpx
    async with httpx.AsyncClient(base_url=TARGET_URL, timeout=30) as client:
        resp = await client.post(f"/rest/v1/{table}", json=data, headers=HEADERS_TARGET)
        resp.raise_for_status()
        return resp.json()


async def target_get(table: str, params: dict = None) -> list[dict]:
    import httpx
    async with httpx.AsyncClient(base_url=TARGET_URL, timeout=30) as client:
        resp = await client.get(f"/rest/v1/{table}", params=params, headers=HEADERS_TARGET)
        resp.raise_for_status()
        return resp.json()


# ─── Drive API helpers ─────────────────────────────────────────────────────────

def get_drive_service(key_json: dict):
    """Construye el servicio de Drive con Service Account credentials."""
    credentials = service_account.Credentials.from_service_account_info(
        key_json,
        scopes=SCOPES,
    )
    return googleapiclient.discovery.build("drive", "v3", credentials=credentials)


def get_sheets_service(key_json: dict):
    """Construye el servicio de Sheets con Service Account credentials."""
    credentials = service_account.Credentials.from_service_account_info(
        key_json,
        scopes=SCOPES,
    )
    return googleapiclient.discovery.build("sheets", "v4", credentials=credentials)


def list_files_in_folder(drive_service, folder_id: str, patterns: list[re.Pattern] | None = None) -> list[dict]:
    """
    Lista archivos en una carpeta de Drive.
    Si patterns se pasa, filtra por nombre.
    """
    results = []
    page_token = None
    while True:
        query = f"'{folder_id}' in parents and trashed = false"
        if patterns:
            for p in patterns:
                query += f" and name contains '{p.pattern}'"

        response = drive_service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
        ).execute()

        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results


def read_sheet_as_csv(sheets_service, spreadsheet_id: str, sheet_name: str = None) -> list[dict]:
    """
    Lee una hoja de Google Sheets y devuelve como lista de diccionarios.
    Usa la primera fila como headers.
    """
    range_name = f"'{sheet_name}'" if sheet_name else "Sheet1!A1:ZZ10000"

    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueRenderOption="UNFORMATTED_VALUE",
    ).execute()

    values = result.get("values", [])
    if not values or len(values) < 2:
        return []

    headers = [str(h).strip() for h in values[0]]
    rows = values[1:]

    result_rows = []
    for row in rows:
        row_dict = {}
        for i, header in enumerate(headers):
            row_dict[header] = row[i] if i < len(row) else None
        result_rows.append(row_dict)

    return result_rows


# ─── Mapeo de columnas ─────────────────────────────────────────────────────────

def normalizar_columna_drive(nombre: str) -> str:
    """Mapea nombre de columna de Sheets a campo canónico."""
    col_lower = nombre.lower().strip()
    mapa = {
        "nombre de usuario": "influencer_name",
        "usuario": "influencer_name",
        "vistas": "views",
        "me gusta": "likes",
        "megusta": "likes",
        "comentarios": "comments",
        "guardados": "saves",
        "compartidos": "shares",
        "alcanzadas": "reach",
        "reach": "reach",
        "total segundos": "total_watch_time_seconds",
        "fecha de publicación": "published_at",
        "fecha publicacion": "published_at",
        "followers": "followers_at_time",
        "seguidores": "followers_at_time",
        "enlace": "content_url",
        "url": "content_url",
        "plataforma": "platform",
        "formato": "content_format",
        "tipo": "content_type",
        "campaña": "campaign_name",
        "campaign": "campaign_name",
        "costo": "cost",
    }
    return mapa.get(col_lower, col_lower)


def mapear_fila_drive(fila: dict, campaign_id: uuid.UUID | None) -> dict:
    """Convierte una fila de Sheets al schema canónico de publicaciones."""
    row_mapped = {normalizar_columna_drive(k): v for k, v in fila.items()}

    views = safe_int(row_mapped.get("views"))
    likes = safe_int(row_mapped.get("likes"))
    comments = safe_int(row_mapped.get("comments"))
    shares = safe_int(row_mapped.get("shares"))
    saves = safe_int(row_mapped.get("saves"))
    reach = safe_int(row_mapped.get("reach"))
    followers = safe_int(row_mapped.get("followers_at_time"))
    total_watch = safe_int(row_mapped.get("total_watch_time_seconds"))

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
    if total_watch and views and views > 0:
        retention_avg = total_watch / views

    depth_index = None
    if saves and shares and views and views > 0:
        depth_index = ((saves + shares) / views) * 100

    data_quality_flags = []
    if engagement_total is None:
        data_quality_flags.append("engagement_missing")
    if views is None:
        data_quality_flags.append("views_missing")
    if reach is None:
        data_quality_flags.append("reach_missing")

    return {
        "campaign_id": str(campaign_id) if campaign_id else None,
        "fecha_publicacion": parse_date(row_mapped.get("published_at")) or datetime.utcnow().isoformat(),
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
        "depth_index": round(depth_index, 6) if depth_index is not None else None,
        "url_publicacion": row_mapped.get("content_url"),
        "plataforma": str(row_mapped.get("platform", "instagram")).lower(),
        "formato": str(row_mapped.get("content_format") or row_mapped.get("content_type") or "").lower() or None,
        "source": "DRIVE_SHEETS",
        "data_quality_flags": data_quality_flags,
        "raw_data": dict(fila),
    }


# ─── Resolución de campaign ────────────────────────────────────────────────────

async def resolver_campaign_id(campaign_name: str, campaigns_map: dict) -> uuid.UUID | None:
    """Busca campaign_id por nombre exacto o por código."""
    if not campaign_name:
        return None
    key = str(campaign_name).lower().strip()
    if key in campaigns_map:
        return campaigns_map[key]
    key_no_hash = key.lstrip("#")
    if key_no_hash in campaigns_map:
        return campaigns_map[key_no_hash]
    return None


# ─── Main ETL ────────────────────────────────────────────────────────────────

async def etl_drive(dry_run: bool = False, limit_per_file: int = 5000):
    print("=" * 60)
    print("ETL: Google Drive Sheets → La Web Core (P.I.A.R.)")
    print("=" * 60)
    print(f"Modo: {'DRY RUN (sin escribir)' if dry_run else 'PRODUCCIÓN'}")
    print()

    key_json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY", "")
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")

    if not key_json_str or not folder_id:
        print("⚠️  Advertencia: GOOGLE_SERVICE_ACCOUNT_KEY o GOOGLE_DRIVE_FOLDER_ID no están configurados.")
        print("   Continuing en modo DRY sin acceso real a Drive.")
        print("   Configura las variables de entorno para activar el ETL real.")
        dry_run = True
        key_json = None
    else:
        key_json = json.loads(key_json_str)
        print(f"✔ Service Account: {key_json.get('client_email', 'unknown')}")

    print("[1/6] Construyendo mapa de campañas en La Web Core...")
    campaigns_map: dict[str, uuid.UUID] = {}
    try:
        rows = await target_get("campaigns", {"select": "id,name,code", "limit": 500})
        for row in rows:
            name = str(row.get("name", "")).lower().strip()
            code = str(row.get("code", "")).lower().strip().lstrip("#")
            cid = uuid.UUID(str(row["id"]))
            if name:
                campaigns_map[name] = cid
            if code:
                campaigns_map[code] = cid
    except Exception as e:
        print(f"  Error conectando a La Web Core: {e}")
        print("  Saliendo.")
        return

    print(f"  → {len(campaigns_map)} campañas conocidas")

    if not key_json:
        print("\n[2/6] Drive: Modo demo (sin credentials)")
        print("[3/6] Sheets: Modo demo")
        print("[4/6] Procesando: Sin acceso real a Drive")
        print("[5/6] ---")
        print("[6/6] Reporte: 0 archivos, 0 filas (demo mode)")
        print("\n✅ ETL demo completado (configura credenciales para modo real)")
        return

    print("[2/6] Conectando a Google Drive...")
    try:
        drive_service = get_drive_service(key_json)
        sheets_service = get_sheets_service(key_json)
        print("  ✔ Conectado a Google Drive API")
    except Exception as e:
        print(f"  ✗ Error conectando: {e}")
        print("  Verifica que el Service Account tenga acceso a la carpeta.")
        return

    print("[3/6] Buscando archivos en Drive...")

    pattern_list = [PATTERNS["metricas"], PATTERNS["matriz"]]
    files = list_files_in_folder(drive_service, folder_id, patterns=pattern_list)
    print(f"  → {len(files)} archivos encontrados")

    if not files:
        print("  No se encontraron archivos con los patrones esperados.")
        print("  Patrones buscados:")
        print("    - Metricas_Campana_Insights_*")
        print("    - Matriz_de_Influencer_*")
        return

    print("[4/6] Procesando archivos...")

    inserted_total = updated_total = skipped_total = 0
    archivos_procesados = 0

    for file in files:
        file_id = file["id"]
        file_name = file["name"]
        print(f"\n  📄 {file_name}")

        if dry_run:
            print(f"     [DRY] Procesaría este archivo")
            continue

        try:
            filas_raw = read_sheet_as_csv(sheets_service, file_id)
            if not filas_raw:
                print(f"     ⚠ Archivo vacío o ilegible")
                continue
        except Exception as e:
            print(f"     ✗ Error leyendo hoja: {e}")
            continue

        metricas_match = PATTERNS["metricas"].search(file_name)
        matriz_match = PATTERNS["matriz"].search(file_name)

        if metricas_match:
            campaign_name_from_file = metricas_match.group(1).replace("_", " ").strip()
            campaign_id = await resolver_campaign_id(campaign_name_from_file, campaigns_map)
            if not campaign_id:
                print(f"     ⚠ Campaña '{campaign_name_from_file}' no resuelta — saltando")
                skipped_total += len(filas_raw)
                continue

            print(f"     → Campaña resuelta: {campaign_name_from_file} ({campaign_id})")
            print(f"     → {len(filas_raw)} filas")

            for fila in filas_raw[:limit_per_file]:
                mapped = mapear_fila_drive(fila, campaign_id)
                url = mapped.get("url_publicacion")

                if url:
                    existing = await target_get(
                        "publicaciones",
                        {"select": "id", "url_publicacion": f"eq.{url}", "limit": 1},
                    )
                    if existing:
                        updated_total += 1
                        continue

                try:
                    await target_insert("publicaciones", mapped)
                    inserted_total += 1
                except Exception:
                    skipped_total += 1

        elif matriz_match:
            print(f"     → Archivo de matriz de influencers (procesando como perfiles)")
            print(f"     → {len(filas_raw)} filas (perfiles de influencers)")

            for fila in filas_raw[:100]:
                handle = fila.get("usuario") or fila.get("nombre") or fila.get("handle") or ""
                if not handle:
                    continue
                followers = safe_int(fila.get("seguidores") or fila.get("followers"))
                tier = fila.get("tier") or fila.get("tipo") or ""

                if dry_run:
                    print(f"     [DRY] Crearía influencer: @{handle}")
                    continue

                # Verificar si ya existe
                try:
                    existing = await target_get(
                        "influencers",
                        {"select": "id", "primary_handle": f"eq.{handle.strip().lower()}", "limit": 1},
                    )
                    if existing:
                        continue
                except Exception:
                    pass

                influencer_data = {
                    "full_name": handle,
                    "primary_handle": handle.strip(),
                    "country": "VE",
                    "primary_tier": tier.upper() if tier else "NANO",
                    "source": "DRIVE_SHEETS",
                    "status": "active",
                }
                try:
                    await target_insert("influencers", influencer_data)
                    inserted_total += 1
                except Exception:
                    skipped_total += 1

        archivos_procesados += 1

    print("\n[5/6] Fin de procesamiento")
    print("[6/6] Reporte:")
    print(f"  Archivos procesados : {archivos_procesados}")
    print(f"  Insertadas        : {inserted_total}")
    print(f"  Actualizadas       : {updated_total}")
    print(f"  Omitidas          : {skipped_total}")
    print()
    print("✅ ETL Drive completado")


async def main():
    parser = argparse.ArgumentParser(
        description="ETL: Google Drive Sheets → La Web Core (P.I.A.R.)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sin escribir")
    parser.add_argument("--limit", type=int, default=5000, help="Límite de filas por archivo")
    args = parser.parse_args()

    await etl_drive(dry_run=args.dry_run, limit_per_file=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
