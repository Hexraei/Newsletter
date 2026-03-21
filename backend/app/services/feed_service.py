"""Feed curation service for generating personalized newsletters."""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import select, func, case, literal, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProcessedContent, RawContent, Source
from app.config import settings

_IS_SQLITE = os.environ.get("DATABASE_URL", "").startswith("sqlite")


def _dept_filter(department: str):
    """Return a SQLAlchemy filter for department_tags containing *department*.

    PostgreSQL uses the native ``@>`` (contains) operator on JSONB arrays.
    SQLite stores JSON as TEXT, so we fall back to a LIKE match.
    """
    if _IS_SQLITE:
        return ProcessedContent.department_tags.like(f'%"{department}"%')
    return ProcessedContent.department_tags.contains([department])


_image_priority = case(
    (
        (ProcessedContent.featured_image_url != None) &
        (ProcessedContent.featured_image_url != ''),
        1,
    ),
    else_=0,
).desc()


class FeedService:
    """Service for curating personalized content feeds."""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    def _strict_mode_enabled(self) -> bool:
        return bool(getattr(settings, "RELEVANCE_STRICT_MODE", True))

    def _strict_relevance_filter(self):
        """Filter for strict TN/India relevance based on stored diagnostics."""
        if _IS_SQLITE:
            geo_expr = func.coalesce(
                func.cast(func.json_extract(ProcessedContent.visualizations, "$.geo_relevance_score"), Integer),
                0,
            )
            action_expr = func.coalesce(
                func.cast(func.json_extract(ProcessedContent.visualizations, "$.student_actionability_score"), Integer),
                0,
            )
            knowledge_expr = func.coalesce(
                func.cast(func.json_extract(ProcessedContent.visualizations, "$.knowledge_relevance_score"), Integer),
                0,
            )
        else:
            geo_expr = func.coalesce(
                func.cast(ProcessedContent.visualizations["geo_relevance_score"].astext, Integer),
                0,
            )
            action_expr = func.coalesce(
                func.cast(ProcessedContent.visualizations["student_actionability_score"].astext, Integer),
                0,
            )
            knowledge_expr = func.coalesce(
                func.cast(ProcessedContent.visualizations["knowledge_relevance_score"].astext, Integer),
                0,
            )
        min_geo = int(getattr(settings, "RELEVANCE_MIN_GEO_SCORE", 45))
        min_actionability = int(getattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 25))
        min_knowledge = int(getattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 32))
        global_override = int(getattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 65))
        global_knowledge_override = int(getattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 72))
        return (
            ((geo_expr >= min_geo) & (action_expr >= min_actionability))
            | ((geo_expr >= min_geo) & (knowledge_expr >= min_knowledge))
            | (action_expr >= global_override)
            | (knowledge_expr >= global_knowledge_override)
        )

    def _normalize_raw_id(self, raw_id: Optional[str]) -> Optional[str]:
        if not raw_id:
            return None
        raw = str(raw_id).strip().lower()
        if _IS_SQLITE:
            return raw.replace("-", "")
        return raw
    
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
        if self._strict_mode_enabled():
            query = query.where(self._strict_relevance_filter())
        
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
        
        # Prefer career/opportunity and knowledge/tech items over generic updates.
        text_col = func.lower(func.coalesce(ProcessedContent.title, '') + ' ' + func.coalesce(ProcessedContent.summary, ''))
        career_priority = case(
            (
                (ProcessedContent.category.in_(["career", "opportunity", "startup"])) |
                text_col.like('%internship%') |
                text_col.like('%hiring%') |
                text_col.like('%placement%') |
                text_col.like('%fresher%'),
                2,
            ),
            else_=0,
        )
        knowledge_priority = case(
            (
                (ProcessedContent.category.in_([
                    "research", "ai_ml", "electronics", "robotics", "energy",
                    "biotech", "aerospace", "automotive", "backend", "webdev", "devops"
                ])) |
                text_col.like('%research%') |
                text_col.like('%paper%') |
                text_col.like('%ieee%') |
                text_col.like('%arxiv%') |
                text_col.like('%technology%') |
                text_col.like('%semiconductor%') |
                text_col.like('%robotics%'),
                1,
            ),
            else_=0,
        )
        mix_priority = (career_priority + knowledge_priority).label("mix_priority")

        # Order by mix, then relevance (if filtering by dept), then attractiveness and recency.
        if department:
            query = query.order_by(
                mix_priority.desc(),
                _image_priority,
                ProcessedContent.relevance_score.desc().nullslast(),
                ProcessedContent.attractiveness_score.desc(),
                ProcessedContent.published_at.desc()
            )
        else:
            query = query.order_by(
                mix_priority.desc(),
                _image_priority,
                ProcessedContent.attractiveness_score.desc(),
                ProcessedContent.published_at.desc()
            )
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Cross-department supplement for low-content departments (disabled in strict mode)
        if department and len(items) < limit and not self._strict_mode_enabled():
            existing_ids = [item.id for item in items]
            week_ago_xd = datetime.now(timezone.utc) - timedelta(days=30)
            xdept_query = (
                select(ProcessedContent)
                .where(ProcessedContent.status == "published")
                .where(ProcessedContent.published_at >= week_ago_xd)
            )
            if existing_ids:
                xdept_query = xdept_query.where(
                    ProcessedContent.id.not_in(existing_ids)
                )
            xdept_query = xdept_query.order_by(
                _image_priority,
                ProcessedContent.attractiveness_score.desc(),
                ProcessedContent.published_at.desc()
            ).limit(limit - len(items)).offset(offset)
            xd_result = await self.db.execute(xdept_query)
            items.extend(xd_result.scalars().all())
        raw_ids = [self._normalize_raw_id(item.raw_content_id) for item in items if item.raw_content_id]
        raw_ids = [raw_id for raw_id in raw_ids if raw_id]
        url_map = {}
        content_map = {}
        if raw_ids:
            raw_result = await self.db.execute(
                select(RawContent.id, RawContent.original_url, RawContent.original_content)
                .where(RawContent.id.in_(raw_ids))
            )
            for row in raw_result.all():
                url_map[str(row.id)] = row.original_url
                content_map[str(row.id)] = row.original_content
        
        # Format response
        feed_items = []
        for item in items:
            raw_id = self._normalize_raw_id(item.raw_content_id)
            feed_items.append({
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "content": content_map.get(raw_id, "") if raw_id else "",
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
                "original_url": url_map.get(raw_id, None)
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
        text_col = func.lower(func.coalesce(ProcessedContent.title, '') + ' ' + func.coalesce(ProcessedContent.summary, ''))
        career_priority = case(
            (
                (ProcessedContent.category.in_(["career", "opportunity", "startup"])) |
                text_col.like('%internship%') |
                text_col.like('%hiring%') |
                text_col.like('%placement%'),
                2,
            ),
            else_=0,
        )
        knowledge_priority = case(
            (
                (ProcessedContent.category.in_([
                    "research", "ai_ml", "electronics", "robotics", "energy",
                    "biotech", "aerospace", "automotive", "backend", "webdev", "devops"
                ])) |
                text_col.like('%research%') |
                text_col.like('%paper%') |
                text_col.like('%technology%') |
                text_col.like('%robotics%'),
                1,
            ),
            else_=0,
        )
        mix_priority = (career_priority + knowledge_priority).label("mix_priority")

        query = (
            select(ProcessedContent)
            .where(ProcessedContent.status == "published")
        )
        if self._strict_mode_enabled():
            query = query.where(self._strict_relevance_filter())
        
        if department:
            query = query.where(_dept_filter(department))
        
        query = query.order_by(
            mix_priority.desc(),
            _image_priority,
            ProcessedContent.attractiveness_score.desc(),
            ProcessedContent.view_count.desc()
        ).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Cross-department supplement for low-content departments (disabled in strict mode)
        if department and len(items) < limit and not self._strict_mode_enabled():
            existing_ids = [item.id for item in items]
            xdept_query = (
                select(ProcessedContent)
                .where(ProcessedContent.status == "published")
            )
            if existing_ids:
                xdept_query = xdept_query.where(
                    ProcessedContent.id.not_in(existing_ids)
                )
            xdept_query = xdept_query.order_by(
                _image_priority,
                ProcessedContent.attractiveness_score.desc(),
                ProcessedContent.view_count.desc()
            ).limit(limit - len(items))
            xd_result = await self.db.execute(xdept_query)
            items.extend(xd_result.scalars().all())
        
        # Fetch original URLs and content
        raw_ids = [self._normalize_raw_id(item.raw_content_id) for item in items if item.raw_content_id]
        raw_ids = [raw_id for raw_id in raw_ids if raw_id]
        url_map = {}
        content_map = {}
        if raw_ids:
            raw_result = await self.db.execute(
                select(RawContent.id, RawContent.original_url, RawContent.original_content)
                .where(RawContent.id.in_(raw_ids))
            )
            for row in raw_result.all():
                url_map[str(row.id)] = row.original_url
                content_map[str(row.id)] = row.original_content
        
        return [
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "content": content_map.get(self._normalize_raw_id(item.raw_content_id), "") if item.raw_content_id else "",
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
                "original_url": url_map.get(self._normalize_raw_id(item.raw_content_id), None)
            }
            for item in items
        ]
    
    async def get_career_content(self, limit: int = 3, department: str = None) -> List[dict]:
        """Get career/startup content, optionally filtered to a department."""

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
        if self._strict_mode_enabled():
            query = query.where(self._strict_relevance_filter())
        if department:
            query = query.where(_dept_filter(department))
        result = await self.db.execute(query)
        items = result.scalars().all()

        raw_ids = [self._normalize_raw_id(item.raw_content_id) for item in items if item.raw_content_id]
        raw_ids = [raw_id for raw_id in raw_ids if raw_id]
        url_map = {}
        content_map = {}
        if raw_ids:
            raw_result = await self.db.execute(
                select(RawContent.id, RawContent.original_url, RawContent.original_content)
                .where(RawContent.id.in_(raw_ids))
            )
            for row in raw_result.all():
                url_map[str(row.id)] = row.original_url
                content_map[str(row.id)] = row.original_content

        return [
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "content": content_map.get(self._normalize_raw_id(item.raw_content_id), "") if item.raw_content_id else "",
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
                "original_url": url_map.get(self._normalize_raw_id(item.raw_content_id), None),
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

        if _IS_SQLITE:
            # SQLite: use julianday for age calculation
            age_hours = (func.julianday('now') - func.julianday(ProcessedContent.published_at)) * 24.0
        else:
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
        if self._strict_mode_enabled():
            query = query.where(self._strict_relevance_filter())
        if department:
            query = query.where(_dept_filter(department))
        primary_query = (
            query
            .where(total_score >= 40)
            .order_by(_image_priority, total_score.desc())
            .limit(limit)
        )
        result = await self.db.execute(primary_query)
        rows = result.all()
        items = [row[0] for row in rows]

        # Fallback: if not enough, fill with top recent by attractiveness
        if len(items) < limit:
            fallback_window = now - timedelta(days=30)
            existing_ids = [item.id for item in items]
            fallback_query = (
                select(ProcessedContent)
                .where(ProcessedContent.status == "published")
                .where(ProcessedContent.published_at >= fallback_window)
                .where(ProcessedContent.attractiveness_score >= 25)
            )
            if self._strict_mode_enabled():
                fallback_query = fallback_query.where(self._strict_relevance_filter())
            if department:
                fallback_query = fallback_query.where(_dept_filter(department))
            if existing_ids:
                fallback_query = fallback_query.where(
                    ProcessedContent.id.not_in(existing_ids)
                )
            fallback_query = fallback_query.order_by(
                _image_priority,
                ProcessedContent.attractiveness_score.desc(),
                ProcessedContent.published_at.desc(),
            ).limit(limit - len(items))
            fb_result = await self.db.execute(fallback_query)
            items.extend(fb_result.scalars().all())

        # Cross-department supplement: fill remaining with top general content (disabled in strict mode)
        if department and len(items) < limit and not self._strict_mode_enabled():
            existing_ids = [item.id for item in items]
            xdept_query = (
                select(ProcessedContent)
                .where(ProcessedContent.status == "published")
                .where(ProcessedContent.published_at >= recent_window)
                .where(ProcessedContent.attractiveness_score >= 25)
            )
            if existing_ids:
                xdept_query = xdept_query.where(
                    ProcessedContent.id.not_in(existing_ids)
                )
            xdept_query = xdept_query.order_by(
                _image_priority,
                ProcessedContent.attractiveness_score.desc(),
                ProcessedContent.published_at.desc(),
            ).limit(limit - len(items))
            xd_result = await self.db.execute(xdept_query)
            items.extend(xd_result.scalars().all())

        # Fetch original URLs and content
        raw_ids = [self._normalize_raw_id(item.raw_content_id) for item in items if item.raw_content_id]
        raw_ids = [raw_id for raw_id in raw_ids if raw_id]
        url_map = {}
        content_map = {}
        if raw_ids:
            raw_result = await self.db.execute(
                select(RawContent.id, RawContent.original_url, RawContent.original_content)
                .where(RawContent.id.in_(raw_ids))
            )
            for row in raw_result.all():
                url_map[str(row.id)] = row.original_url
                content_map[str(row.id)] = row.original_content

        return [
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "content": content_map.get(self._normalize_raw_id(item.raw_content_id), "") if item.raw_content_id else "",
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
                "original_url": url_map.get(self._normalize_raw_id(item.raw_content_id), None),
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
        if self._strict_mode_enabled():
            query = query.where(self._strict_relevance_filter())
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
                .where(self._strict_relevance_filter() if self._strict_mode_enabled() else True)
                .where(_dept_filter(department) if department else True)
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
        if self._strict_mode_enabled():
            query = query.where(self._strict_relevance_filter())

        if department:
            query = query.where(_dept_filter(department))

        query = query.order_by(
            ProcessedContent.attractiveness_score.desc(),
            ProcessedContent.published_at.desc(),
        ).limit(total)

        result = await self.db.execute(query)
        items = result.scalars().all()

        # Fetch original URLs and metadata
        raw_ids = [self._normalize_raw_id(item.raw_content_id) for item in items if item.raw_content_id]
        raw_ids = [raw_id for raw_id in raw_ids if raw_id]
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
            raw_id = self._normalize_raw_id(item.raw_content_id) or ""
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

        strict_filter = self._strict_relevance_filter()
        strict_result = await self.db.execute(
            select(func.count(ProcessedContent.id))
            .where(ProcessedContent.status == "published")
            .where(strict_filter)
        )
        strict_relevant = strict_result.scalar() or 0
        
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

        india_result = await self.db.execute(
            select(func.count(ProcessedContent.id))
            .where(ProcessedContent.status == "published")
            .where(
                func.lower(func.coalesce(ProcessedContent.title, "") + " " + func.coalesce(ProcessedContent.summary, "")).like("%india%")
                | func.lower(func.coalesce(ProcessedContent.title, "") + " " + func.coalesce(ProcessedContent.summary, "")).like("%indian%")
            )
        )
        tamil_result = await self.db.execute(
            select(func.count(ProcessedContent.id))
            .where(ProcessedContent.status == "published")
            .where(
                func.lower(func.coalesce(ProcessedContent.title, "") + " " + func.coalesce(ProcessedContent.summary, "")).like("%tamil%")
                | func.lower(func.coalesce(ProcessedContent.title, "") + " " + func.coalesce(ProcessedContent.summary, "")).like("%chennai%")
            )
        )
        india_count = india_result.scalar() or 0
        tamil_count = tamil_result.scalar() or 0
        
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
            "average_attractiveness_score": round(avg_score, 2),
            "strict_relevance_enabled": self._strict_mode_enabled(),
            "strict_relevant_count": strict_relevant,
            "india_signal_share": round((india_count / total_published) * 100, 2) if total_published else 0.0,
            "tamil_signal_share": round((tamil_count / total_published) * 100, 2) if total_published else 0.0,
        }
