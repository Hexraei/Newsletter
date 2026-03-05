"""Health check endpoints for content freshness monitoring."""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.content import RawContent

router = APIRouter()


@router.get("/content")
async def content_health(db: AsyncSession = Depends(get_db)):
    """Check content freshness and scraper health."""
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
