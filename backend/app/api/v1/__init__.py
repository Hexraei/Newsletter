"""API v1 router."""

from fastapi import APIRouter

from app.api.v1 import ai, auth

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(ai.router, prefix="/ai", tags=["AI Services"])
