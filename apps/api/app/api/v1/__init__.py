"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    clients,
    brands,
    campaigns,
    influencers,
    kpis,
    dashboard,
    ai,
    users,
    projections,
    publicaciones,
    imports,
    scoring,
    sentiment,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(brands.router, prefix="/brands", tags=["brands"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(influencers.router, prefix="/influencers", tags=["influencers"])
api_router.include_router(kpis.router, prefix="/kpis", tags=["kpis"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(projections.router, prefix="/projections", tags=["projections"])
api_router.include_router(publicaciones.router, prefix="/publicaciones", tags=["publicaciones"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(scoring.router, tags=["scoring"])
api_router.include_router(sentiment.router, tags=["sentiment"])