"""Lightweight FastAPI app without database for testing."""

import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.integrations.ai_provider import AIProvider, check_ai_status


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


def _parse_json_field(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _engagement_score(item: dict) -> int:
    engagement = _parse_json_field(item.get("engagement"))
    upvotes = _safe_int(engagement.get("upvotes"))
    comments = _safe_int(engagement.get("comments"))
    stars = _safe_int(engagement.get("stars"))
    forks = _safe_int(engagement.get("forks"))

    content_text = str(item.get("content") or "")
    score_match = re.search(r"score\s*:\s*(\d+)", content_text, flags=re.IGNORECASE)
    comments_match = re.search(r"comments\s*:\s*(\d+)", content_text, flags=re.IGNORECASE)

    if upvotes == 0 and score_match:
        upvotes = _safe_int(score_match.group(1))
    if comments == 0 and comments_match:
        comments = _safe_int(comments_match.group(1))

    return upvotes + comments * 2 + stars + forks * 2


def _summary_text(item: dict, max_len: int = 140) -> str:
    content = str(item.get("content") or "").strip()
    if content.lower().startswith("score:"):
        content = ""

    source = str(item.get("source") or "Campus Tech")
    base = content if content else f"{source} update for CS students."
    collapsed = " ".join(base.split())
    return collapsed[: max_len - 3] + "..." if len(collapsed) > max_len else collapsed


def _category_text(item: dict) -> str:
    metadata = _parse_json_field(item.get("metadata"))
    category = str(metadata.get("category") or "").strip()
    return category if category else "general"


def _breaking_score(item: dict) -> int:
    title = str(item.get("title") or "").lower()
    summary = _summary_text(item, max_len=180).lower()
    text = f"{title} {summary}"
    keywords = [
        "breaking", "breach", "outage", "down", "critical", "urgent",
        "incident", "attack", "leak", "ban", "lawsuit", "shutdown",
        "acquires", "launch", "security",
    ]
    keyword_hits = sum(1 for k in keywords if k in text)
    return _engagement_score(item) + keyword_hits * 25


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


def _to_feed_item(item: dict, is_breaking: bool = False) -> dict:
    return {
        "title": str(item.get("title") or ""),
        "summary": _summary_text(item),
        "source": str(item.get("source") or "Campus Tech"),
        "url": str(item.get("url") or "#"),
        "original_url": str(item.get("url") or "#"),
        "category": _category_text(item),
        "is_breaking": is_breaking,
        "published_at": item.get("published_at"),
        "attractiveness_score": _engagement_score(item),
    }

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

    items = _load_scraped_items()
    if not items:
        return {"success": True, "data": {"items": []}}

    ranked = sorted(items, key=_engagement_score, reverse=True)
    out = [_to_feed_item(item, is_breaking=False) for item in ranked[: max(1, min(limit, 60))]]
    return {"success": True, "data": {"items": out}}


@app.get("/api/v1/feed/breaking", tags=["Feed"])
async def lite_breaking_feed(limit: int = 8):
    """Breaking feed from latest scraped JSON (lite mode)."""

    items = _load_scraped_items()
    if not items:
        return {"success": True, "data": {"items": []}}

    ranked = sorted(items, key=_breaking_score, reverse=True)
    out = [_to_feed_item(item, is_breaking=True) for item in ranked[: max(1, min(limit, 30))]]
    return {"success": True, "data": {"items": out}}


# Note: Auth/feed/pipeline endpoints are not included in lite mode (DB required)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main_lite:app", host="0.0.0.0", port=8000, reload=True)
