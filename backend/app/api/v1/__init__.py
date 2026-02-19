"""API v1 router."""

from fastapi import APIRouter

from app.api.v1 import ai, auth, departments, feed, pipeline, scrapers

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(departments.router, prefix="/departments", tags=["Departments"])
router.include_router(ai.router, prefix="/ai", tags=["AI Services"])
router.include_router(scrapers.router, prefix="/scrapers", tags=["Scraper Management"])
router.include_router(feed.router, prefix="/feed", tags=["Content Feed"])
router.include_router(pipeline.router, prefix="/pipeline", tags=["Content Pipeline"])
