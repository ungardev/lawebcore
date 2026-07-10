"""
P.I.A.R. Importer — Universal data ingestion engine.

Aplica las correcciones C-01 a C-07 del audit técnico del ISM:
- C-01: Mapeo de columnas CSV español/inglés → snake_case Supabase
- C-02: campaign_id obligatorio en cada insert
- C-03: Cálculo de campos derivados post-insert
- C-04: raw_data completo con la fila original
- C-07: NULL vs 0 — nunca defaultear a 0 para valores faltantes

Data sources soportadas:
- CSV/Excel del Google Form (español)
- CSV/Excel de Metricool (inglés)
- JSON del data contract P.I.A.R.
- HypeAuditor payload
- Meta Graph API payload
"""

import csv
import io
import re
import uuid
from datetime import datetime
from typing import Any

import structlog

from app.core.supabase_rest import supabase_rest

logger = structlog.get_logger(__name__)


# ─── C-01: Mapeo de columnas (español Google Form + inglés Metricool) ───────

COLUMN_MAP_ES: dict[str, str] = {
    "nombre de usuario": "influencer_name",
    "usuario": "influencer_name",
    "vistas": "views",
    "me gusta": "likes",
    "me gustas": "likes",
    "megusta": "likes",
    "likes": "likes",
    "comentarios": "comments",
    "coment": "comments",
    "coments": "comments",
    "compartidos": "shares",
    "compartidos": "shares",
    "shares": "shares",
    "guardados": "saves",
    "saves": "saves",
    "reposts": "reposts",
    "alcanzadas": "reach",
    "alcance": "reach",
    "reach": "reach",
    "total segundos": "total_watch_time_seconds",
    "tiempo total": "total_watch_time_seconds",
    "nombre y apellido": "display_name",
    "grupo asignado": "group_label",
    "grupo": "group_label",
    "fecha de publicación": "published_at",
    "fecha publicacion": "published_at",
    "fecha": "published_at",
    "publicacion": "published_at",
    "agrega el enlace de tu publicación": "content_url",
    "enlace": "content_url",
    "url": "content_url",
    "link": "content_url",
    "followers": "followers_at_time",
    "seguidores": "followers_at_time",
    "seguidor": "followers_at_time",
    "platform": "platform",
    "plataforma": "platform",
    "tipo": "content_type",
    "content type": "content_type",
    "formato": "content_format",
    "formato de contenido": "content_format",
    "tipo de contenido": "content_type",
    "costo": "cost",
    "coste": "cost",
    "price": "cost",
    "precio": "cost",
    "campaña actual": "campaign_name",
    "campaña": "campaign_name",
    "campaign name": "campaign_name",
}

COLUMN_MAP_EN: dict[str, str] = {
    "views": "views",
    "likes": "likes",
    "comments": "comments",
    "shares": "shares",
    "saves": "saves",
    "reposts": "reposts",
    "reach": "reach",
    "total_watch_time_seconds": "total_watch_time_seconds",
    "follower_count": "followers_at_time",
    "followers": "followers_at_time",
    "username": "influencer_name",
    "user_name": "influencer_name",
    "display_name": "display_name",
    "published_at": "published_at",
    "post_date": "published_at",
    "content_url": "content_url",
    "url": "content_url",
    "platform": "platform",
    "content_type": "content_type",
    "content_format": "content_format",
    "campaign_name": "campaign_name",
    "campaign": "campaign_name",
    "cost": "cost",
    "roi": "roi",
    "notes": "notes",
    "group_label": "group_label",
    "virality_index": "virality_index",
    "video_length_seconds": "video_length_seconds",
    "hook_effectiveness": "hook_effectiveness",
}


def normalizar_nombre_columna(col: str) -> str:
    """Normaliza un nombre de columna a su equivalente snake_case en Supabase."""
    col_lower = col.lower().strip()
    if col_lower in COLUMN_MAP_ES:
        return COLUMN_MAP_ES[col_lower]
    if col_lower in COLUMN_MAP_EN:
        return COLUMN_MAP_EN[col_lower]
    return col_lower


def parsear_fecha(valor: str | None) -> datetime | None:
    """Intenta parsear una fecha en múltiples formatos comunes."""
    if not valor:
        return None
    formatos = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(valor.strip(), fmt)
        except (ValueError, AttributeError):
            pass
    return None


def safe_int(val: Any) -> int | None:
    """Convierte a int, devuelve None si no es posible (no 0). C-07."""
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
    """Convierte a float, devuelve None si no es posible (no 0.0). C-07."""
    if val is None:
        return None
    try:
        v = str(val).strip().replace(",", ".").replace(" ", "")
        if v in ("", "null", "none", "na", "n/a"):
            return None
        return float(v)
    except (ValueError, TypeError):
        return None


def normalizar_fila(
    row: dict[str, Any],
    source: str = "SHEETS",
    campaign_id_override: str | None = None,
    campaign_name_override: str | None = None,
    influencers_map: dict[str, uuid.UUID] | None = None,
) -> dict[str, Any]:
    """
    Normaliza una fila cruda (de CSV, JSON o API) al schema canónico de Supabase.

    Aplica C-01 (mapeo ES/EN), C-02 (campaign_id), C-03 (derivados),
    C-04 (raw_data), C-07 (NULL vs 0).

    Args:
        row: Fila cruda con keys originales
        source: Fuente del dato (SHEETS, API_IG, MANUAL, HYPEAUDITOR, IMPORT_LEGACY)
        campaign_id_override: campaign_id forzado (para CSV que no tiene la columna)
        campaign_name_override: campaign_name cuando se detecta por contexto
        influencers_map: {handle_lower: uuid} para resolver influencer_id

    Returns:
        Fila normalizada con todos los campos canónicos
    """
    raw_row = dict(row)

    normalized: dict[str, Any] = {}

    for original_key, value in row.items():
        mapped_key = normalizar_nombre_columna(original_key)
        if mapped_key in (
            "views",
            "likes",
            "comments",
            "shares",
            "saves",
            "reposts",
            "reach",
            "followers_at_time",
            "total_watch_time_seconds",
            "cost",
            "roi",
            "video_length_seconds",
            "hook_effectiveness",
            "virality_index",
        ):
            normalized[mapped_key] = safe_int(value)
        elif mapped_key in (
            "er_vistas",
            "er_alcance",
            "er_views",
            "er_reach",
            "er",
            "engagement_rate",
            "retention_avg",
            "views_followers_ratio",
            "views_reach_ratio",
            "save_rate",
            "share_rate",
            "comment_rate",
            "consumption_intensity",
            "depth_index",
        ):
            normalized[mapped_key] = safe_float(value)
        elif mapped_key == "published_at":
            dt = parsear_fecha(value)
            normalized["fecha_publicacion"] = dt
        elif mapped_key == "influencer_name":
            normalized["influencer_handle_raw"] = str(value).strip().lower() if value else None
        elif mapped_key in ("display_name", "group_label", "content_url", "notes"):
            normalized[mapped_key] = str(value).strip() if value else None
        elif mapped_key in ("platform", "content_type", "content_format"):
            normalized[mapped_key] = str(value).strip().lower() if value else None
        elif mapped_key == "campaign_name":
            normalized["campaign_name_imported"] = str(value).strip() if value else None
        else:
            normalized[mapped_key] = value

    if campaign_id_override:
        normalized["campaign_id"] = campaign_id_override
    if campaign_name_override:
        normalized["campaign_name_imported"] = campaign_name_override

    data_quality_flags: list[str] = []

    views = normalized.get("views")
    likes = normalized.get("likes")
    comments = normalized.get("comments")
    shares = normalized.get("shares")
    saves = normalized.get("saves")
    reach = normalized.get("reach")
    followers_at_time = normalized.get("followers_at_time")
    total_watch_time = normalized.get("total_watch_time_seconds")

    if likes is None and comments is None and shares is None and saves is None:
        data_quality_flags.append("engagement_missing")
    if views is None:
        data_quality_flags.append("views_missing")
    if reach is None:
        data_quality_flags.append("reach_missing")
    if followers_at_time is None:
        data_quality_flags.append("followers_missing")
    if total_watch_time is not None and views is not None and views > 0:
        pass
    elif total_watch_time is not None and views is None:
        data_quality_flags.append("retention_missing")

    engagement_total = None
    if likes is not None or comments is not None or shares is not None or saves is not None:
        engagement_total = (likes or 0) + (comments or 0) + (shares or 0) + (saves or 0)
        if engagement_total == 0:
            engagement_total = None

    er_vistas = None
    if engagement_total is not None and views is not None and views > 0:
        er_vistas = (engagement_total / views) * 100

    er_alcance = None
    if engagement_total is not None and reach is not None and reach > 0:
        er_alcance = (engagement_total / reach) * 100

    views_followers_ratio = None
    if views is not None and followers_at_time is not None and followers_at_time > 0:
        views_followers_ratio = views / followers_at_time

    retention_avg = None
    if total_watch_time is not None and views is not None and views > 0:
        retention_avg = total_watch_time / views

    save_rate = None
    if saves is not None and views is not None and views > 0:
        save_rate = (saves / views) * 100

    share_rate = None
    if shares is not None and views is not None and views > 0:
        share_rate = (shares / views) * 100

    depth_index = None
    if saves is not None and shares is not None and views is not None and views > 0:
        depth_index = ((saves + shares) / views) * 100

    influencer_handle = normalized.get("influencer_handle_raw")
    influencer_id_resolved: uuid.UUID | None = None
    if influencer_handle and influencers_map and influencer_handle in influencers_map:
        influencer_id_resolved = influencers_map[influencer_handle]

    result: dict[str, Any] = {
        "vistas": views,
        "alcance": reach,
        "likes": likes,
        "comentarios": comments,
        "compartidos": shares,
        "guardados": saves,
        "er_alcance": round(er_alcance, 6) if er_alcance is not None else None,
        "er_vistas": round(er_vistas, 6) if er_vistas is not None else None,
        "retencion": round(retention_avg, 4) if retention_avg is not None else None,
        "engagement_total": engagement_total,
        "views_followers_ratio": round(views_followers_ratio, 6) if views_followers_ratio is not None else None,
        "save_rate": round(save_rate, 6) if save_rate is not None else None,
        "share_rate": round(share_rate, 6) if share_rate is not None else None,
        "depth_index": round(depth_index, 6) if depth_index is not None else None,
        "url_publicacion": normalized.get("content_url"),
        "plataforma": normalized.get("platform", "instagram"),
        "formato": normalized.get("content_format") or normalized.get("content_type"),
        "source": source,
        "data_quality_flags": data_quality_flags,
        "raw_data": raw_row,
    }

    fecha_pub = normalized.get("fecha_publicacion")
    if fecha_pub:
        result["fecha_publicacion"] = fecha_pub.isoformat() if isinstance(fecha_pub, datetime) else fecha_pub
    else:
        result["fecha_publicacion"] = datetime.utcnow().isoformat()

    if influencer_id_resolved:
        result["influencer_id"] = str(influencer_id_resolved)

    return result


async def resolver_campaign_id(
    campaign_id_input: str | None,
    campaign_name_input: str | None,
) -> str | None:
    """
    C-02: campaign_id es obligatorio — nunca implícito.

    Si se pasa campaign_id directamente, validarlo contra la DB.
    Si se pasa campaign_name, buscar por nombre exacto o por código.
    Retorna None si no se encuentra (el endpoint rejectará con 400).
    """
    if campaign_id_input:
        rows = await supabase_rest.table(
            "campaigns",
            select="id",
            eq_filters={"id": campaign_id_input},
            limit=1,
        )
        if rows:
            return str(rows[0]["id"])
        return None

    if campaign_name_input:
        rows = await supabase_rest.table(
            "campaigns",
            select="id,name,code",
            limit=500,
        )
        name_lower = campaign_name_input.lower().strip()
        for row in rows:
            if (row.get("name") or "").lower().strip() == name_lower:
                return str(row["id"])
            code_lower = (row.get("code") or "").lower().strip().lstrip("#")
            if code_lower == name_lower or code_lower == name_lower.lstrip("#"):
                return str(row["id"])
        return None

    return None


async def obtener_influencers_map() -> dict[str, uuid.UUID]:
    """Construye {handle_lower: uuid} para resolver influencer_id rápidamente."""
    rows = await supabase_rest.table("influencers", select="id,primary_handle", limit=10000)
    result: dict[str, uuid.UUID] = {}
    for row in rows:
        handle = row.get("primary_handle")
        if handle:
            result[str(handle).strip().lower()] = uuid.UUID(str(row["id"]))
    return result


async def insertar_publicacion(
    fila_normalizada: dict[str, Any],
    campaign_id: str,
    user_email: str | None = None,
) -> tuple[str, str | None]:
    """
    Inserta una publicación en Supabase con idempotencia.

    Idempotencia: verifica por url_publicacion o por (campaign_id + influencer_id + fecha_publicacion).
    Si ya existe, actualiza.

    Returns:
        (status: 'inserted' | 'updated' | 'skipped', error_message | None)
    """
    url = fila_normalizada.get("url_publicacion")
    fecha = fila_normalizada.get("fecha_publicacion")

    if url:
        existing = await supabase_rest.table(
            "publicaciones",
            select="id",
            eq_filters={"url_publicacion": url},
            limit=1,
        )
        if existing:
            await supabase_rest.update(
                "publicaciones",
                fila_normalizada,
                eq_filters={"id": str(existing[0]["id"])},
            )
            return "updated", None

    if campaign_id and fecha:
        inf_id = fila_normalizada.get("influencer_id")
        if inf_id:
            existing = await supabase_rest.table(
                "publicaciones",
                select="id",
                eq_filters={"campaign_id": campaign_id},
                limit=1000,
            )
            for row in existing:
                if str(row.get("influencer_id")) == inf_id and row.get("fecha_publicacion") == fecha:
                    await supabase_rest.update(
                        "publicaciones",
                        fila_normalizada,
                        eq_filters={"id": str(row["id"])},
                    )
                    return "updated", None

    fila_normalizada["campaign_id"] = campaign_id
    try:
        await supabase_rest.insert("publicaciones", fila_normalizada)
        return "inserted", None
    except Exception as e:
        logger.error("piar_import_insert_error", error=str(e), row=fila_normalizada)
        return "skipped", str(e)


def parsear_csv(csv_text: str) -> list[dict[str, Any]]:
    """Parsea texto CSV a lista de diccionarios."""
    reader = csv.DictReader(io.StringIO(csv_text))
    return list(reader)


async def importar_csv(
    csv_text: str,
    campaign_id: str,
    source: str = "SHEETS",
    user_email: str | None = None,
) -> dict[str, Any]:
    """
    Importa un CSV completo con mapeo de columnas automático.

    Aplica C-01 (COLUMN_MAP), C-02 (campaign_id), C-03 (derivados),
    C-04 (raw_data), C-07 (NULL vs 0).
    """
    filas = parsear_csv(csv_text)
    if not filas:
        return {"inserted": 0, "updated": 0, "skipped": 0, "errors": []}

    campaign_id_resolved = await resolver_campaign_id(campaign_id, None)
    if not campaign_id_resolved:
        return {
            "inserted": 0,
            "updated": 0,
            "skipped": len(filas),
            "errors": [{"row": i + 1, "reason": f"campaign_id '{campaign_id}' no encontrado en la base de datos"}],
        }

    influencers_map = await obtener_influencers_map()

    inserted = updated = skipped = 0
    errors: list[dict[str, Any]] = []

    for i, fila in enumerate(filas):
        normalizada = normalizar_fila(
            fila,
            source=source,
            campaign_id_override=campaign_id_resolved,
            influencers_map=influencers_map,
        )
        status, error = await insertar_publicacion(normalizada, campaign_id_resolved, user_email)
        if status == "inserted":
            inserted += 1
        elif status == "updated":
            updated += 1
        else:
            skipped += 1
            if error:
                errors.append({"row": i + 1, "reason": error, "data": dict(fila)})

    return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors}


async def importar_json(
    payload: list[dict[str, Any]],
    user_email: str | None = None,
) -> dict[str, Any]:
    """
    Importa un array JSON siguiendo el data contract P.I.A.R.

    Validates campaign_id is present (C-02).
    Saves raw_data (C-04).
    Calculates derived fields (C-03).
    Handles NULL vs 0 (C-07).
    """
    if not isinstance(payload, list):
        raise ValueError("Payload debe ser un array de objetos")

    influencers_map = await obtener_influencers_map()

    inserted = updated = skipped = 0
    errors: list[dict[str, Any]] = []

    for i, item in enumerate(payload):
        campaign_id_raw = item.get("campaign_id")
        if not campaign_id_raw:
            errors.append({
                "row": i + 1,
                "reason": "campaign_id obligatorio según el data contract (C-02)",
                "data": {"username": item.get("username")},
            })
            skipped += 1
            continue

        campaign_id_resolved = await resolver_campaign_id(str(campaign_id_raw), item.get("campaign_name"))
        if not campaign_id_resolved:
            errors.append({
                "row": i + 1,
                "reason": f"campaign_id '{campaign_id_raw}' no encontrado en la base de datos",
                "data": {"username": item.get("username")},
            })
            skipped += 1
            continue

        raw_data = item.get("raw_data") or dict(item)

        row_for_normalize: dict[str, Any] = {
            "influencer_name": item.get("username"),
            "followers_at_time": item.get("followers"),
            "views": item.get("views"),
            "likes": item.get("likes"),
            "comments": item.get("comments"),
            "saves": item.get("saves"),
            "shares": item.get("shares"),
            "reach": item.get("reach"),
            "er_vistas": item.get("er_views"),
            "er_alcance": item.get("er_alcance"),
            "retention_avg": item.get("retention_avg"),
            "virality_index": item.get("virality_index"),
            "published_at": item.get("post_date"),
            "content_url": item.get("post_url"),
            "total_watch_time_seconds": item.get("total_watch_time_seconds"),
            "campaign_name": item.get("campaign_name"),
        }

        flags_from_input = item.get("data_quality_flags") or []
        normalizada = normalizar_fila(
            row_for_normalize,
            source="API_IG",
            campaign_id_override=campaign_id_resolved,
            campaign_name_override=item.get("campaign_name"),
            influencers_map=influencers_map,
        )

        if flags_from_input and normalizada.get("data_quality_flags"):
            normalizada["data_quality_flags"] = list(set(normalizada["data_quality_flags"] + flags_from_input))
        elif flags_from_input:
            normalizada["data_quality_flags"] = flags_from_input

        normalizada["raw_data"] = raw_data

        status, error = await insertar_publicacion(normalizada, campaign_id_resolved, user_email)
        if status == "inserted":
            inserted += 1
        elif status == "updated":
            updated += 1
        else:
            skipped += 1
            if error:
                errors.append({"row": i + 1, "reason": error, "data": {"username": item.get("username")}})

    return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors}


def generar_template_csv() -> str:
    """Genera un CSV de plantilla con headers en español e inglés."""
    headers_es = [
        "nombre de usuario",
        "vistas",
        "me gusta",
        "comentarios",
        "guardados",
        "compartidos",
        "alcanzadas",
        "total segundos",
        "fecha de publicación",
        "agrega el enlace de tu publicación",
        "followers",
        "plataforma",
        "formato",
        "campaña actual",
    ]
    headers_en = [
        "username",
        "views",
        "likes",
        "comments",
        "saves",
        "shares",
        "reach",
        "total_watch_time_seconds",
        "published_at",
        "content_url",
        "followers",
        "platform",
        "content_format",
        "campaign_name",
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers_es)
    writer.writerow(headers_en)
    return output.getvalue()
