"""Feed curation service for generating personalized newsletters."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProcessedContent, RawContent, Source


class FeedService:
    """Service for curating personalized content feeds."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_personalized_feed(
        self,
        user_interests: List[str] = None,
        department: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict:
        """Generate a personalized content feed."""
        
        # Base query - published content only
        query = select(ProcessedContent).where(
            ProcessedContent.status == "published"
        )
        
        # Filter by recency (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        query = query.where(ProcessedContent.published_at >= week_ago)
        
        # Apply interest filters
        if user_interests:
            # Match any of the user's interests
            query = query.where(
                func.array_overlap(ProcessedContent.topic_tags, user_interests) |
                func.array_overlap(ProcessedContent.department_tags, user_interests)
            )
        
        # Apply department filter
        if department:
            query = query.where(
                ProcessedContent.department_tags.contains([department])
            )
        
        # Order by attractiveness score and recency
        query = query.order_by(
            ProcessedContent.attractiveness_score.desc(),
            ProcessedContent.published_at.desc()
        )
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        # Batch fetch original URLs from raw content
        raw_ids = [item.raw_content_id for item in items if item.raw_content_id]
        url_map = {}
        if raw_ids:
            raw_result = await self.db.execute(
                select(RawContent.id, RawContent.original_url)
                .where(RawContent.id.in_(raw_ids))
            )
            url_map = {str(row.id): row.original_url for row in raw_result.all()}
        
        # Format response
        feed_items = []
        for item in items:
            feed_items.append({
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
                "original_url": url_map.get(str(item.raw_content_id), None)
            })
        
        return {
            "items": feed_items,
            "total": len(feed_items),
            "has_more": len(feed_items) == limit,
            "filters_applied": {
                "interests": user_interests,
                "department": department
            }
        }
    
    async def get_trending_content(self, limit: int = 10) -> List[dict]:
        """Get trending content based on engagement scores."""
        
        result = await self.db.execute(
            select(ProcessedContent)
            .where(ProcessedContent.status == "published")
            .order_by(
                ProcessedContent.attractiveness_score.desc(),
                ProcessedContent.view_count.desc()
            )
            .limit(limit)
        )
        items = result.scalars().all()
        
        # Fetch original URLs
        raw_ids = [item.raw_content_id for item in items if item.raw_content_id]
        url_map = {}
        if raw_ids:
            raw_result = await self.db.execute(
                select(RawContent.id, RawContent.original_url)
                .where(RawContent.id.in_(raw_ids))
            )
            url_map = {str(row.id): row.original_url for row in raw_result.all()}
        
        return [
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "category": item.category,
                "attractiveness_score": item.attractiveness_score,
                "topic_tags": item.topic_tags,
                "reading_time_minutes": item.reading_time_minutes,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "content_blocks": item.content_blocks,
                "original_url": url_map.get(str(item.raw_content_id), None)
            }
            for item in items
        ]
    
    async def get_breaking_news(self, limit: int = 5) -> List[dict]:
        """Get breaking news alerts."""
        
        result = await self.db.execute(
            select(ProcessedContent)
            .where(ProcessedContent.is_breaking == True)
            .where(ProcessedContent.status == "published")
            .order_by(ProcessedContent.breaking_detected_at.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        
        # Fetch original URLs
        raw_ids = [item.raw_content_id for item in items if item.raw_content_id]
        url_map = {}
        if raw_ids:
            raw_result = await self.db.execute(
                select(RawContent.id, RawContent.original_url)
                .where(RawContent.id.in_(raw_ids))
            )
            url_map = {str(row.id): row.original_url for row in raw_result.all()}
        
        return [
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "breaking_score": item.breaking_score,
                "detected_at": item.breaking_detected_at.isoformat() if item.breaking_detected_at else None,
                "original_url": url_map.get(str(item.raw_content_id), None)
            }
            for item in items
        ]
    
    async def get_content_by_category(
        self,
        category: str,
        limit: int = 10
    ) -> List[dict]:
        """Get content filtered by category."""
        
        result = await self.db.execute(
            select(ProcessedContent)
            .where(ProcessedContent.category == category)
            .where(ProcessedContent.status == "published")
            .order_by(ProcessedContent.published_at.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        
        return [
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "category": item.category,
                "attractiveness_score": item.attractiveness_score
            }
            for item in items
        ]
    
    async def get_daily_digest(self, limit: int = 5) -> Dict:
        """Generate a daily digest of top content."""
        
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        # Get top stories from today
        result = await self.db.execute(
            select(ProcessedContent)
            .where(ProcessedContent.status == "published")
            .where(ProcessedContent.published_at >= today_start)
            .where(ProcessedContent.attractiveness_score >= 50)
            .order_by(ProcessedContent.attractiveness_score.desc())
            .limit(limit)
        )
        today_items = result.scalars().all()
        
        # If not enough today, get recent high-quality content
        if len(today_items) < limit:
            remaining = limit - len(today_items)
            existing_ids = [item.id for item in today_items]
            
            result = await self.db.execute(
                select(ProcessedContent)
                .where(ProcessedContent.status == "published")
                .where(ProcessedContent.id.notin_(existing_ids) if existing_ids else True)
                .where(ProcessedContent.attractiveness_score >= 60)
                .order_by(ProcessedContent.published_at.desc())
                .limit(remaining)
            )
            additional_items = result.scalars().all()
            today_items = list(today_items) + list(additional_items)
        
        # Categorize items
        categories = {}
        for item in today_items:
            cat = item.category or "general"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "reading_time": item.reading_time_minutes
            })
        
        return {
            "date": today.isoformat(),
            "total_stories": len(today_items),
            "categories": categories
        }
    
    async def record_read(self, content_id: str) -> bool:
        """Record that content was read."""
        
        result = await self.db.execute(
            select(ProcessedContent).where(ProcessedContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        
        if content:
            content.read_count += 1
            await self.db.commit()
            return True
        return False
    
    async def get_feed_stats(self) -> Dict:
        """Get feed statistics."""
        
        # Total published content
        result = await self.db.execute(
            select(func.count(ProcessedContent.id))
            .where(ProcessedContent.status == "published")
        )
        total_published = result.scalar()
        
        # Content by category
        result = await self.db.execute(
            select(ProcessedContent.category, func.count(ProcessedContent.id))
            .where(ProcessedContent.status == "published")
            .group_by(ProcessedContent.category)
        )
        by_category = dict(result.all())
        
        # Average attractiveness score
        result = await self.db.execute(
            select(func.avg(ProcessedContent.attractiveness_score))
            .where(ProcessedContent.status == "published")
        )
        avg_score = result.scalar() or 0
        
        # Today's content count
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        result = await self.db.execute(
            select(func.count(ProcessedContent.id))
            .where(ProcessedContent.status == "published")
            .where(ProcessedContent.published_at >= today_start)
        )
        today_count = result.scalar()
        
        return {
            "total_published": total_published,
            "today_count": today_count,
            "by_category": by_category,
            "average_attractiveness_score": round(avg_score, 2)
        }
