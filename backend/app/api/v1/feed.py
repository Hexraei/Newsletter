"""API endpoints for content feed."""

import hashlib
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_current_user, get_optional_current_user, get_db
from app.models import ProcessedContent, RawContent, User, UserFeedback, UserSaves
from app.schemas.content import FeedbackRequest
from app.schemas.responses import SingleResponse, SuccessResponse
from app.services.cache_service import cached, get_cache, invalidate_feed_caches
from app.services.feed_service import FeedService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# Cached data-fetching helpers (in-memory TTL cache sits in front of DB/service)
# ---------------------------------------------------------------------------

@cached(ttl=1800, key_prefix="feed:trending")
async def _fetch_trending(limit: int, department: Optional[str], db: AsyncSession):
    service = FeedService(db)
    return await service.get_trending_content(limit=limit, department=department)


@cached(ttl=600, key_prefix="feed:breaking")
async def _fetch_breaking(limit: int, department: Optional[str], db: AsyncSession):
    service = FeedService(db)
    return await service.get_breaking_news(limit=limit, department=department)


@cached(ttl=21600, key_prefix="feed:daily_digest")
async def _fetch_daily_digest(limit: int, department: Optional[str], db: AsyncSession):
    service = FeedService(db)
    return await service.get_daily_digest(limit=limit, department=department)


@cached(ttl=3600, key_prefix="feed:all_sections")
async def _fetch_all_sections(
    breaking_limit: int,
    department_limit: int,
    trending_limit: int,
    department: Optional[str],
    db: AsyncSession,
):
    dept_key = (department or "CSE").upper()

    from sqlalchemy import text as sa_text
    try:
        row = (await db.execute(
            sa_text("SELECT data FROM cached_feeds WHERE department = :d"),
            {"d": dept_key},
        )).first()
        if row and row[0]:
            return {"success": True, "data": row[0]}
    except Exception:
        pass  # cached_feeds table may not exist (e.g. SQLite local dev)

    service = FeedService(db)
    breaking = await service.get_breaking_news(limit=breaking_limit, department=dept_key)
    trending = await service.get_trending_content(limit=trending_limit, department=dept_key)
    dept_feed = await service.get_personalized_feed(department=dept_key, limit=department_limit)
    dept_items = dept_feed.get("items", [])
    research = await service.get_research_papers(department=dept_key, featured_limit=3, general_limit=10)

    return {
        "success": True,
        "data": {
            "breaking": breaking,
            "department": dept_items,
            "trending": trending,
            "research_papers": research,
        },
    }


# ---------------------------------------------------------------------------
# ETag helpers
# ---------------------------------------------------------------------------


def compute_etag(data: dict) -> str:
    """Compute ETag from response data."""
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(content.encode()).hexdigest()


def etag_response(request: Request, data: dict) -> JSONResponse | Response:
    """Return 304 if ETag matches, otherwise JSONResponse with ETag header."""
    etag = compute_etag(data)
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304)
    return JSONResponse(content=data, headers={"ETag": f'"{etag}"'})


@router.get(
    "/personalized",
    summary="Get personalized feed",
    description="Returns a personalized content feed based on user interests and department. "
                "Authenticated users automatically get content tailored to their profile.",
    responses={
        200: {"description": "Personalized content feed"},
        422: {"description": "Invalid query parameters"},
    },
)
@cached(ttl=1800, key_prefix="feed:personalized")
async def get_personalized_feed(
    interests: Optional[List[str]] = Query(None, description="List of interest tags to filter content"),
    department: Optional[str] = Query(None, description="Department key to filter by (e.g., CSE, IT, AIDS)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of items to return (1-100)"),
    offset: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Get personalized content feed.

    Returns articles ranked by relevance to the user's interests and department.
    If authenticated, the user's saved preferences are used as defaults.
    Results are cached for 30 minutes.
    """
    
    service = FeedService(db)
    
    # Use user's interests if authenticated and no explicit filters
    if current_user and not interests and not department:
        interests = current_user.interests or []
        department = current_user.department
    
    return await service.get_personalized_feed(
        user_interests=interests,
        department=department,
        limit=limit,
        offset=offset
    )


@router.get(
    "/trending",
    summary="Get trending articles",
    description="Returns top trending articles ranked by engagement score, optionally filtered by department.",
    responses={
        200: {"description": "List of trending articles"},
        422: {"description": "Invalid query parameters"},
    },
)
async def get_trending(
    request: Request,
    limit: int = Query(10, ge=1, le=50, description="Number of articles to return (1-50)"),
    department: Optional[str] = Query(None, description="Department key to filter by (e.g., CSE, IT, AIDS)"),
    db: AsyncSession = Depends(get_db)
):
    """Get trending articles ranked by engagement and recency.

    Articles are scored based on views, saves, and recency.
    Supports ETag-based caching; returns 304 if content unchanged.
    Results are cached for 30 minutes.
    """
    
    data = await _fetch_trending(limit=limit, department=department, db=db)
    return etag_response(request, data)


@router.get(
    "/breaking",
    summary="Get breaking news",
    description="Returns the latest breaking news alerts, optionally filtered by department.",
    responses={
        200: {"description": "List of breaking news articles"},
        422: {"description": "Invalid query parameters"},
    },
)
async def get_breaking_news(
    request: Request,
    limit: int = Query(5, ge=1, le=20, description="Number of breaking news items to return (1-20)"),
    department: Optional[str] = Query(None, description="Department key to filter by (e.g., CSE, IT, AIDS)"),
    db: AsyncSession = Depends(get_db)
):
    """Get breaking news alerts.

    Returns time-sensitive, high-priority articles flagged as breaking news.
    Supports ETag-based caching; returns 304 if content unchanged.
    Results are cached for 10 minutes.
    """
    
    data = await _fetch_breaking(limit=limit, department=department, db=db)
    return etag_response(request, data)


@router.get(
    "/daily-digest",
    summary="Get daily digest",
    description="Returns a curated daily digest of top content, optionally filtered by department.",
    responses={
        200: {"description": "Daily digest of top articles"},
        422: {"description": "Invalid query parameters"},
    },
)
async def get_daily_digest(
    request: Request,
    limit: int = Query(5, ge=1, le=10, description="Number of digest items to return (1-10)"),
    department: Optional[str] = Query(None, description="Department key to filter by (e.g., CSE, IT, AIDS)"),
    db: AsyncSession = Depends(get_db)
):
    """Get daily digest of top content.

    Returns a curated selection of the day's most important articles.
    Supports ETag-based caching; returns 304 if content unchanged.
    Results are cached for 6 hours.
    """
    
    data = await _fetch_daily_digest(limit=limit, department=department, db=db)
    return etag_response(request, data)


@router.get(
    "/search",
    summary="Search content",
    description="Full-text search across article titles, summaries, and categories. Rate limited to 30 requests per minute.",
    responses={
        200: {"description": "Search results with matching articles"},
        422: {"description": "Invalid search parameters"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
async def search_content(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Search query string (1-200 characters)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return (1-100)"),
    offset: int = Query(0, ge=0, description="Number of results to skip for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """Search content by title, summary, or category.

    Performs case-insensitive LIKE search across published content.
    Results are ordered by attractiveness score descending.
    """
    
    # Escape LIKE wildcards to prevent wildcard abuse/DoS
    safe_q = q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    search_term = f"%{safe_q}%"
    
    result = await db.execute(
        select(ProcessedContent)
        .where(ProcessedContent.status == "published")
        .where(
            or_(
                func.lower(ProcessedContent.title).like(search_term),
                func.lower(ProcessedContent.summary).like(search_term),
                func.lower(ProcessedContent.category).like(search_term),
            )
        )
        .order_by(ProcessedContent.attractiveness_score.desc())
        .limit(limit)
        .offset(offset)
    )
    items = result.scalars().all()
    
    # Fetch original URLs
    raw_ids = [item.raw_content_id for item in items if item.raw_content_id]
    url_map = {}
    if raw_ids:
        raw_result = await db.execute(
            select(RawContent.id, RawContent.original_url)
            .where(RawContent.id.in_(raw_ids))
        )
        url_map = {str(row.id): row.original_url for row in raw_result.all()}
    
    return {
        "query": q,
        "items": [
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "content_blocks": item.content_blocks,
                "category": item.category,
                "topic_tags": item.topic_tags,
                "department_tags": item.department_tags,
                "reading_time_minutes": item.reading_time_minutes,
                "attractiveness_score": item.attractiveness_score,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "is_breaking": item.is_breaking,
                "featured_image_url": item.featured_image_url,
                "original_url": url_map.get(str(item.raw_content_id), None),
            }
            for item in items
        ],
        "total": len(items),
    }


@router.get(
    "/saved",
    summary="Get saved articles",
    description="Returns the authenticated user's saved/bookmarked articles, ordered by most recently saved.",
    responses={
        200: {"description": "List of saved articles"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid query parameters"},
    },
)
async def get_saved_content(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of saved items to return (1-100)"),
    offset: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the authenticated user's saved/bookmarked articles.

    Returns saved articles ordered by most recently saved first.
    Requires authentication.
    """
    
    result = await db.execute(
        select(ProcessedContent)
        .join(UserSaves, UserSaves.content_id == ProcessedContent.id)
        .where(UserSaves.user_id == str(current_user.id))
        .order_by(UserSaves.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = result.scalars().all()
    
    # Fetch original URLs
    raw_ids = [item.raw_content_id for item in items if item.raw_content_id]
    url_map = {}
    if raw_ids:
        raw_result = await db.execute(
            select(RawContent.id, RawContent.original_url)
            .where(RawContent.id.in_(raw_ids))
        )
        url_map = {str(row.id): row.original_url for row in raw_result.all()}
    
    return {
        "items": [
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "content_blocks": item.content_blocks,
                "category": item.category,
                "topic_tags": item.topic_tags,
                "reading_time_minutes": item.reading_time_minutes,
                "attractiveness_score": item.attractiveness_score,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "original_url": url_map.get(str(item.raw_content_id), None),
            }
            for item in items
        ],
        "total": len(items),
    }


@router.get(
    "/category/{category}",
    summary="Get content by category",
    description="Returns articles filtered by a specific content category.",
    responses={
        200: {"description": "Articles in the specified category"},
        422: {"description": "Invalid query parameters"},
    },
)
@cached(ttl=1800, key_prefix="feed:category")
async def get_by_category(
    category: str = Path(description="Content category to filter by (e.g., technology, research, career)"),
    limit: int = Query(10, ge=1, le=50, description="Number of articles to return (1-50)"),
    db: AsyncSession = Depends(get_db)
):
    """Get content filtered by category.

    Returns articles matching the specified category, ordered by relevance.
    Results are cached for 30 minutes.
    """
    
    service = FeedService(db)
    items = await service.get_content_by_category(category, limit=limit)
    
    return {
        "category": category,
        "items": items,
        "total": len(items)
    }


@router.post(
    "/{content_id}/read",
    summary="Record content read",
    description="Records that a piece of content was read, incrementing its view count.",
    responses={
        200: {"description": "Read event recorded successfully"},
        404: {"description": "Content not found"},
    },
)
async def record_read(
    content_id: str = Path(description="Unique identifier of the content item"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Record that content was read.

    Increments the view counter for the specified content item.
    Works for both authenticated and anonymous users.
    """
    
    service = FeedService(db)
    success = await service.record_read(content_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {"status": "recorded"}


@router.post(
    "/{content_id}/save",
    summary="Save/bookmark content",
    description="Adds a content item to the authenticated user's saved/bookmarks list.",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Content saved or already saved"},
        401: {"description": "Not authenticated"},
        404: {"description": "Content not found"},
    },
)
async def save_content(
    content_id: str = Path(description="Unique identifier of the content item to save"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Save/bookmark a content item.

    Adds the article to the user's saved list. Returns success even if
    already saved (idempotent).
    """
    
    # Check content exists
    result = await db.execute(
        select(ProcessedContent).where(ProcessedContent.id == content_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Check if already saved
    result = await db.execute(
        select(UserSaves).where(
            UserSaves.user_id == str(current_user.id),
            UserSaves.content_id == content_id
        )
    )
    if result.scalar_one_or_none():
        return SuccessResponse(message="Already saved")
    
    save = UserSaves(
        user_id=str(current_user.id),
        content_id=content_id
    )
    db.add(save)
    await db.commit()
    
    return SuccessResponse(message="Content saved")


@router.delete(
    "/{content_id}/save",
    summary="Unsave/unbookmark content",
    description="Removes a content item from the authenticated user's saved/bookmarks list.",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Content removed from saved list"},
        401: {"description": "Not authenticated"},
        404: {"description": "Saved item not found"},
    },
)
async def unsave_content(
    content_id: str = Path(description="Unique identifier of the content item to unsave"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a saved/bookmarked content item.

    Removes the article from the user's saved list.
    Returns 404 if the item was not previously saved.
    """
    
    result = await db.execute(
        select(UserSaves).where(
            UserSaves.user_id == str(current_user.id),
            UserSaves.content_id == content_id
        )
    )
    save = result.scalar_one_or_none()
    
    if not save:
        raise HTTPException(status_code=404, detail="Saved item not found")
    
    await db.delete(save)
    await db.commit()
    
    return SuccessResponse(message="Content unsaved")


@router.post(
    "/{content_id}/feedback",
    summary="Submit content feedback",
    description="Allows authenticated users to submit feedback (like, dislike, report) on a content item.",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Feedback submitted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Content not found"},
        422: {"description": "Invalid feedback data"},
    },
)
async def submit_feedback(
    content_id: str = Path(description="Unique identifier of the content item"),
    feedback: FeedbackRequest = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit feedback on a content item.

    Accepts feedback type (like, dislike, report) with an optional reason.
    Used to improve content recommendations and flag inappropriate content.
    """
    
    # Check content exists
    result = await db.execute(
        select(ProcessedContent).where(ProcessedContent.id == content_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Content not found")
    
    fb = UserFeedback(
        user_id=str(current_user.id),
        content_id=content_id,
        feedback_type=feedback.feedback_type,
        reason=feedback.reason,
        reported_issue=feedback.reported_issue
    )
    db.add(fb)
    await db.commit()
    
    return SuccessResponse(message="Feedback submitted")


@router.get(
    "/all-sections",
    summary="Get all homepage sections",
    description="Returns a unified response containing breaking news, department feed, trending articles, "
                "and research papers for the homepage. Uses multi-layer caching for performance.",
    responses={
        200: {"description": "All homepage sections bundled together"},
        422: {"description": "Invalid query parameters"},
    },
)
async def get_all_sections(
    request: Request,
    breaking_limit: int = Query(8, ge=1, le=30, description="Max breaking news items (1-30)"),
    department_limit: int = Query(15, ge=1, le=50, description="Max department feed items (1-50)"),
    trending_limit: int = Query(10, ge=1, le=30, description="Max trending items (1-30)"),
    department: Optional[str] = Query(None, description="Department key to filter by (defaults to CSE)"),
    db: AsyncSession = Depends(get_db),
):
    """Get all homepage sections in a single request.

    Returns breaking news, department-specific feed, trending articles,
    and research papers. Uses a multi-layer caching strategy:
    in-memory TTL cache → DB-level cached_feeds → live computation.
    Supports ETag-based caching; returns 304 if content unchanged.
    """
    data = await _fetch_all_sections(
        breaking_limit=breaking_limit,
        department_limit=department_limit,
        trending_limit=trending_limit,
        department=department,
        db=db,
    )
    return etag_response(request, data)


@router.get(
    "/cache-stats",
    summary="Get cache statistics",
    description="Returns in-memory cache statistics including hit/miss rates, cached keys, and memory usage estimates.",
    responses={200: {"description": "Cache statistics"}},
)
async def get_cache_stats():
    """Return in-memory cache statistics.

    Reports hits, misses, cached key count, and estimated memory usage.
    """
    cache = get_cache()
    return await cache.stats()


@router.get(
    "/stats",
    summary="Get feed statistics",
    description="Returns aggregate statistics about the content feed including total articles, categories, and processing metrics.",
    responses={200: {"description": "Feed statistics"}},
)
async def get_feed_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get aggregate feed statistics.

    Returns counts of total articles, categories, sources, and processing metrics.
    """
    
    service = FeedService(db)
    return await service.get_feed_stats()
