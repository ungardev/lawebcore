"""P.I.A.R. import endpoints — CSV, JSON, HypeAuditor ingestion."""

import io

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.piar_importer import (
    generar_template_csv,
    importar_csv,
    importar_json,
)
from app.schemas.imports import (
    ImportError,
    ImportReport,
    JSONImportRequest,
)

router = APIRouter()


@router.post(
    "/csv",
    response_model=ImportReport,
    summary="Importar publicaciones desde CSV",
)
async def import_csv(
    file: UploadFile = File(..., description="Archivo CSV con publicaciones"),
    campaign_id: str = Form(..., description="ID de la campaña en Supabase"),
    source: str = Form(default="SHEETS"),
    user_email: str | None = Form(default=None),
):
    """
    Importa publicaciones desde un archivo CSV.

    Aplica COLUMN_MAP automático (español Google Form ↔ inglés Metricool).
    Valida campaign_id contra la base de datos.
    Calcula campos derivados: engagement_total, er_vistas, er_alcance, retention_avg, etc.
    Idempotente: si la publicación ya existe (por url_publicacion), actualiza.

    Errores por fila en el reporte de respuesta.
    """
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV o Excel (.csv, .xlsx, .xls)")

    contents = await file.read()

    try:
        csv_text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            csv_text = contents.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="No se pudo decodificar el archivo. Usa UTF-8.")  # noqa: B904

    report = await importar_csv(
        csv_text=csv_text,
        campaign_id=campaign_id,
        source=source.upper(),
        user_email=user_email,
    )

    report["total_rows"] = report["inserted"] + report["updated"] + report["skipped"]
    report["errors"] = [ImportError(**e) for e in report["errors"]]

    return ImportReport(**report)


@router.post(
    "/json",
    response_model=ImportReport,
    summary="Importar publicaciones via JSON (Data Contract P.I.A.R.)",
)
async def import_json(
    payload: JSONImportRequest,
    user_email: str | None = Header(default=None, alias="X-User-Email"),
):
    """
    Importa publicaciones via JSON array siguiendo el data contract P.I.A.R.

    Formato esperado: array de objetos con los campos del data contract.
    campaign_id es OBLIGATORIO en cada objeto (C-02 del audit).
    raw_data es OBLIGATORIO (C-04 del audit).
    data_quality_flags reemplaza valores por defecto (C-07 del audit).

    Ver: 13_data_contract_hub.md
    """
    report = await importar_json(
        payload=payload.model_dump(),
        user_email=user_email or payload.user_email,
    )

    report["total_rows"] = report["inserted"] + report["updated"] + report["skipped"]
    report["errors"] = [ImportError(**e) for e in report["errors"]]

    return ImportReport(**report)


@router.get(
    "/template",
    summary="Descargar plantilla CSV para importación",
)
async def get_template():
    """
    Genera un CSV de plantilla con headers en español e inglés.

    El operador puede usar esta plantilla para importar datos,
    preenchiendo las columnas según el formato de su fuente.
    """
    csv_content = generar_template_csv()

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=piar_import_template.csv"
        },
    )
