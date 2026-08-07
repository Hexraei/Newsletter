"""Main FastAPI application."""

import logging
import sys
import uuid
from pathlib import Path
# Add scraper_platform to Python path
scraper_path = str(Path(__file__).parent.parent.parent / "scraper_platform")
if scraper_path not in sys.path:
    sys.path.insert(0, scraper_path)

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router
from app.config import settings
from app.models import get_db, init_db


def configure_logging():
    """Configure structured logging based on environment."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    missing_json_logger = False

    if settings.LOG_FORMAT == "json":
        try:
            from pythonjsonlogger import jsonlogger
        except ModuleNotFoundError:
            missing_json_logger = True
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
        else:
            handler = logging.StreamHandler(sys.stdout)
            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
            )
            handler.setFormatter(formatter)
    else:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    if missing_json_logger:
        logging.getLogger(__name__).warning(
            "python-json-logger is not installed; falling back to plain-text logs"
        )


configure_logging()

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

# Compress responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

STATIC_EXTENSIONS= frozenset([
    '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg',
    '.woff', '.woff2', '.ico',
])
USER_SPECIFIC_SEGMENTS = frozenset(["/save", "/read", "/feedback", "/search"])
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
NO_CACHE_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate"}


def serve_frontend_asset(
    filename: str,
    *,
    media_type: str | None = None,
    not_found_detail: str | None = None,
):
    """Serve a frontend file from repository root/frontend."""
    path = FRONTEND_DIR / filename
    if path.exists():
        return FileResponse(
            str(path),
            media_type=media_type,
            headers=NO_CACHE_HEADERS,
        )
    if not_found_detail:
        return JSONResponse(status_code=404, content={"detail": not_found_detail})
    return RedirectResponse(url="/")


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add a unique correlation ID to each request for tracing."""
    correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = correlation_id
    return response


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    """Add Cache-Control headers based on response path."""
    response = await call_next(request)
    path = request.url.path

    if path.startswith("/api/v1/feed/") and request.method == "GET":
        if not any(seg in path for seg in USER_SPECIFIC_SEGMENTS):
            response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    elif any(path.endswith(ext) for ext in STATIC_EXTENSIONS):
        response.headers["Cache-Control"] = "public, max-age=86400, immutable"
    elif path.startswith("/api/v1/ai/") and request.method == "GET":
        response.headers["Cache-Control"] = "public, max-age=3600"

    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    # CSP for HTML responses - allows inline styles/scripts, Google Fonts, Unsplash images
    if "text/html" in response.headers.get("content-type", ""):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https://images.unsplash.com https://source.unsplash.com https://*.openverse.org https://*.wikimedia.org https://*.wp.com blob:; "
            "connect-src 'self' https://text.pollinations.ai https://api.unsplash.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    return response


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint — validates DB connectivity."""
    try:
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


# Root endpoint
@app.get("/", tags=["Root"])
@app.get("/index.html", tags=["Root"], include_in_schema=False)
async def root():
    """Serve frontend index.html directly (no-cache) or show API info."""
    if (FRONTEND_DIR / "index.html").exists():
        return serve_frontend_asset("index.html")
    return {
        "app": "NEWS DAY API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/sw.js", tags=["Root"], include_in_schema=False)
async def service_worker():
    """Serve service worker from root scope with no-cache headers."""
    return serve_frontend_asset(
        "sw.js",
        media_type="application/javascript",
        not_found_detail="Service worker not found",
    )


@app.get("/auth_session.js", tags=["Root"], include_in_schema=False)
async def auth_session_script():
    """Serve shared auth helper from root path used by frontend pages."""
    return serve_frontend_asset(
        "auth_session.js",
        media_type="application/javascript",
        not_found_detail="auth_session.js not found",
    )


@app.get("/department.html", tags=["Root"])
async def department_page():
    return serve_frontend_asset("department.html")


@app.get("/stories.html", tags=["Root"])
async def stories_page():
    return serve_frontend_asset("stories.html")


@app.get("/research.html", tags=["Root"])
async def research_page():
    return serve_frontend_asset("research.html")


@app.get("/auth.html", tags=["Root"])
async def auth_page():
    return serve_frontend_asset("auth.html")


@app.get("/skills.html", tags=["Root"])
async def skills_page():
    return serve_frontend_asset("skills.html")


@app.get("/insights.html", tags=["Root"])
async def insights_page():
    return serve_frontend_asset("insights.html")


@app.get("/reader.html", tags=["Root"])
async def reader_page():
    return serve_frontend_asset("reader.html")


@app.get("/privacy", tags=["Root"])
@app.get("/privacy.html", tags=["Root"], include_in_schema=False)
async def privacy_page():
    return serve_frontend_asset("privacy.html")


@app.get("/terms", tags=["Root"])
@app.get("/terms.html", tags=["Root"], include_in_schema=False)
async def terms_page():
    return serve_frontend_asset("terms.html")


@app.get("/robots.txt", tags=["Root"])
async def robots_txt():
    return FileResponse(str(frontend_path / "robots.txt"), media_type="text/plain")


@app.get("/sitemap.xml", tags=["Root"])
async def sitemap_xml():
    return FileResponse(str(frontend_path / "sitemap.xml"), media_type="application/xml")


# Include API router
app.include_router(router)

# Mount static files (frontend)
frontend_path = FRONTEND_DIR
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
