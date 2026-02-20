"""API endpoints for content feed."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_current_user, get_optional_current_user, get_db
from app.models import ProcessedContent, RawContent, User, UserFeedback, UserSaves
from app.schemas.content import FeedbackRequest
from app.schemas.responses import SingleResponse, SuccessResponse
from app.services.feed_service import FeedService

router = APIRouter()


@router.get("/personalized")
async def get_personalized_feed(
    interests: Optional[List[str]] = Query(None),
    department: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Get personalized content feed."""
    
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


@router.get("/trending")
async def get_trending(
    limit: int = Query(10, ge=1, le=50),
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get trending content."""
    
    service = FeedService(db)
    return await service.get_trending_content(limit=limit, department=department)


@router.get("/breaking")
async def get_breaking_news(
    limit: int = Query(5, ge=1, le=20),
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get breaking news alerts."""
    
    service = FeedService(db)
    return await service.get_breaking_news(limit=limit, department=department)


@router.get("/daily-digest")
async def get_daily_digest(
    limit: int = Query(5, ge=1, le=10),
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get daily digest of top content."""
    
    service = FeedService(db)
    return await service.get_daily_digest(limit=limit, department=department)


@router.get("/search")
async def search_content(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Search content by title, summary, or tags."""
    
    search_term = f"%{q.lower()}%"
    
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


@router.get("/saved")
async def get_saved_content(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's saved/bookmarked articles."""
    
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


@router.get("/category/{category}")
async def get_by_category(
    category: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get content by category."""
    
    service = FeedService(db)
    items = await service.get_content_by_category(category, limit=limit)
    
    return {
        "category": category,
        "items": items,
        "total": len(items)
    }


@router.post("/{content_id}/read")
async def record_read(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Record that content was read."""
    
    service = FeedService(db)
    success = await service.record_read(content_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {"status": "recorded"}


@router.post("/{content_id}/save", response_model=SuccessResponse)
async def save_content(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Save/bookmark content."""
    
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


@router.delete("/{content_id}/save", response_model=SuccessResponse)
async def unsave_content(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove saved/bookmarked content."""
    
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


@router.post("/{content_id}/feedback", response_model=SuccessResponse)
async def submit_feedback(
    content_id: str,
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit feedback on content."""
    
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


@router.get("/all-sections")
async def get_all_sections(
    breaking_limit: int = Query(8, ge=1, le=30),
    department_limit: int = Query(3, ge=1, le=30),
    trending_limit: int = Query(3, ge=1, le=30),
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Unified section response for the homepage with optional department filtering.

    Serves pre-cached data for instant page loads. Falls back to live
    computation on cache miss.
    """
    dept_key = (department or "CSE").upper()

    # Try cached data first (instant response)
    from sqlalchemy import text as sa_text
    row = (await db.execute(
        sa_text("SELECT data FROM cached_feeds WHERE department = :d"),
        {"d": dept_key},
    )).first()

    if row and row[0]:
        return {"success": True, "data": row[0]}

    # Cache miss — compute live
    service = FeedService(db)
    breaking = await service.get_breaking_news(limit=breaking_limit, department=department)
    trending = await service.get_trending_content(limit=trending_limit, department=department)
    dept_feed = await service.get_personalized_feed(department=department, limit=department_limit)
    dept_items = dept_feed.get("items", [])
    research = await service.get_research_papers(department=department, featured_limit=3, general_limit=10)

    return {
        "success": True,
        "data": {
            "breaking": breaking,
            "department": dept_items,
            "trending": trending,
            "research_papers": research,
        },
    }


@router.get("/stats")
async def get_feed_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get feed statistics."""
    
    service = FeedService(db)
    return await service.get_feed_stats()
