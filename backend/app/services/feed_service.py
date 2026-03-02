"""Feed curation service for generating personalized newsletters."""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import select, func, case, literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProcessedContent, RawContent, Source

_IS_SQLITE = os.environ.get("DATABASE_URL", "").startswith("sqlite")


def _dept_filter(department: str):
    """Return a SQLAlchemy filter for department_tags containing *department*.

    PostgreSQL uses the native ``@>`` (contains) operator on JSONB arrays.
    SQLite stores JSON as TEXT, so we fall back to a LIKE match.
    """
    if _IS_SQLITE:
        return ProcessedContent.department_tags.like(f'%"{department}"%')
    return ProcessedContent.department_tags.contains([department])


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
        
        # Filter by recency — try 30 days first, fall back to all content if empty
        week_ago = datetime.now(timezone.utc) - timedelta(days=30)
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
            query = query.where(_dept_filter(department))
        
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
                "image_credit": (item.visualizations or {}).get("image_credit"),
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
    
    async def get_trending_content(self, limit: int = 10, department: str = None) -> List[dict]:
        """Get trending content based on engagement scores."""
        
        query = (
            select(ProcessedContent)
            .where(ProcessedContent.status == "published")
        )
        
        if department:
            query = query.where(_dept_filter(department))
        
        query = query.order_by(
            ProcessedContent.attractiveness_score.desc(),
            ProcessedContent.view_count.desc()
        ).limit(limit)
        result = await self.db.execute(query)
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
                "is_breaking": item.is_breaking,
                "breaking_score": item.breaking_score,
                "topic_tags": item.topic_tags,
                "reading_time_minutes": item.reading_time_minutes,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "content_blocks": item.content_blocks,
                "featured_image_url": item.featured_image_url,
                "image_credit": (item.visualizations or {}).get("image_credit"),
                "original_url": url_map.get(str(item.raw_content_id), None)
            }
            for item in items
        ]
    
    async def get_career_content(self, limit: int = 3) -> List[dict]:
        """Get career and opportunity news (category = career or startup), not department-filtered."""

        query = (
            select(ProcessedContent)
            .where(ProcessedContent.status == "published")
            .where(ProcessedContent.category.in_(["career", "startup"]))
            .order_by(
                ProcessedContent.attractiveness_score.desc(),
                ProcessedContent.published_at.desc(),
            )
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()

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
                "is_breaking": item.is_breaking,
                "breaking_score": item.breaking_score,
                "topic_tags": item.topic_tags,
                "reading_time_minutes": item.reading_time_minutes,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "content_blocks": item.content_blocks,
                "featured_image_url": item.featured_image_url,
                "image_credit": (item.visualizations or {}).get("image_credit"),
                "original_url": url_map.get(str(item.raw_content_id), None),
            }
            for item in items
        ]

    async def get_breaking_news(self, limit: int = 5, department: str = None) -> List[dict]:
        """Get breaking news alerts with SQL-level ranking.

        Scoring done entirely in SQL:
        - base = COALESCE(breaking_score, attractiveness_score, 0)
        - recency boost: +20 (<=2h), +15 (<=6h), +10 (<=12h), +5 (<=24h)
        - is_breaking bonus: +10
        - urgent term bonus: +6 if title/summary contains breaking/outage/security/etc.
        """

        now = datetime.now(timezone.utc)
        recent_window = now - timedelta(days=30)  # extended window; recency_boost rewards truly new content

        age_hours = func.extract('epoch', literal(now) - ProcessedContent.published_at) / 3600.0

        recency_boost = case(
            (age_hours <= 2, 20),
            (age_hours <= 6, 15),
            (age_hours <= 12, 10),
            (age_hours <= 24, 5),
            else_=0,
        )

        breaking_bonus = case(
            (ProcessedContent.is_breaking == True, 10),
            else_=0,
        )

        text_col = func.lower(func.coalesce(ProcessedContent.title, '') + ' ' + func.coalesce(ProcessedContent.summary, ''))
        urgent_bonus = case(
            (
                text_col.like('%breaking%') |
                text_col.like('%outage%') |
                text_col.like('%breach%') |
                text_col.like('%zero-day%') |
                text_col.like('%vulnerability%') |
                text_col.like('%exploit%') |
                text_col.like('%acquires%') |
                text_col.like('%shutdown%') |
                text_col.like('%ban%') |
                text_col.like('%lawsuit%') |
                text_col.like('%emergency%') |
                text_col.like('%offline%') |
                text_col.like('%critical%'),
                6,
            ),
            else_=0,
        )

        base_score = func.coalesce(ProcessedContent.breaking_score, ProcessedContent.attractiveness_score, literal(0))
        total_score = (base_score + recency_boost + breaking_bonus + urgent_bonus).label('rank_score')

        query = (
            select(ProcessedContent, total_score)
            .where(ProcessedContent.status == "published")
            .where(ProcessedContent.published_at >= recent_window)
        )
        if department:
            query = query.where(_dept_filter(department))
        primary_query = (
            query
            .where(total_score >= 55)
            .order_by(total_score.desc())
            .limit(limit)
        )
        result = await self.db.execute(primary_query)
        rows = result.all()
        items = [row[0] for row in rows]

        # Fallback: if not enough, fill with top recent by attractiveness (14-day window, not 30)
        if len(items) < limit:
            fallback_window = now - timedelta(days=14)
            existing_ids = [item.id for item in items]
            fallback_query = (
                select(ProcessedContent)
                .where(ProcessedContent.status == "published")
                .where(ProcessedContent.published_at >= fallback_window)
                .where(ProcessedContent.attractiveness_score >= 40)
            )
            if department:
                fallback_query = fallback_query.where(_dept_filter(department))
            if existing_ids:
                fallback_query = fallback_query.where(
                    ProcessedContent.id.not_in(existing_ids)
                )
            fallback_query = fallback_query.order_by(
                ProcessedContent.attractiveness_score.desc(),
                ProcessedContent.published_at.desc(),
            ).limit(limit - len(items))
            fb_result = await self.db.execute(fallback_query)
            items.extend(fb_result.scalars().all())

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
                "content_blocks": item.content_blocks,
                "category": item.category,
                "topic_tags": item.topic_tags,
                "reading_time_minutes": item.reading_time_minutes,
                "attractiveness_score": item.attractiveness_score,
                "is_breaking": item.is_breaking,
                "breaking_score": item.breaking_score,
                "featured_image_url": item.featured_image_url,
                "image_credit": (item.visualizations or {}).get("image_credit"),
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "detected_at": item.breaking_detected_at.isoformat() if item.breaking_detected_at else None,
                "original_url": url_map.get(str(item.raw_content_id), None),
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
    
    async def get_daily_digest(self, limit: int = 5, department: str = None) -> Dict:
        """Generate a daily digest of top content."""
        
        today = datetime.now(timezone.utc).date()
        today_start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        
        # Get top stories from today
        query = (
            select(ProcessedContent)
            .where(ProcessedContent.status == "published")
            .where(ProcessedContent.published_at >= today_start)
            .where(ProcessedContent.attractiveness_score >= 50)
        )
        if department:
            query = query.where(_dept_filter(department))
        query = query.order_by(ProcessedContent.attractiveness_score.desc()).limit(limit)
        
        result = await self.db.execute(query)
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

    async def get_research_papers(
        self, department: str = None, featured_limit: int = 3, general_limit: int = 10
    ) -> Dict:
        """Get research papers split into featured (top) and general (rest)."""
        total = featured_limit + general_limit

        query = (
            select(ProcessedContent)
            .where(
                ProcessedContent.status == "published",
                ProcessedContent.content_type == "research_paper",
            )
        )

        if department:
            query = query.where(_dept_filter(department))

        query = query.order_by(
            ProcessedContent.attractiveness_score.desc(),
            ProcessedContent.published_at.desc(),
        ).limit(total)

        result = await self.db.execute(query)
        items = result.scalars().all()

        # Fetch original URLs and metadata
        raw_ids = [item.raw_content_id for item in items if item.raw_content_id]
        url_map = {}
        meta_map = {}
        if raw_ids:
            raw_result = await self.db.execute(
                select(RawContent.id, RawContent.original_url, RawContent.original_author, RawContent.raw_metadata)
                .where(RawContent.id.in_(raw_ids))
            )
            for row in raw_result.all():
                url_map[str(row.id)] = row.original_url
                meta_map[str(row.id)] = {
                    "author": row.original_author or "",
                    **(row.raw_metadata or {}),
                }

        def _to_dict(item):
            raw_id = str(item.raw_content_id) if item.raw_content_id else ""
            meta = meta_map.get(raw_id, {})
            return {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "category": item.category,
                "attractiveness_score": item.attractiveness_score,
                "topic_tags": item.topic_tags,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "content_blocks": item.content_blocks,
                "original_url": url_map.get(raw_id),
                "authors": meta.get("author", ""),
                "venue": meta.get("venue", ""),
                "citations": meta.get("citations", 0),
                "doi": meta.get("doi", ""),
            }

        all_items = [_to_dict(item) for item in items]
        return {
            "featured": all_items[:featured_limit],
            "papers": all_items[featured_limit:],
        }
    
    async def record_read(self, content_id: str) -> bool:
        """Record that content was read (atomic DB-level increment)."""
        from sqlalchemy import update as sa_update
        
        result = await self.db.execute(
            sa_update(ProcessedContent)
            .where(ProcessedContent.id == content_id)
            .values(read_count=ProcessedContent.read_count + 1)
        )
        await self.db.commit()
        return result.rowcount > 0
    
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
        today = datetime.now(timezone.utc).date()
        today_start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        
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
