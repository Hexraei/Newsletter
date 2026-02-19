"""Lightweight FastAPI app without database for testing."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.integrations.ai_provider import AIProvider, check_ai_status
from app.integrations.supabase_lite import SupabaseLiteClient
from app.ranking_engine import (
    candidate_to_feed_item,
    rank_all_sections,
    rank_breaking,
    rank_department,
    rank_student_stories,
    rank_trending,
)


supabase_client = SupabaseLiteClient()


class LiteSummarizeRequest(BaseModel):
    """Request body for lite summarize endpoint."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    category: str = Field(default="computer-science", max_length=100)


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _latest_scraped_file() -> Path | None:
    data_dir = _repo_root() / "scraper_platform" / "data"
    files = sorted(data_dir.glob("scraped_*.json"), reverse=True)
    return files[0] if files else None


def _load_scraped_items() -> list[dict]:
    latest = _latest_scraped_file()
    if not latest or not latest.exists():
        return []

    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
        items = payload.get("items", [])
        return items if isinstance(items, list) else []
    except Exception:
        return []


def _clamp_limit(limit: int, default: int, hard_max: int) -> int:
    parsed = _safe_int(limit)
    return max(1, min(parsed or default, hard_max))


def _empty_items_response() -> dict:
    return {"success": True, "data": {"items": []}}


async def _load_items_for_feed() -> list[dict]:
    supabase_items = await supabase_client.fetch_scraped_items()
    if supabase_items:
        return supabase_items
    return _load_scraped_items()

app = FastAPI(
    title=settings.APP_NAME,
    description="College Newsletter Platform API (Lite Mode - No DB)",
    version=settings.VERSION,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/api/v1/ai/status", tags=["AI Services"])
async def ai_status_lite():
    """AI provider status in lite mode."""

    status_info = await check_ai_status()
    return {"success": True, "data": status_info}


@app.post("/api/v1/ai/summarize", tags=["AI Services"])
async def summarize_content_lite(request: LiteSummarizeRequest):
    """Summarize content using AI in lite mode (no DB)."""

    provider = AIProvider()
    try:
        summary = await provider.summarize(request.title, request.content, request.category)
        return {
            "success": True,
            "data": {
                "summary": summary,
                "provider": provider.get_provider_name(),
                "mode": "lite",
            },
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service unavailable: {exc}",
        )
    finally:
        await provider.close()


@app.get("/api/v1/feed/trending", tags=["Feed"])
async def lite_trending_feed(limit: int = 20):
    """Trending feed from latest scraped JSON (lite mode)."""

    items = await _load_items_for_feed()
    if not items:
        return _empty_items_response()

    ranked = rank_trending(items, limit=_clamp_limit(limit, default=20, hard_max=60))
    out = [candidate_to_feed_item(candidate) for candidate in ranked]
    return {"success": True, "data": {"items": out}}


@app.get("/api/v1/feed/breaking", tags=["Feed"])
async def lite_breaking_feed(limit: int = 8):
    """Breaking feed from latest scraped JSON (lite mode)."""

    items = await _load_items_for_feed()
    if not items:
        return _empty_items_response()

    ranked = rank_breaking(items, limit=_clamp_limit(limit, default=8, hard_max=30))
    out = [candidate_to_feed_item(candidate) for candidate in ranked]
    return {"success": True, "data": {"items": out}}


@app.get("/api/v1/feed/department", tags=["Feed"])
async def lite_department_feed(limit: int = 12):
    """Department news feed with CS relevance ranking."""

    items = await _load_items_for_feed()
    if not items:
        return _empty_items_response()

    ranked = rank_department(items, limit=_clamp_limit(limit, default=12, hard_max=30))
    out = [candidate_to_feed_item(candidate) for candidate in ranked]
    return {"success": True, "data": {"items": out}}


@app.get("/api/v1/feed/student-stories", tags=["Feed"])
async def lite_student_stories_feed(limit: int = 12):
    """Student stories feed with career/community relevance ranking."""

    items = await _load_items_for_feed()
    if not items:
        return _empty_items_response()

    ranked = rank_student_stories(items, limit=_clamp_limit(limit, default=12, hard_max=30))
    out = [candidate_to_feed_item(candidate) for candidate in ranked]
    return {"success": True, "data": {"items": out}}


@app.get("/api/v1/feed/all-sections", tags=["Feed"])
async def lite_all_sections_feed(
    breaking_limit: int = 8,
    department_limit: int = 3,
    student_stories_limit: int = 3,
    trending_limit: int = 3,
):
    """Unified section response with backend-side ranking and scoring."""

    cached = await supabase_client.fetch_ranked_cache()
    if cached and {"breaking", "department", "student_stories", "trending"}.issubset(cached.keys()):
        return {"success": True, "data": cached}

    items = await _load_items_for_feed()
    if not items:
        return {
            "success": True,
            "data": {
                "breaking": [],
                "department": [],
                "student_stories": [],
                "trending": [],
            },
        }

    ranked = rank_all_sections(
        items,
        limits={
            "breaking": _clamp_limit(breaking_limit, default=8, hard_max=30),
            "department": _clamp_limit(department_limit, default=3, hard_max=30),
            "student_stories": _clamp_limit(student_stories_limit, default=3, hard_max=30),
            "trending": _clamp_limit(trending_limit, default=3, hard_max=30),
        },
    )

    payload = {
        "success": True,
        "data": {
            "breaking": [candidate_to_feed_item(candidate) for candidate in ranked["breaking"]],
            "department": [candidate_to_feed_item(candidate) for candidate in ranked["department"]],
            "student_stories": [candidate_to_feed_item(candidate) for candidate in ranked["student_stories"]],
            "trending": [candidate_to_feed_item(candidate) for candidate in ranked["trending"]],
        },
    }

    await supabase_client.upsert_ranked_cache(payload["data"])
    return payload


@app.get("/api/v1/feed/search", tags=["Feed"])
async def lite_search_feed(q: str = "", limit: int = 20):
    """Search across all feed items by keyword (case-insensitive title/summary/category match)."""

    query = (q or "").strip().lower()
    if not query:
        return _empty_items_response()

    items = await _load_items_for_feed()
    if not items:
        return _empty_items_response()

    capped = _clamp_limit(limit, default=20, hard_max=60)

    matched: list[dict] = []
    for item in items:
        haystack = " ".join(
            str(item.get(field) or "")
            for field in ("title", "summary", "content", "category", "source")
        ).lower()
        if query in haystack:
            matched.append(item)
        if len(matched) >= capped:
            break

    return {"success": True, "data": {"items": matched, "query": query, "total": len(matched)}}


# Note: Auth/feed/pipeline endpoints are not included in lite mode (DB required)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main_lite:app", host="0.0.0.0", port=8000, reload=True)
