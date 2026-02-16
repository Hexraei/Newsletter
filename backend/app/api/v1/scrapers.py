"""Scraper management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_db
from app.models import RawContent, Source, User
from app.schemas.responses import SingleResponse, SuccessResponse
from app.services.content_processor import ContentProcessor
from app.services.scraper_service import ScraperService
from app.tasks.scraper_tasks import (
    scrape_all,
    scrape_github,
    scrape_hackernews,
    scrape_medium,
    scrape_producthunt,
    scrape_reddit,
    scrape_twitter,
    trigger_all_scrapers,
    trigger_scraper,
)

router = APIRouter()


@router.get("/status", response_model=SingleResponse)
async def get_scrapers_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get status of all scrapers."""
    service = ScraperService(db)
    status_list = await service.get_scraper_status()
    
    return SingleResponse(data={
        "scrapers": status_list,
        "total_sources": len(status_list)
    })


@router.post("/run/{scraper_name}", response_model=SingleResponse)
async def run_single_scraper(
    scraper_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Manually trigger a single scraper."""
    
    valid_scrapers = ["hackernews", "reddit", "twitter", "github", "medium", "producthunt"]
    
    if scraper_name not in valid_scrapers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scraper. Choose from: {', '.join(valid_scrapers)}"
        )
    
    # Run synchronously for immediate feedback
    import asyncio
    result = await trigger_scraper(scraper_name)
    
    return SingleResponse(data=result)


@router.post("/run-all", response_model=SingleResponse)
async def run_all_scrapers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Manually trigger all scrapers."""
    
    import asyncio
    result = await trigger_all_scrapers()
    
    return SingleResponse(data=result)


@router.post("/schedule/{scraper_name}", response_model=SuccessResponse)
async def schedule_scraper(
    scraper_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Schedule a scraper to run via Celery."""
    
    task_map = {
        "hackernews": scrape_hackernews,
        "reddit": scrape_reddit,
        "twitter": scrape_twitter,
        "github": scrape_github,
        "medium": scrape_medium,
        "producthunt": scrape_producthunt,
    }
    
    if scraper_name not in task_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scraper. Choose from: {', '.join(task_map.keys())}"
        )
    
    # Queue the task
    task = task_map[scraper_name].delay()
    
    return SuccessResponse(
        message=f"Scraper '{scraper_name}' scheduled",
        data={"task_id": task.id}
    )


@router.post("/process-pending", response_model=SingleResponse)
async def process_pending(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Process pending raw content."""
    
    processor = ContentProcessor(db)
    result = await processor.process_pending_items(limit=limit)
    
    return SingleResponse(data=result)


@router.get("/stats", response_model=SingleResponse)
async def get_processing_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get content processing statistics."""
    
    processor = ContentProcessor(db)
    stats = await processor.get_processing_stats()
    
    return SingleResponse(data=stats)


@router.get("/pending", response_model=SingleResponse)
async def get_pending_content(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get list of pending raw content."""
    
    result = await db.execute(
        select(RawContent)
        .where(RawContent.status == "pending")
        .order_by(RawContent.scraped_at.desc())
        .limit(limit)
    )
    pending_items = result.scalars().all()
    
    items_data = []
    for item in pending_items:
        items_data.append({
            "id": str(item.id),
            "title": item.original_title,
            "url": item.original_url,
            "source_id": item.source_id,
            "scraped_at": item.scraped_at.isoformat() if item.scraped_at else None,
            "content_hash": item.content_hash,
        })
    
    return SingleResponse(data={
        "pending_items": items_data,
        "count": len(items_data)
    })


@router.post("/sources/{source_id}/toggle", response_model=SingleResponse)
async def toggle_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Enable/disable a scraper source."""
    
    result = await db.execute(
        select(Source).where(Source.id == source_id)
    )
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    source.is_active = not source.is_active
    await db.commit()
    
    return SingleResponse(data={
        "source_id": source_id,
        "name": source.name,
        "is_active": source.is_active
    })


@router.get("/queue/status", response_model=SingleResponse)
async def get_celery_queue_status(
    current_user: User = Depends(get_current_admin_user)
):
    """Get Celery task queue status."""
    
    try:
        from app.tasks.scraper_tasks import celery_app
        
        # Get queue info
        inspector = celery_app.control.inspect()
        
        active = inspector.active() or {}
        scheduled = inspector.scheduled() or {}
        reserved = inspector.reserved() or {}
        
        return SingleResponse(data={
            "active_tasks": sum(len(t) for t in active.values()),
            "scheduled_tasks": sum(len(t) for t in scheduled.values()),
            "reserved_tasks": sum(len(t) for t in reserved.values()),
        })
    except Exception as e:
        return SingleResponse(data={
            "error": str(e),
            "note": "Celery worker may not be running"
        })


@router.api_route("/dev/refresh", methods=["GET", "POST"])
async def dev_refresh_content(
    db: AsyncSession = Depends(get_db)
):
    """Dev-only: Reset, re-scrape HN, and process all content. No auth required."""
    from app.config import settings
    if not getattr(settings, 'DEBUG', True):
        raise HTTPException(status_code=403, detail="Only available in debug mode")

    from app.models import ProcessedContent as PC
    from sqlalchemy import update, delete

    # Reset all raw content to pending so they get reprocessed
    await db.execute(
        update(RawContent).where(RawContent.status == "processed").values(status="pending")
    )
    # Delete old processed content so fresh versions are created
    await db.execute(delete(PC))
    await db.commit()

    service = ScraperService(db)
    await service.initialize_sources()
    scrape_result = await service.run_scraper("hackernews", limit=30)

    processor = ContentProcessor(db)
    process_result = await processor.process_pending_items(limit=50)

    return SingleResponse(data={
        "scrape": scrape_result,
        "process": process_result,
    })
