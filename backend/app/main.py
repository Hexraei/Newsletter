"""Main FastAPI application."""

import logging
import sys
from pathlib import Path
# Add scraper_platform to Python path
scraper_path = str(Path(__file__).parent.parent.parent / "scraper_platform")
if scraper_path not in sys.path:
    sys.path.insert(0, scraper_path)

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import router
from app.config import settings
from app.models import init_db

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting up...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="College Newsletter Platform API",
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware — always use explicit allowlist, never wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint — validates DB connectivity."""
    from sqlalchemy import text
    from app.models.base import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "version": settings.VERSION, "database": f"error: {e}"}
        )
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "database": db_status,
    }


# Root endpoint - redirect to frontend
@app.get("/", tags=["Root"])
async def root():
    """Redirect to frontend."""
    return RedirectResponse(url="/static/index.html")


# Include API router
app.include_router(router)

# Mount static files (frontend)
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    logger.info(f"Static files mounted from: {frontend_path}")
else:
    logger.warning(f"Frontend path not found: {frontend_path}")


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
