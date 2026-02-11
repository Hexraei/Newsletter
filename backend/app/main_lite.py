"""Lightweight FastAPI app without database for testing."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="College Newsletter Platform API (Lite Mode - No DB)",
    version=settings.VERSION,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mode": "lite (no database)",
        "version": settings.VERSION,
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "mode": "lite (no database)",
        "version": settings.VERSION,
        "docs_url": "/docs"
    }


# Note: Auth endpoints won't work without DB
# app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main_lite:app", host="0.0.0.0", port=8000, reload=True)
