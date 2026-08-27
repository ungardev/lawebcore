"""P.I.A.R. Data Contract schemas — PublicacionIngest + validation."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class PublicacionIngest(BaseModel):
    """
    Data Contract P.I.A.R. — esquema de una publicación para ingestión.

    Basado en: 06_informe_tecnico_audit_ism.md §8 + 13_data_contract_hub.md

    Reglas críticas (del audit):
    - campaign_id es OBLIGATORIO (C-02)
    - raw_data es OBLIGATORIO (C-04)
    - data_quality_flags reemplaza valores por defecto (C-07)
    - Números crudos siempre (45200, no "45.2K")
    """

    username: str = Field(..., description="Handle del influencer (sin @)")
    followers: int | None = Field(default=None, description="Seguidores en el momento de la publicación")
    campaign_id: UUID = Field(..., description="ID de campaña en Supabase (OBLIGATORIO — C-02)")
    campaign_name: str | None = Field(default=None, description="Nombre de campaña (para referencia)")
    post_date: str = Field(..., description="Fecha de publicación (DD-MM-AA o ISO)")
    post_url: HttpUrl | None = Field(default=None, description="URL directa de la publicación")
    views: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    engagement_total: int | None = Field(default=None, ge=0, description="Auto-calculado si se omite")
    er_views: float | None = Field(default=None, ge=0, le=100, description="ER sobre vistas % (auto-calculado si se omite)")
    er_alcance: float | None = Field(default=None, ge=0, le=100)
    virality_index: float | None = Field(default=None, ge=0, description="V/F ratio")
    retention_avg: float | None = Field(default=None, ge=0, description="Segundos promedio por vista (NO total acumulado)")
    data_quality_flags: list[str] = Field(
        default_factory=list,
        description="Banderas de calidad: 'retention_missing', 'engagement_missing', 'no_followers', etc."
    )
    raw_data: dict[str, Any] = Field(..., description="Fila original sin transformar (C-04 — OBLIGATORIO)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "usuario1",
                "followers": 12300,
                "campaign_id": "550e8400-e29b-41d4-a716-446655440000",
                "campaign_name": "#PorFinIlimitados",
                "post_date": "11-12-2025",
                "post_url": "https://instagram.com/p/xxxx",
                "views": 5600,
                "likes": 410,
                "comments": 22,
                "saves": 9,
                "shares": 5,
                "engagement_total": 446,
                "er_views": 7.96,
                "virality_index": 0.46,
                "retention_avg": None,
                "data_quality_flags": ["retention_missing"],
                "raw_data": {"...": "fila original tal cual llegó de la fuente"}
            }
        }
    }


class PreFlightReport(BaseModel):
    campaign_id: str
    campaign_name: str
    fecha_corte: str
    fuentes: list[str] = Field(default_factory=list)
    hypeauditor_disponible: bool = False
    hay_capturas_retencion: bool = False
    perfiles_publicaron: int = 0
    observaciones: list[str] = Field(default_factory=list)
    listo_para_reporte: bool = False
