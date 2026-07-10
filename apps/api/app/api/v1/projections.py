"""P.I.A.R projection endpoints."""

from fastapi import APIRouter, HTTPException

from app.core.piar_engine import PiarEngine
from app.core.supabase_rest import supabase_rest
from app.core.security import CurrentUserDep
from app.schemas.projections import (
    ProjectionCalculateRequest,
    ProjectionCalculateResponse,
)

router = APIRouter()


@router.post("/calculate", response_model=ProjectionCalculateResponse, summary="Calcular proyección P.I.A.R")
async def calcular_proyeccion(
    payload: ProjectionCalculateRequest,
    user: CurrentUserDep,
) -> ProjectionCalculateResponse:
    """
    Calcula la proyección de KPIs para una marca usando el motor P.I.A.R.

    La metodología usa promedio ponderado por tier + peso temporal.
    Retorna 3 escenarios: conservador ×0.75 / base ×1.0 / optimista ×1.30.

    Si la marca tiene menos de 3 campañas con datos, usa fallback a sector (industry).
    """
    engine = PiarEngine(supabase_rest)

    try:
        resultado = await engine.calcular_proyeccion(
            brand_id=payload.brand_id,
            posts_per_tier=payload.posts_per_tier,
            reference_date=payload.reference_date,
        )
        return ProjectionCalculateResponse.model_validate(resultado)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando proyección: {e}")
