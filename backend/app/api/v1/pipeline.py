"""API endpoints for content pipeline management."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_db
from app.models import User
from app.services.pipeline_service import PipelineService
from app.services.content_processor import ContentProcessor
from app.services.vector_service import VectorService
from app.services.cache_service import invalidate_feed_caches, get_cache

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/run")
async def run_pipeline(
    scrape_limit: int = 10,
    process_limit: int = 10,
    embed_limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Run the full content pipeline (admin only)."""
    logger.info("ADMIN_ACTION: pipeline/run by %s (id=%s)", current_user.email, current_user.id)
    
    service = PipelineService(db)
    result = await service.run_full_pipeline(
        scrape_limit=scrape_limit,
        process_limit=process_limit,
        embed_limit=embed_limit
    )
    
    return result


@router.get("/status")
async def get_pipeline_status(
    db: AsyncSession = Depends(get_db)
):
    """Get pipeline status."""
    
    service = PipelineService(db)
    return await service.get_pipeline_status()


@router.post("/process")
async def process_pending(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Process pending raw content (admin only)."""
    logger.info("ADMIN_ACTION: pipeline/process by %s (id=%s)", current_user.email, current_user.id)
    
    service = ContentProcessor(db)
    result = await service.process_pending_items(limit=limit)
    
    return {
        "status": "completed",
        "result": result
    }


@router.post("/process/{content_id}")
async def process_single(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Process a single content item (admin only)."""
    logger.info("ADMIN_ACTION: pipeline/process/%s by %s (id=%s)", content_id, current_user.email, current_user.id)
    
    service = PipelineService(db)
    result = await service.process_single_item(content_id)
    
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    return result


@router.post("/embed")
async def generate_embeddings(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Generate embeddings for content without embeddings (admin only)."""
    logger.info("ADMIN_ACTION: pipeline/embed by %s (id=%s)", current_user.email, current_user.id)
    
    service = VectorService(db)
    result = await service.embed_pending_content(limit=limit)
    
    return {
        "status": "completed",
        "result": result
    }


@router.get("/stats")
async def get_processing_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get content processing statistics."""
    
    service = ContentProcessor(db)
    return await service.get_processing_stats()


@router.post("/cache/invalidate")
async def invalidate_caches(
    current_user: User = Depends(get_current_admin_user)
):
    """Invalidate all feed caches (admin only)."""
    logger.info("ADMIN_ACTION: pipeline/cache/invalidate by %s (id=%s)", current_user.email, current_user.id)
    removed = await invalidate_feed_caches()
    stats = await get_cache().stats()
    return {
        "status": "ok",
        "keys_removed": removed,
        "cache_stats": stats
    }
