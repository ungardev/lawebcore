"""
ETL: Convierte "HISTORIAL DE CAMPAÑAS - LA WEB.xlsx" en INSERTs SQL para Supabase.
Idempotente: usa ON CONFLICT DO NOTHING en el seed.sql.

Uso:
  python3 scripts/etl_excel.py [path_to_xlsx]
  -> genera supabase/seed_excel_data.sql

El script es READ-ONLY sobre el Excel. Solo escribe el SQL de salida.
"""

import sys
import os
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, date
from collections import defaultdict
from decimal import Decimal
import re

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NSMAP = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


# ---------------------------- Excel parsing ----------------------------

def col_letters(ref: str) -> str:
    return "".join(ch for ch in ref if ch.isalpha())


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        data = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(data)
    strings = []
    for si in root.findall("main:si", NSMAP):
        text = ""
        for t in si.iter(NS + "t"):
            text += t.text or ""
        strings.append(text)
    return strings


def parse_excel(xlsx_path: str) -> list[dict]:
    """Parsea la primera hoja y devuelve una lista de filas como dicts {col: value}."""
    with zipfile.ZipFile(xlsx_path) as zf:
        strings = load_shared_strings(zf)
        sheet_xml = zf.read("xl/worksheets/sheet1.xml")
        root = ET.fromstring(sheet_xml)
        sheet_data = root.find("main:sheetData", NSMAP)

        rows = []
        for row in sheet_data.findall("main:row", NSMAP):
            cells = {}
            for c in row.findall("main:c", NSMAP):
                ref = c.get("r")
                col = col_letters(ref)
                t = c.get("t")
                v = c.find("main:v", NSMAP)
                is_el = c.find("main:is", NSMAP)
                val = None
                if t == "s" and v is not None:
                    val = strings[int(v.text)]
                elif t == "inlineStr" and is_el is not None:
                    tn = is_el.find("main:t", NSMAP)
                    if tn is not None:
                        val = tn.text
                elif v is not None:
                    val = v.text
                cells[col] = val
            rows.append(cells)
        return rows


# ---------------------------- Data normalization ----------------------------

# Mapeo BBDD -> categoria normalizada
BBDD_MAP = {
    "NANOS":        "NANOS",
    "MICROS":       "MICROS",
    "MACROS":       "MACROS",
    "BASE DE DATOS":"BASE_DATOS",
    "REPORTE":      "REPORTE",
}

# Mapeo INF-TYPE -> influencer_tier (el Excel mezcla varios con comas)
def parse_inf_types(raw: str) -> list[str]:
    if not raw:
        return []
    raw = raw.upper().strip()
    parts = [p.strip() for p in raw.split(",")]
    tiers = set()
    for p in parts:
        if p in ("NANO", "MICRO", "MID", "MACRO", "MEGA", "MIX"):
            tiers.add(p)
        else:
            # fallback
            tiers.add("MIX")
    # si hay multiples, agregar MIX para reflejar combinacion
    if len(tiers) > 1:
        tiers.add("MIX")
    return sorted(tiers)


# Mapeo OBJETIVO -> enum
OBJETIVO_MAP = {
    "AWARENESS":            "AWARENESS",
    "CONSIDERACIÓN":        "CONSIDERACION",
    "CONSIDERACION":        "CONSIDERACION",
    "CONVERSIÓN":           "CONVERSION",
    "CONVERSION":           "CONVERSION",
    "GEST. DE CRISIS":      "GESTION_DE_CRISIS",
    "GESTION DE CRISIS":    "GESTION_DE_CRISIS",
}


# Mapeo STATUS -> enum (canonica)
STATUS_MAP = {
    "BRIEF":            "BRIEF",
    "CONTACTANDO":      "CONTACTANDO",
    "PLAN DE CUENTAS":  "PLAN_DE_CUENTAS",
    "PULL":             "PULL",
    "CAMPAÑA INTERNA":  "CAMPAÑA INTERNA",   # el seed espera CAMPAÑA INTERNA
    "REPORTE":          "REPORTE",
    "TERMINADA":        "TERMINADA",
}


def slugify(text: str) -> str:
    if not text:
        return ""
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    return text.strip("_")


# ---------------------------- SQL generation ----------------------------

def sql_str(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def sql_num(value, default="NULL"):
    if value is None or value == "":
        return default
    try:
        return str(float(value))
    except (ValueError, TypeError):
        return default


def sql_date(value, default="NULL"):
    if value is None or value == "":
        return default
    # Excel almacena fechas como seriales
    try:
        serial = float(value)
        # base 1900-01-01 con bug de Excel
        d = datetime(1899, 12, 30) + __import__("datetime").timedelta(days=int(serial))
        return f"'{d.date().isoformat()}'"
    except (ValueError, TypeError):
        # intentar parsear formatos comunes
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d DE %B", "%B"):
            try:
                d = datetime.strptime(value.strip(), fmt)
                return f"'{d.date().isoformat()}'"
            except ValueError:
                continue
        return default


# ---------------------------- Main ETL ----------------------------

def main(xlsx_path: str, out_path: str):
    print(f"📥 Leyendo Excel: {xlsx_path}")
    rows = parse_excel(xlsx_path)
    print(f"   Filas totales: {len(rows)}")

    # La fila 3 (index 2) tiene los headers reales
    # Las filas 4-37 (index 3-36) son datos
    # Fila 1 y 2 son titulos decorativos

    # Header canonico segun la inspeccion del Excel:
    header_map = {
        "B": "bbdd_category",     # BBDD
        "F": "event_marker",      # EVENTO -11
        "G": "start_date",        # Inicio
        "H": "end_date",          # Cierre
        "I": "budget",            # BUDGET
        "J": "num_influencers",   # # Influencers
        "O": "client_name",       # CLIENTE
        "Q": "brand_name",        # MARCA
        "S": "campaign_name",     # NOMBRE
        "U": "inf_type_raw",      # INF-TYPE
        "V": "objective_raw",     # OBJETIVO
        "X": "brief_title",       # BRIEF
        "Z": "induccion_doc",     # Documento de induccion
        "AB": "contract_ref",     # CONTRATO
        "AD": "hook_doc",         # Hook
        "AG": "formulario",       # FORMULARIO
        "AI": "pull_ref",         # PULL
        "AK": "plan_cuentas_ref", # PLAN DE CUENTAS
        "AM": "campana_interna_ref", # CAMPANA INTERNA
        "AO": "drive_ref",        # DRIVE
        "AP": "reporte_ref",      # REPORTE
        "AR": "status",           # STATUS
        "AT": "videos_count",     # VIDEOS
        "AU": "reach",            # REACH
        "AV": "engagement",       # ENGAGEMENT
        "AW": "engagement_rate",  # ER X
        "AX": "views",            # VIEWS X
        "AY": "retention",        # RETENCION X
        "AZ": "insights_text",    # Insight
        "BF": "winning_format_text", # FORMATO GANADOR
    }

    data_rows = rows[3:37]  # filas 4..37 inclusive
    print(f"   Filas de datos: {len(data_rows)}")

    # 1) Descubrir clientes y marcas unicos
    clients = {}
    brands = {}
    client_order = []
    brand_order = []
    for r in data_rows:
        c = (r.get("O") or "").strip()
        b = (r.get("Q") or "").strip()
        if c and c not in clients:
            clients[c] = len(client_order) + 1
            client_order.append(c)
        if b and (c, b) not in brands:
            brands[(c, b)] = len(brand_order) + 1
            brand_order.append((c, b))

    # 2) Generar SQL
    out = []
    out.append("-- =================================================================")
    out.append("-- LA WEB CORE - Seed data del Excel HISTORIAL DE CAMPAÑAS - LA WEB.xlsx")
    out.append(f"-- Generado automaticamente por scripts/etl_excel.py el {datetime.utcnow().isoformat()}Z")
    out.append("-- =================================================================")
    out.append("")
    out.append("-- CLIENTES")
    client_ids = {}
    for c in client_order:
        cid = f"'20000000-0000-0000-0000-{clients[c]:012d}'"
        code = slugify(c)[:50] or "CLIENT"
        name = c.title()
        out.append(f"INSERT INTO clients (id, code, name) VALUES ({cid}, {sql_str(code)}, {sql_str(name)}) ON CONFLICT (id) DO NOTHING;")
        client_ids[c] = cid
    out.append("")

    out.append("-- MARCAS")
    brand_ids = {}
    for c, b in brand_order:
        bid = f"'30000000-0000-0000-0000-{brands[(c,b)]:012d}'"
        cid = client_ids[c]
        code = slugify(b)[:50] or "BRAND"
        name = b.title()
        out.append(f"INSERT INTO brands (id, client_id, code, name) VALUES ({bid}, {cid}, {sql_str(code)}, {sql_str(name)}) ON CONFLICT (client_id, code) DO NOTHING;")
        brand_ids[(c, b)] = bid
    out.append("")

    out.append("-- CAMPAÑAS")
    out.append("-- Nota: el codigo se genera como CAMP-<idx>-<año>")
    camp_ids = []
    for idx, r in enumerate(data_rows, start=1):
        c = (r.get("O") or "").strip()
        b = (r.get("Q") or "").strip()
        if not c or not b:
            continue
        name = (r.get("S") or "").strip() or f"Campana {idx}"
        status_raw = (r.get("AR") or "").strip().upper()
        status = STATUS_MAP.get(status_raw, "BRIEF")
        obj_raw = (r.get("V") or "").strip().upper()
        obj = OBJETIVO_MAP.get(obj_raw, "AWARENESS")
        tiers = parse_inf_types(r.get("U"))
        start_d = sql_date(r.get("G"))
        end_d = sql_date(r.get("H"))
        budget = sql_num(r.get("I"))
        n_inf = int(float(r["J"])) if r.get("J") else 0

        cid = client_ids[c]
        bid = brand_ids[(c, b)]
        camp_id = f"'40000000-0000-0000-0000-{idx:012d}'"
        code = f"CAMP-2026-{idx:03d}"
        tier_arr = "{" + ",".join(tiers) + "}" if tiers else "{}"

        out.append(
            f"INSERT INTO campaigns (id, code, client_id, brand_id, name, objective, influencer_tiers, "
            f"start_date, end_date, budget_total, num_influencers, status, business_unit_id) VALUES "
            f"({camp_id}, {sql_str(code)}, {cid}, {bid}, {sql_str(name)}, {sql_str(obj)}, "
            f"{tier_arr}::influencer_tier[], {start_d}, {end_d}, {budget}, {n_inf}, "
            f"{sql_str(status)}, '00000000-0000-0000-0000-000000000003'::uuid) "
            f"ON CONFLICT (id) DO NOTHING;"
        )
        camp_ids.append(camp_id)

        # KPI values
        kpi_map = {
            "videos_count": r.get("AT"),
            "reach": r.get("AU"),
            "engagement": r.get("AV"),
            "engagement_rate": r.get("AW"),
            "views": r.get("AX"),
            "retention": r.get("AY"),
        }
        for kpi_code, val in kpi_map.items():
            if val:
                v = sql_num(val)
                out.append(
                    f"INSERT INTO campaign_kpi_values (campaign_id, kpi_definition_id, value, source) "
                    f"SELECT {camp_id}, kd.id, {v}, 'IMPORTADO' "
                    f"FROM kpi_definitions kd WHERE kd.code = {sql_str(kpi_code)} "
                    f"ON CONFLICT DO NOTHING;"
                )

        # Insights (texto)
        ins = (r.get("AZ") or "").strip()
        if ins and not ins.upper().startswith("EJ"):
            out.append(
                f"INSERT INTO insights (campaign_id, insight_type, title, description, generated_by_ai) "
                f"VALUES ({camp_id}, 'qualitative', 'Insight registrado', {sql_str(ins)}, FALSE) ON CONFLICT DO NOTHING;"
            )

        # Winning format
        wf = (r.get("BF") or "").strip()
        if wf and not wf.upper().startswith("EJ"):
            out.append(
                f"INSERT INTO winning_formats (campaign_id, format_name, description) "
                f"VALUES ({camp_id}, {sql_str(wf[:80])}, {sql_str(wf)}) ON CONFLICT DO NOTHING;"
            )

        # Links externos (canva, drive, hypeauditor, etc.)
        link_cols = [
            ("X",  "BRIEF",                 r.get("X")),
            ("Z",  "DOCUMENTO_INDUCCION",   r.get("Z")),
            ("AB", "CONTRATO",              r.get("AB")),
            ("AD", "HOOK",                  r.get("AD")),
            ("AG", "FORMULARIO",            r.get("AG")),
            ("AI", "PULL",                  r.get("AI")),
            ("AK", "PLAN_DE_CUENTAS",       r.get("AK")),
            ("AM", "CAMPANA_INTERNA",       r.get("AM")),
            ("AO", "DRIVE",                 r.get("AO")),
            ("AP", "REPORTE",               r.get("AP")),
        ]
        for col, ltype, val in link_cols:
            v = (val or "").strip()
            if v and not v.upper().startswith("EJ"):
                # si parece URL, link_type = URL; si no, OTRO
                actual_type = "OTRO"
                if v.startswith("http"):
                    if "canva" in v.lower():
                        actual_type = "CANVA"
                    elif "drive.google" in v.lower() or "docs.google" in v.lower():
                        actual_type = "DRIVE"
                    elif "hypeauditor" in v.lower():
                        actual_type = "HYPEAUDITOR"
                    elif "trello" in v.lower():
                        actual_type = "TRELLO"
                    else:
                        actual_type = ltype
                else:
                    actual_type = ltype
                out.append(
                    f"INSERT INTO campaign_links (campaign_id, link_type, title, url) "
                    f"VALUES ({camp_id}, {sql_str(actual_type)}, {sql_str(v[:80])}, {sql_str(v)}) ON CONFLICT DO NOTHING;"
                )

    out.append("")
    out.append(f"-- Total campanas migradas: {len(camp_ids)}")
    out.append(f"-- Total clientes: {len(client_order)}")
    out.append(f"-- Total marcas: {len(brand_order)}")

    sql_content = "\n".join(out)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(sql_content)
    print(f"✅ SQL generado: {out_path} ({len(sql_content)} bytes)")
    print(f"   Clientes: {len(client_order)}, Marcas: {len(brand_order)}, Campañas: {len(camp_ids)}")


if __name__ == "__main__":
    xlsx = sys.argv[1] if len(sys.argv) > 1 else "HISTORIAL DE CAMPAÑAS - LA WEB.xlsx"
    out  = sys.argv[2] if len(sys.argv) > 2 else "supabase/seed_excel_data.sql"
    main(xlsx, out)