"""Schemas for P.I.A.R. import operations."""

from typing import Any

from pydantic import BaseModel, Field


class ImportError(BaseModel):
    row: int
    reason: str
    data: dict[str, Any] | None = None


class ImportReport(BaseModel):
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[ImportError] = Field(default_factory=list)
    total_rows: int = 0


class CSVImportRequest(BaseModel):
    campaign_id: str = Field(..., description="ID de la campaña en Supabase")
    source: str = Field(default="SHEETS", description="Fuente del dato: SHEETS, API_IG, MANUAL, HYPEAUDITOR")
    user_email: str | None = Field(default=None, description="Email del usuario que importa (para auditoría)")


class JSONImportRequest(BaseModel):
    user_email: str | None = Field(default=None, description="Email del usuario que importa (para auditoría)")
