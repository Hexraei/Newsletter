"""Content processing service for transforming raw to processed content."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.ai_provider import AIProvider
from app.models import ProcessedContent, RawContent, Source


class ContentProcessor:
    """Process raw scraped content into newsletter-ready format."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_provider = AIProvider()
    
    async def calculate_attractiveness_score(self, raw: RawContent) -> int:
        """Calculate attractiveness score (0-100) for content."""
        score = 0
        
        # Base score
        score += 20
        
        # Engagement bonus (from metadata)
        metadata = raw.raw_metadata or {}
        engagement = raw.raw_metadata.get("engagement", {}) if raw.raw_metadata else {}
        
        if engagement:
            # Hacker News: upvotes + comments
            upvotes = engagement.get("upvotes", 0)
            if upvotes > 500:
                score += 30
            elif upvotes > 100:
                score += 20
            elif upvotes > 50:
                score += 10
            
            # GitHub: stars
            stars = engagement.get("stars", 0)
            if stars > 1000:
                score += 30
            elif stars > 500:
                score += 20
            elif stars > 100:
                score += 10
        
        # Freshness bonus (published today)
        if raw.published_at:
            try:
                # Handle both timezone-aware and naive datetimes
                published = raw.published_at
                now = datetime.now(timezone.utc)
                if published.tzinfo is None:
                    # Naive datetime, assume UTC
                    published = published.replace(tzinfo=timezone.utc)
                age_hours = (now - published).total_seconds() / 3600
                if age_hours < 24:
                    score += 15
                elif age_hours < 48:
                    score += 10
                elif age_hours < 72:
                    score += 5
            except Exception:
                # Skip freshness bonus if date comparison fails
                pass
        
        # Content length bonus
        content_length = len(raw.original_content or "")
        if content_length > 1000:
            score += 10
        elif content_length > 500:
            score += 5
        
        # Source reliability bonus
        source_bonus = {
            "hackernews": 10,
            "github": 10,
            "reddit": 5,
            "medium": 5,
            "producthunt": 5,
        }
        source_result = await self.db.execute(
            select(Source).where(Source.id == raw.source_id)
        )
        source = source_result.scalar_one_or_none()
        if source:
            score += source_bonus.get(source.platform, 0)
        
        return min(100, score)
    
    async def process_pending_items(self, limit: int = 10) -> Dict:
        """Process pending raw content items."""
        
        # Get pending items
        result = await self.db.execute(
            select(RawContent)
            .where(RawContent.status == "pending")
            .order_by(RawContent.scraped_at.desc())
            .limit(limit)
        )
        pending_items = result.scalars().all()
        
        processed_count = 0
        errors = []
        
        for raw in pending_items:
            try:
                await self.process_single_item(raw)
                processed_count += 1
            except Exception as e:
                errors.append(f"Error processing {raw.id}: {str(e)}")
                raw.status = "failed"
                raw.processing_error = str(e)[:500]
                await self.db.commit()
        
        return {
            "processed": processed_count,
            "total_pending": len(pending_items),
            "errors": errors
        }
    
    async def process_single_item(self, raw: RawContent) -> Optional[ProcessedContent]:
        """Process a single raw content item."""
        
        # Calculate attractiveness score
        attractiveness_score = await self.calculate_attractiveness_score(raw)
        
        # Determine processing path
        if attractiveness_score >= 60:
            # High score: Full NLP processing
            processed = await self._process_with_nlp(raw, attractiveness_score)
        else:
            # Low score: Basic processing (snippet only)
            processed = await self._process_basic(raw, attractiveness_score)
        
        # Update raw content status
        raw.status = "processed"
        raw.processed_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return processed
    
    async def _process_with_nlp(self, raw: RawContent, score: int) -> ProcessedContent:
        """Process with full NLP (high attractiveness)."""
        
        # Get AI summary
        try:
            summary_data = await self.ai_provider.summarize(
                title=raw.original_title or "",
                content=raw.original_content or "",
                category="tech"
            )
        except Exception as e:
            # Fallback to basic if AI fails
            print(f"AI summarization failed: {e}, using basic")
            return await self._process_basic(raw, score)
        
        # Generate headline
        try:
            headline = await self.ai_provider.headline(
                title=raw.original_title or "",
                content=raw.original_content or ""
            )
        except Exception:
            headline = raw.original_title
        
        # Get source info for department tags
        source_result = await self.db.execute(
            select(Source).where(Source.id == raw.source_id)
        )
        source = source_result.scalar_one_or_none()
        
        # Create processed content
        processed = ProcessedContent(
            raw_content_id=raw.id,
            title=headline or raw.original_title or "Untitled",
            summary=summary_data.get("why_it_matters", ""),
            content_blocks={
                "hook": summary_data.get("hook", ""),
                "why_it_matters": summary_data.get("why_it_matters", ""),
                "key_points": summary_data.get("key_points", []),
                "action_step": summary_data.get("action_step", "")
            },
            reading_time_minutes=2,
            category=self._detect_category(raw),
            department_tags=source.default_categories if source else ["general"],
            topic_tags=self._extract_topics(raw),
            attractiveness_score=score,
            quality_score=min(100, score + 10),
            content_type="news",
            status="published",
            published_at=datetime.now(timezone.utc)
        )
        
        self.db.add(processed)
        await self.db.commit()
        await self.db.refresh(processed)
        
        return processed
    
    async def _process_basic(self, raw: RawContent, score: int) -> ProcessedContent:
        """Basic processing for low attractiveness (snippet only)."""
        
        # Get source info
        source_result = await self.db.execute(
            select(Source).where(Source.id == raw.source_id)
        )
        source = source_result.scalar_one_or_none()
        
        # Build a useful summary from available data
        title = raw.original_title or "Untitled"
        content = raw.original_content or ""
        metadata = raw.raw_metadata or {}
        engagement = metadata.get("engagement", {})

        # If content is just score info (e.g. "Score: 125 | Comments: 22"),
        # generate a better summary from the title and metadata
        is_score_only = content.startswith("Score:") or len(content) < 50
        if is_score_only:
            parts = []
            upvotes = engagement.get("upvotes", 0)
            comments = engagement.get("comments", 0)
            if upvotes:
                parts.append(f"{upvotes} upvotes")
            if comments:
                parts.append(f"{comments} comments")
            source_name = source.name if source else "the web"
            engagement_str = f" ({', '.join(parts)})" if parts else ""
            summary = f"Trending on {source_name}{engagement_str}. {title}."
        else:
            summary = content[:300]
            if len(content) > 300:
                summary += "..."

        processed = ProcessedContent(
            raw_content_id=raw.id,
            title=title,
            summary=summary,
            content_blocks={
                "hook": title,
                "why_it_matters": summary,
                "key_points": [],
            },
            reading_time_minutes=max(1, len(content) // 1000 + 1),
            category=self._detect_category(raw),
            department_tags=source.default_categories if source else ["general"],
            topic_tags=self._extract_topics(raw),
            attractiveness_score=score,
            quality_score=score,
            content_type="snippet",
            status="published",
            published_at=datetime.now(timezone.utc),
        )
        
        self.db.add(processed)
        await self.db.commit()
        await self.db.refresh(processed)
        
        return processed
    
    def _detect_category(self, raw: RawContent) -> str:
        """Detect content category from metadata."""
        title = (raw.original_title or "").lower()
        content = (raw.original_content or "").lower()
        
        categories = {
            "ai_ml": ["ai", "machine learning", "gpt", "llm", "neural", "deep learning"],
            "webdev": ["javascript", "react", "vue", "angular", "frontend", "web"],
            "backend": ["python", "java", "go", "rust", "backend", "server"],
            "mobile": ["ios", "android", "flutter", "react native", "mobile"],
            "devops": ["docker", "kubernetes", "ci/cd", "aws", "cloud"],
            "career": ["job", "hiring", "interview", "salary", "career"],
            "startup": ["startup", "funding", "venture", "entrepreneur"],
            "security": ["security", "vulnerability", "hack", "cve", "exploit"],
        }
        
        scores = {}
        for cat, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in title or kw in content)
            if score > 0:
                scores[cat] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return "general"
    
    def _extract_topics(self, raw: RawContent) -> List[str]:
        """Extract topic tags from content."""
        title = (raw.original_title or "").lower()
        
        # Common tech topics
        topics = []
        tech_keywords = [
            "python", "javascript", "typescript", "react", "vue", "angular",
            "nodejs", "django", "fastapi", "docker", "kubernetes", "aws",
            "ai", "machine learning", "openai", "gpt", "api", "database"
        ]
        
        for keyword in tech_keywords:
            if keyword in title:
                topics.append(keyword.replace(" ", "-"))
        
        return topics[:5]  # Max 5 topics
    
    async def get_processing_stats(self) -> Dict:
        """Get content processing statistics."""
        from sqlalchemy import func
        
        # Count by status
        result = await self.db.execute(
            select(RawContent.status, func.count(RawContent.id))
            .group_by(RawContent.status)
        )
        status_counts = dict(result.all())
        
        # Count processed content
        result = await self.db.execute(
            select(func.count(ProcessedContent.id))
        )
        processed_count = result.scalar()
        
        # Average attractiveness score
        result = await self.db.execute(
            select(func.avg(ProcessedContent.attractiveness_score))
        )
        avg_score = result.scalar() or 0
        
        return {
            "raw_content": {
                "pending": status_counts.get("pending", 0),
                "processed": status_counts.get("processed", 0),
                "failed": status_counts.get("failed", 0),
            },
            "processed_content": processed_count,
            "average_attractiveness_score": round(avg_score, 2)
        }
