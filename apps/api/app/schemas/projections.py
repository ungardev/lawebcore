"""Pydantic schemas for P.I.A.R projection endpoints."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProjectionTierInput(BaseModel):
    tier: str = Field(..., description="NANO | MICRO | MID | MACRO | MEGA")
    num_posts: int = Field(..., ge=0, description="Número de posts planeados para este tier")


class ProjectionCalculateRequest(BaseModel):
    brand_id: str
    posts_per_tier: dict[str, int] = Field(
        ...,
        description='Distribución de posts por tier, ej. {"NANO": 10, "MICRO": 4}',
    )
    reference_date: datetime | None = None


class ProjectionScenario(BaseModel):
    vistas_proyectadas: int
    alcance_proyectado: int
    engagement_proyectado: int
    posts_virales_esperados: int


class ProjectionTasaPromedio(BaseModel):
    er_promedio: float | None = None
    retencion_promedio: float | None = None


class ProjectionTierResult(BaseModel):
    tier: str
    num_posts: int
    fuente: str
    num_campanas: int
    tasas: ProjectionTasaPromedio
    escenarios: dict[str, ProjectionScenario]


class ProjectionTotal(BaseModel):
    conservador: dict[str, int]
    base: dict[str, int]
    optimista: dict[str, int]


class ProjectionCalculateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    brand_id: str
    brand_name: str
    client_id: str
    industry: str | None
    reference_date: str
    resultados_por_tier: list[ProjectionTierResult]
    total: ProjectionTotal
