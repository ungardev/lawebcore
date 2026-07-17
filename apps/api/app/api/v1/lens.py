"""API v1 router para Influencer Lens — re-exporta discovery con prefijo /lens."""

from fastapi import APIRouter

from app.api.v1 import discovery

router = APIRouter(prefix="/lens", tags=["lens"])
router.include_router(discovery.router, prefix="")
