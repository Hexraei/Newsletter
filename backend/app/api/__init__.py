"""API router aggregator."""

from fastapi import APIRouter

from app.api.v1 import router as v1_router
from app.config import settings

router = APIRouter(prefix=settings.API_V1_PREFIX)
router.include_router(v1_router)
