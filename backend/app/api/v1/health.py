"""Health check endpoints for content freshness and cache monitoring."""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.content import RawContent
from app.services.cache_service import get_cache, RedisCache

router = APIRouter()


@router.get(
    "/content",
    summary="Check content freshness",
    description="Returns content freshness metrics including last scrape time, article counts for 24h and 7d windows, "
                "and whether the content is considered stale.",
    responses={200: {"description": "Content health metrics"}},
)
async def content_health(db: AsyncSession = Depends(get_db)):
    """Check content freshness and scraper health.

    Reports the most recent scrape timestamp, article counts for the last
    24 hours and 7 days, and a staleness flag (true if no articles in 24h).
    """
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    # Most recent article timestamp
    result = await db.execute(
        select(func.max(RawContent.created_at))
    )
    last_scrape_time = result.scalar_one_or_none()

    # Count articles in last 24h
    result = await db.execute(
        select(func.count(RawContent.id))
        .where(RawContent.created_at >= cutoff_24h)
    )
    count_24h = result.scalar_one()

    # Count articles in last 7 days
    result = await db.execute(
        select(func.count(RawContent.id))
        .where(RawContent.created_at >= cutoff_7d)
    )
    count_7d = result.scalar_one()

    is_stale = count_24h == 0

    return {
        "success": True,
        "data": {
            "is_stale": is_stale,
            "last_scrape_time": last_scrape_time.isoformat() if last_scrape_time else None,
            "articles_last_24h": count_24h,
            "articles_last_7d": count_7d,
            "checked_at": now.isoformat(),
        },
    }


@router.get(
    "/cache",
    summary="Get cache health",
    description="Returns cache backend type (Redis or in-memory) and hit/miss statistics.",
    responses={200: {"description": "Cache health and statistics"}},
)
async def cache_stats():
    """Return cache backend type and hit/miss statistics.

    Reports whether Redis or in-memory cache is active, along with
    hit rate, miss count, and other performance metrics.
    """
    cache = get_cache()
    stats = await cache.stats()
    stats["backend_type"] = "redis" if isinstance(cache, RedisCache) else "in-memory"
    return {"success": True, "data": stats}
