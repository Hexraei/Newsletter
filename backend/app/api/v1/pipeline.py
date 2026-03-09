"""API endpoints for content pipeline management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_db
from app.models import User
from app.services.pipeline_service import PipelineService
from app.services.content_processor import ContentProcessor
from app.services.vector_service import VectorService
from app.services.cache_service import invalidate_feed_caches, get_cache

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/run",
    summary="Run full content pipeline",
    description="Executes the full content pipeline: scrape → process → embed. Admin only. "
                "Limits control the maximum items processed at each stage.",
    responses={
        200: {"description": "Pipeline execution results"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def run_pipeline(
    scrape_limit: int = Query(10, ge=1, description="Maximum number of items to scrape"),
    process_limit: int = Query(10, ge=1, description="Maximum number of items to process with AI"),
    embed_limit: int = Query(10, ge=1, description="Maximum number of items to generate embeddings for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Run the full content pipeline (admin only).

    Executes scraping, AI processing, and embedding generation sequentially.
    Each stage is limited to the specified maximum number of items.
    """
    logger.info("ADMIN_ACTION: pipeline/run by %s (id=%s)", current_user.email, current_user.id)
    
    service = PipelineService(db)
    result = await service.run_full_pipeline(
        scrape_limit=scrape_limit,
        process_limit=process_limit,
        embed_limit=embed_limit
    )
    
    return result


@router.get(
    "/status",
    summary="Get pipeline status",
    description="Returns the current status of the content pipeline including pending, processing, and completed item counts.",
    responses={200: {"description": "Pipeline status information"}},
)
async def get_pipeline_status(
    db: AsyncSession = Depends(get_db)
):
    """Get current content pipeline status.

    Reports counts of items at each pipeline stage (pending, processing, published).
    """
    
    service = PipelineService(db)
    return await service.get_pipeline_status()


@router.post(
    "/process",
    summary="Process pending content",
    description="Processes pending raw content through the AI pipeline (summarization, tagging, scoring). Admin only.",
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
    """Process pending raw content through AI (admin only).

    Runs summarization, category tagging, and attractiveness scoring
    on up to `limit` pending items.
    """
    logger.info("ADMIN_ACTION: pipeline/process by %s (id=%s)", current_user.email, current_user.id)
    
    service = ContentProcessor(db)
    result = await service.process_pending_items(limit=limit)
    
    return {
        "status": "completed",
        "result": result
    }


@router.post(
    "/process/{content_id}",
    summary="Process single content item",
    description="Processes a specific raw content item through the AI pipeline. Admin only.",
    responses={
        200: {"description": "Processing result for the item"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
        404: {"description": "Content item not found"},
    },
)
async def process_single(
    content_id: str = Path(description="Unique identifier of the raw content item to process"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Process a single content item through the AI pipeline (admin only).

    Useful for reprocessing or debugging individual articles.
    """
    logger.info("ADMIN_ACTION: pipeline/process/%s by %s (id=%s)", content_id, current_user.email, current_user.id)
    
    service = PipelineService(db)
    result = await service.process_single_item(content_id)
    
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    return result


@router.post(
    "/embed",
    summary="Generate content embeddings",
    description="Generates vector embeddings for processed content that lacks them. Admin only. "
                "Used for semantic search and content similarity.",
    responses={
        200: {"description": "Embedding generation results"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def generate_embeddings(
    limit: int = Query(10, ge=1, description="Maximum number of items to generate embeddings for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Generate vector embeddings for content without them (admin only).

    Processes up to `limit` published articles that don't yet have embeddings.
    """
    logger.info("ADMIN_ACTION: pipeline/embed by %s (id=%s)", current_user.email, current_user.id)
    
    service = VectorService(db)
    result = await service.embed_pending_content(limit=limit)
    
    return {
        "status": "completed",
        "result": result
    }


@router.get(
    "/stats",
    summary="Get processing statistics",
    description="Returns detailed content processing statistics including counts by status, category breakdown, and processing times.",
    responses={200: {"description": "Processing statistics"}},
)
async def get_processing_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get content processing statistics.

    Reports counts by processing status, category breakdown, and timing metrics.
    """
    
    service = ContentProcessor(db)
    return await service.get_processing_stats()


@router.post(
    "/cache/invalidate",
    summary="Invalidate feed caches",
    description="Clears all cached feed data, forcing fresh computation on next request. Admin only.",
    responses={
        200: {"description": "Cache invalidation result with stats"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def invalidate_caches(
    current_user: User = Depends(get_current_admin_user)
):
    """Invalidate all feed caches (admin only).

    Removes all cached feed entries and returns the number of keys removed
    along with updated cache statistics.
    """
    logger.info("ADMIN_ACTION: pipeline/cache/invalidate by %s (id=%s)", current_user.email, current_user.id)
    removed = await invalidate_feed_caches()
    stats = await get_cache().stats()
    return {
        "status": "ok",
        "keys_removed": removed,
        "cache_stats": stats
    }
