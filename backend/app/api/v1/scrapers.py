"""Scraper management API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
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

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/status",
    summary="Get all scrapers status",
    description="Returns the current status of all configured scrapers including last run time, "
                "success/failure counts, and source totals. Admin only.",
    response_model=SingleResponse,
    responses={
        200: {"description": "Scraper status for all sources"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def get_scrapers_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get status of all configured scrapers.

    Reports last run time, item counts, and error states for each scraper source.
    """
    logger.info("ADMIN_ACTION: scrapers/status by %s (id=%s)", current_user.email, current_user.id)
    service = ScraperService(db)
    status_list = await service.get_scraper_status()
    
    return SingleResponse(data={
        "scrapers": status_list,
        "total_sources": len(status_list)
    })


@router.post(
    "/run/{scraper_name}",
    summary="Run a single scraper",
    description="Manually triggers a specific scraper to run immediately and returns results. Admin only. "
                "Valid scrapers: hackernews, reddit, twitter, github, medium, producthunt.",
    response_model=SingleResponse,
    responses={
        200: {"description": "Scraper execution results"},
        400: {"description": "Invalid scraper name"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def run_single_scraper(
    scraper_name: str = Path(description="Name of the scraper to run (hackernews, reddit, twitter, github, medium, producthunt)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Manually trigger a single scraper for immediate execution.

    Runs the specified scraper synchronously and returns the results.
    """
    logger.info("ADMIN_ACTION: scrapers/run/%s by %s (id=%s)", scraper_name, current_user.email, current_user.id)
    
    valid_scrapers= ["hackernews", "reddit", "twitter", "github", "medium", "producthunt"]
    
    if scraper_name not in valid_scrapers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scraper. Choose from: {', '.join(valid_scrapers)}"
        )
    
    # Run synchronously for immediate feedback
    import asyncio
    result = await trigger_scraper(scraper_name)
    
    return SingleResponse(data=result)


@router.post(
    "/run-all",
    summary="Run all scrapers",
    description="Manually triggers all configured scrapers to run immediately. Admin only.",
    response_model=SingleResponse,
    responses={
        200: {"description": "Combined results from all scrapers"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def run_all_scrapers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Manually trigger all scrapers for immediate execution.

    Runs every configured scraper and returns combined results.
    """
    logger.info("ADMIN_ACTION: scrapers/run-all by %s (id=%s)", current_user.email, current_user.id)
    
    import asyncio
    result = await trigger_all_scrapers()
    
    return SingleResponse(data=result)


@router.post(
    "/schedule/{scraper_name}",
    summary="Schedule scraper via Celery",
    description="Queues a scraper to run as a background Celery task. Admin only. "
                "Returns a task ID for tracking.",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Scraper task queued with task ID"},
        400: {"description": "Invalid scraper name"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def schedule_scraper(
    scraper_name: str = Path(description="Name of the scraper to schedule (hackernews, reddit, twitter, github, medium, producthunt)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Schedule a scraper to run as a Celery background task.

    Queues the task and returns immediately with a task ID for status tracking.
    """
    logger.info("ADMIN_ACTION: scrapers/schedule/%s by %s (id=%s)", scraper_name, current_user.email, current_user.id)
    
    task_map= {
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


@router.post(
    "/process-pending",
    summary="Process pending raw content",
    description="Processes pending scraped content through the AI pipeline. Admin only.",
    response_model=SingleResponse,
    responses={
        200: {"description": "Processing results"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def process_pending(
    limit: int = Query(10, ge=1, description="Maximum number of pending items to process"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Process pending raw content through the AI pipeline.

    Runs summarization, tagging, and scoring on pending scraped items.
    """
    logger.info("ADMIN_ACTION: scrapers/process-pending by %s (id=%s)", current_user.email, current_user.id)
    
    processor = ContentProcessor(db)
    result = await processor.process_pending_items(limit=limit)
    
    return SingleResponse(data=result)


@router.get(
    "/stats",
    summary="Get scraper processing statistics",
    description="Returns content processing statistics including counts by status and category. Admin only.",
    response_model=SingleResponse,
    responses={
        200: {"description": "Processing statistics"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def get_processing_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get content processing statistics.

    Reports item counts by processing status and category breakdown.
    """
    logger.info("ADMIN_ACTION: scrapers/stats by %s (id=%s)", current_user.email, current_user.id)
    
    processor = ContentProcessor(db)
    stats = await processor.get_processing_stats()
    
    return SingleResponse(data=stats)


@router.get(
    "/pending",
    summary="List pending raw content",
    description="Returns a list of raw scraped content items awaiting processing, ordered by most recent. Admin only.",
    response_model=SingleResponse,
    responses={
        200: {"description": "List of pending content items"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def get_pending_content(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of pending items to return (1-100)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get list of pending raw content awaiting processing.

    Returns items ordered by most recently scraped first, with metadata
    including title, URL, source, and content hash.
    """
    logger.info("ADMIN_ACTION: scrapers/pending by %s (id=%s)", current_user.email, current_user.id)
    
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


@router.post(
    "/sources/{source_id}/toggle",
    summary="Toggle scraper source",
    description="Enables or disables a specific scraper source. Disabled sources are skipped during scraping runs. Admin only.",
    response_model=SingleResponse,
    responses={
        200: {"description": "Updated source status"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
        404: {"description": "Source not found"},
    },
)
async def toggle_source(
    source_id: int = Path(description="Numeric ID of the scraper source to toggle"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Toggle a scraper source between enabled and disabled.

    Returns the updated source ID, name, and active status.
    """
    logger.info("ADMIN_ACTION: scrapers/sources/%s/toggle by %s (id=%s)", source_id, current_user.email, current_user.id)
    
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


@router.get(
    "/queue/status",
    summary="Get Celery queue status",
    description="Returns the current Celery task queue status including active, scheduled, and reserved task counts. Admin only.",
    response_model=SingleResponse,
    responses={
        200: {"description": "Queue status (may include error if Celery is not running)"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def get_celery_queue_status(
    current_user: User = Depends(get_current_admin_user)
):
    """Get Celery task queue status.

    Reports counts of active, scheduled, and reserved tasks.
    Returns an error note if the Celery worker is not running.
    """
    logger.info("ADMIN_ACTION: scrapers/queue/status by %s (id=%s)", current_user.email, current_user.id)
    
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


@router.api_route(
    "/dev/refresh",
    methods=["GET", "POST"],
    summary="Dev refresh (debug only)",
    description="Development-only endpoint that resets all content to pending, re-scrapes HackerNews, "
                "and reprocesses everything. Only available when DEBUG=True. Admin only.",
    responses={
        200: {"description": "Refresh results with scrape and process details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Only available in debug mode / Admin access required"},
    },
    deprecated=True,
)
async def dev_refresh_content(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Dev-only: Reset, re-scrape HackerNews, and process all content.

    WARNING: Destructive operation — deletes all processed content and
    resets raw content to pending. Only available when DEBUG=True.
    """
    logger.info("ADMIN_ACTION: scrapers/dev/refresh by %s (id=%s)", current_user.email, current_user.id)
    from app.config import settings
    if not settings.DEBUG:
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
