"""Content processing service for transforming raw to processed content."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.ai_provider import AIProvider
from app.models import ProcessedContent, RawContent, Source
from app.services.cache_service import invalidate_feed_caches
from app.services.dept_relevance import assign_departments, detect_category, score_article_departments

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Process raw scraped content into newsletter-ready format."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_provider = AIProvider()
    
    # ── Source Reputation Tiers ─────────────────────────────────────────
    # Named sources get tiered scores based on editorial quality and
    # relevance to engineering students. This replaces the flat platform bonus.
    SOURCE_REPUTATION = {
        # Tier 1 (25 pts) — Top academic, govt research, premier institutions
        "IEEE Spectrum": 25, "ACM TechNews": 25, "ISRO News": 25,
        "ArXiv CS": 25, "ArXiv AI": 25, "ArXiv ML": 25, "ArXiv CV": 25,
        "ArXiv NLP": 25, "ArXiv Robotics": 25, "ArXiv Signal Processing": 25,
        "ArXiv Systems": 25, "ArXiv Systems & Control": 25,
        "ArXiv Quantitative Biology": 25, "ArXiv Chemical Physics": 25,
        "ArXiv Astrophysics": 25, "ArXiv Space Physics": 25,
        "ArXiv Fluid Dynamics": 25, "ArXiv Geophysics": 25,
        "ArXiv Materials Science": 25, "ArXiv Applied Physics": 25,
        "ArXiv Human-Robot Interaction": 25,
        "Science Robotics": 25, "Papers With Code": 25,
        "Google AI Blog": 25, "Microsoft Research": 25, "OpenAI Blog": 25,
        "NASA Blog": 25, "IIT Madras News": 25, "DST India": 25,
        "CSIR News": 25, "Vigyan Prasar": 25, "DRDO News": 25,
        "NIST News": 25, "ASCE News": 25, "SAE International": 25,
        # Tier 2 (20 pts) — Reputed tech media, Indian career/education, govt
        "TechCrunch": 20, "Ars Technica": 20, "MIT Tech Review AI": 20,
        "The Hindu Sci-Tech": 20, "The Hindu Education": 20,
        "Indian Express Technology": 20, "Economic Times Tech": 20,
        "NPTEL Announcements": 20, "NASSCOM Blog": 20,
        "Internshala Blog": 20, "Freshersworld Blog": 20,
        "Analytics Vidhya Blog": 20, "Electronics For You": 20,
        "PIB India": 20, "ET Govt": 20, "Hugging Face Blog": 20,
        "NVIDIA Robotics Blog": 20, "VentureBeat AI": 20,
        "Krebs on Security": 20, "InfoQ": 20, "Devfolio Blog": 20,
        "Unstop Blog": 20, "The News Minute Tech": 20,
        "TOI Education": 20, "Naukri Blog": 20,
        "ETAuto": 20, "ETEnergyWorld": 20, "ETInfra": 20,
        "ET CIO": 20, "ETTelecom": 20,
        # Tier 3 (15 pts) — Quality blogs, Indian startup/tech, niche industry
        "Dev.to": 15, "GeeksforGeeks Jobs": 15, "GeeksforGeeks": 15,
        "YourStory": 15, "Inc42": 15, "MediaNama": 15, "Trak.in": 15,
        "The Wire Science": 15, "Livemint Technology": 15,
        "The Verge": 15, "ZDNet": 15, "Bleeping Computer": 15,
        "Dark Reading": 15, "Hackaday": 15, "EE Times": 15,
        "Citizen Matters Bengaluru": 15, "Citizen Matters Chennai": 15,
        "Manufacturing Today India": 15, "BioVoice News": 15,
        "Mercom India Solar": 15, "The Robot Report": 15,
        "Boston Dynamics Blog": 15, "GEN News": 15, "STAT News": 15,
        "SpaceNews": 15, "AWS Blog": 15, "Google Cloud Blog": 15,
        "Renewable Energy World": 15, "Construction Dive": 15,
        "3D Printing Industry": 15, "Engineering.com": 15,
        # Tier 4 (10 pts) — General platforms, community sources
        "Hacker News": 10, "Reddit": 10, "Medium": 10, "Product Hunt": 10,
        "GitHub Trending": 10,
    }
    # Fallback by platform for sources not in the named dict
    PLATFORM_TIER_FALLBACK = {
        "research": 20, "rss": 8, "hackernews": 10, "github": 10,
        "reddit": 7, "medium": 7, "producthunt": 7,
    }

    # Locality keywords — presence in title/content triggers multiplier
    LOCALITY_KEYWORDS = {
        "chennai", "tamil nadu", "bangalore", "bengaluru", "hyderabad",
        "coimbatore", "madurai", "kochi", "trivandrum", "mysore",
        "srm university", "srm", "anna university", "vit", "iit madras",
        "iit hyderabad", "nit trichy", "psg tech", "iiitdm", "sastra",
        "bits pilani hyderabad", "iiit bangalore",
    }

    async def calculate_attractiveness_score(self, raw: RawContent) -> int:
        """Calculate attractiveness score (0-100) for content.

        Uses source reputation tiers, capped engagement, freshness,
        content quality, and locality multipliers to prioritize content
        relevant to South Indian engineering students.
        """
        score = 0

        # Base score
        score += 15

        # ── Engagement bonus (capped at 15 total) ──
        engagement = raw.raw_metadata.get("engagement", {}) if raw.raw_metadata else {}
        engagement_pts = 0
        if engagement:
            upvotes = engagement.get("upvotes", 0)
            if upvotes > 500:
                engagement_pts += 10
            elif upvotes > 100:
                engagement_pts += 7
            elif upvotes > 50:
                engagement_pts += 4
            stars = engagement.get("stars", 0)
            if stars > 1000:
                engagement_pts += 10
            elif stars > 500:
                engagement_pts += 7
            elif stars > 100:
                engagement_pts += 4
        score += min(15, engagement_pts)

        # ── Freshness bonus (max 20) ──
        if raw.published_at:
            try:
                published = raw.published_at
                now = datetime.now(timezone.utc)
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
                age_hours = (now - published).total_seconds() / 3600
                if age_hours < 12:
                    score += 20
                elif age_hours < 24:
                    score += 16
                elif age_hours < 48:
                    score += 10
                elif age_hours < 72:
                    score += 5
            except Exception:
                pass

        # ── Content length bonus (max 15) ──
        content_length = len(raw.original_content or "")
        if content_length > 2000:
            score += 15
        elif content_length > 1000:
            score += 12
        elif content_length > 500:
            score += 8
        elif content_length > 200:
            score += 4

        # ── Source reputation tier (replaces flat platform bonus) ──
        source_result = await self.db.execute(
            select(Source).where(Source.id == raw.source_id)
        )
        source = source_result.scalar_one_or_none()
        source_name = source.name if source else ""
        source_type = source.source_type if source else ""
        platform = source.platform if source else ""

        # Named source lookup → platform fallback → 5 (unknown)
        reputation_pts = self.SOURCE_REPUTATION.get(
            source_name,
            self.PLATFORM_TIER_FALLBACK.get(platform, 5)
        )
        score += reputation_pts

        # India source type bonus (stacks with reputation)
        india_type_bonus = {
            "india-news": 4, "india-tech": 5, "india-startup": 4,
            "india-education": 6, "india-career": 8, "india-policy": 3,
            "india-industry": 4, "india-energy": 4, "india-defence": 3,
            "india-south": 8, "india-research": 7, "india-events": 8,
        }
        score += india_type_bonus.get(source_type, 0)

        # ── Locality multiplier ──
        text = ((raw.original_title or "") + " " + (raw.original_content or "")[:2000]).lower()
        locality_hits = sum(1 for kw in self.LOCALITY_KEYWORDS if kw in text)
        if locality_hits >= 3:
            score = int(score * 1.35)
        elif locality_hits >= 1:
            score = int(score * 1.2)

        # Career/opportunity source type boost
        if source_type in ("india-career", "india-events"):
            score = int(score * 1.15)

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
        
        # Invalidate feed caches when new content is processed
        if processed_count > 0:
            try:
                await invalidate_feed_caches()
                logger.info("Feed caches invalidated after processing %d items", processed_count)
            except Exception:
                logger.warning("Failed to invalidate feed caches", exc_info=True)
        
        return {
            "processed": processed_count,
            "total_pending": len(pending_items),
            "errors": errors
        }
    
    async def process_single_item(self, raw: RawContent) -> Optional[ProcessedContent]:
        """Process a single raw content item."""
        
        # Calculate attractiveness score
        attractiveness_score = await self.calculate_attractiveness_score(raw)
        
        # All articles get AI processing (score is for ranking, not gating)
        processed = await self._process_with_nlp(raw, attractiveness_score)
        
        # Update raw content status
        raw.status = "processed"
        raw.processed_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return processed
    
    async def _process_with_nlp(self, raw: RawContent, score: int) -> ProcessedContent:
        """Process with full NLP (high attractiveness)."""
        
        # Get AI summary
        try:
            detected_cat = detect_category(raw.original_title or "", raw.original_content or "")
            summary_data = await self.ai_provider.summarize(
                title=raw.original_title or "",
                content=raw.original_content or "",
                category=detected_cat or "general"
            )
        except Exception as e:
            # Fallback to basic if AI fails
            import logging as _log
            _log.getLogger(__name__).warning("AI summarization failed: %s, using basic", e)
            return await self._process_basic(raw, score)
        
        # Get source info for department tags
        source_result = await self.db.execute(
            select(Source).where(Source.id == raw.source_id)
        )
        source = source_result.scalar_one_or_none()
        source_name = source.name if source else ""
        
        # Determine department tags via content analysis (not just source tags)
        source_tags = (source.department_tags or source.default_categories) if source else []
        source_type = source.source_type if source else ""
        dept_tags = assign_departments(
            raw.original_title or "",
            raw.original_content or "",
            source_dept_tags=source_tags,
            source_type=source_type,
        )

        # Compute composite relevance_score (5-100) from multiple signals
        dept_scores = score_article_departments(
            raw.original_title or "",
            raw.original_content or "",
            source_dept_tags=source_tags,
            source_type=source_type,
        )
        max_dept_score = dept_scores[0][1] if dept_scores else 0
        # Content quality
        content_len = len(raw.original_content or "")
        _rel = 0
        if content_len >= 500: _rel += 15
        elif content_len >= 200: _rel += 10
        elif content_len >= 50: _rel += 5
        kp = summary_data.get("key_points", [])
        hook = summary_data.get("hook", "")
        if kp and len(kp) >= 2: _rel += 10
        if hook and hook != (raw.original_title or "") and len(hook) > 20: _rel += 5
        # Category specificity
        _cat = detect_category(raw.original_title or "", raw.original_content or "")
        if _cat and _cat != "general": _rel += 15
        else: _rel += 3
        # Career and opportunity content gets extra relevance
        if _cat in ("career", "opportunity"):
            _rel += 20  # High relevance for actionable career content
        # Department relevance
        _rel += min(35, int(max_dept_score * 3.5))
        # Source quality
        if score >= 50: _rel += 20
        elif score >= 40: _rel += 15
        elif score >= 30: _rel += 10
        elif score >= 20: _rel += 5
        relevance_score = max(5, min(100, _rel))

        # Determine if this is breaking newsusing quality + recency + urgency rules
        is_breaking = self._is_breaking_candidate(raw, score)
        breaking_score = self._calculate_breaking_score(raw, score) if is_breaking else None
        
        # Generate appropriate headline
        try:
            if is_breaking:
                # Use breaking news headline generator for urgent, impactful headlines
                headline = await self.ai_provider.breaking_headline(
                    title=raw.original_title or "",
                    content=raw.original_content or "",
                    source=source_name
                )
            else:
                # Use regular headline generator
                headline = await self.ai_provider.headline(
                    title=raw.original_title or "",
                    content=raw.original_content or ""
                )
        except Exception:
            import logging as _log
            _log.getLogger(__name__).warning("Headline generation failed, using original title", exc_info=True)
            headline = raw.original_title
        
        # Extract featured image from metadata (og:image from feed or scraper)
        featured_image_url = self._extract_featured_image(raw)
        image_credit = None
        
        # Determine content type
        content_type = self._detect_content_type(raw, source)

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
            category=detect_category(raw.original_title or "", raw.original_content or ""),
            department_tags=dept_tags if dept_tags else (source_tags or ["general"]),
            topic_tags=self._extract_topics(raw),
            attractiveness_score=score,
            relevance_score=relevance_score,
            quality_score=min(100, score + 10),
            content_type=content_type,
            status="published",
            published_at=datetime.now(timezone.utc),
            is_breaking=is_breaking,
            breaking_score=breaking_score,
            breaking_detected_at=datetime.now(timezone.utc) if is_breaking else None,
            featured_image_url=featured_image_url,
            visualizations={"image_credit": image_credit} if image_credit else {},
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

        # Even in basic mode, keep media and breaking metadata consistent.
        is_breaking = self._is_breaking_candidate(raw, score)
        breaking_score = self._calculate_breaking_score(raw, score) if is_breaking else None
        content_type = self._detect_content_type(raw, source)

        # For research papers, create a better summary
        if content_type == "research_paper":
            metadata = raw.raw_metadata or {}
            venue = metadata.get("venue", "")
            citations = metadata.get("citations", 0)
            authors = (raw.original_author or "")[:100]
            parts = []
            if authors:
                parts.append(f"By {authors}")
            if venue:
                parts.append(f"Published in {venue}")
            if citations:
                parts.append(f"{citations} citations")
            meta_line = " | ".join(parts)
            abstract = (raw.original_content or "")[:300]
            summary = f"{meta_line}. {abstract}" if meta_line else abstract

        featured_image_url = self._extract_featured_image(raw)
        image_credit = None

        # Assign departments via content analysis
        source_tags = (source.department_tags or source.default_categories) if source else []
        source_type = source.source_type if source else ""
        dept_tags = assign_departments(
            title, content,
            source_dept_tags=source_tags,
            source_type=source_type,
        )

        # Compute composite relevance_score (5-100) from multiple signals
        dept_scores = score_article_departments(
            title, content,
            source_dept_tags=source_tags,
            source_type=source_type,
        )
        max_dept_score = dept_scores[0][1] if dept_scores else 0
        content_len = len(content)
        _rel = 0
        if content_len >= 500: _rel += 15
        elif content_len >= 200: _rel += 10
        elif content_len >= 50: _rel += 5
        _cat = detect_category(title, content)
        if _cat and _cat != "general": _rel += 15
        else: _rel += 3
        # Career and opportunity content gets extra relevance
        if _cat in ("career", "opportunity"):
            _rel += 20  # High relevance for actionable career content
        _rel += min(35, int(max_dept_score * 3.5))
        if score >= 50: _rel += 20
        elif score >= 40: _rel += 15
        elif score >= 30: _rel += 10
        elif score >= 20: _rel += 5
        relevance_score = max(5, min(100, _rel))

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
            category=detect_category(title, content),
            department_tags=dept_tags if dept_tags else (source_tags or ["general"]),
            topic_tags=self._extract_topics(raw),
            attractiveness_score=score,
            relevance_score=relevance_score,
            quality_score=score,
            content_type=content_type if content_type == "research_paper" else "snippet",
            status="published",
            published_at=datetime.now(timezone.utc),
            is_breaking=is_breaking,
            breaking_score=breaking_score,
            breaking_detected_at=datetime.now(timezone.utc) if is_breaking else None,
            featured_image_url=featured_image_url,
            visualizations={"image_credit": image_credit} if image_credit else {},
        )
        
        self.db.add(processed)
        await self.db.commit()
        await self.db.refresh(processed)
        
        return processed

    def _content_age_hours(self, raw: RawContent) -> Optional[float]:
        """Get content age in hours from published/scraped timestamp."""
        dt = raw.published_at or raw.scraped_at
        if not dt:
            return None

        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return max(0.0, (now - dt).total_seconds() / 3600)

    def _has_urgent_keywords(self, raw: RawContent) -> bool:
        """Detect urgent/breaking signals in text using specific, high-signal event terms."""
        text = f"{raw.original_title or ''} {raw.original_content or ''}".lower()
        keywords = [
            "breaking",
            "just announced",
            "outage",
            "urgent",
            "security flaw",
            "data breach",
            "zero-day",
            "vulnerability",
            "exploit",
            "acquires",
            "banned",
            "lawsuit",
            "recall",
            "emergency",
            "shutdown",
            "offline",
            "hacked",
            "launch",
            "release",
            "unveils",
            "announces",
            "critical",
            "alert",
            "leaked",
            "disruption",
            "acquisition",
            "ipo",
            "layoff",
            "raises",
        ]
        return any(k in text for k in keywords)

    def _is_breaking_candidate(self, raw: RawContent, score: int) -> bool:
        """Decide if a story should be marked as breaking.

        Uses achievable score thresholds (max score ~55 from RSS feeds).
        """
        age_hours = self._content_age_hours(raw)
        if age_hours is None or age_hours > 48:
            return False

        # Tier 1: Top-scoring + recent
        if score >= 48 and age_hours <= 12:
            return True
        # Tier 2: Good score + very fresh
        if score >= 40 and age_hours <= 6:
            return True
        # Tier 3: Decent score + fresh + urgent keywords
        if score >= 35 and age_hours <= 24 and self._has_urgent_keywords(raw):
            return True

        return False

    def _calculate_breaking_score(self, raw: RawContent, score: int) -> int:
        """Calculate weighted breaking score for ranking."""
        age_hours = self._content_age_hours(raw)
        boost = 0

        if age_hours is not None:
            if age_hours <= 1:
                boost += 25
            elif age_hours <= 3:
                boost += 20
            elif age_hours <= 6:
                boost += 15
            elif age_hours <= 12:
                boost += 10
            elif age_hours <= 24:
                boost += 5

        if self._has_urgent_keywords(raw):
            boost += 10

        return min(100, score + boost)
    
    def _detect_content_type(self, raw: RawContent, source) -> str:
        """Detect if content is a research paper based on source and metadata."""
        metadata = raw.raw_metadata or {}
        # Explicitly tagged by scraper
        if metadata.get("content_type") == "research_paper":
            return "research_paper"
        # From research platform
        if source and source.platform == "research":
            return "research_paper"
        # ArXiv source
        url = (raw.original_url or "").lower()
        if "arxiv.org" in url:
            return "research_paper"
        return "news"

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
    
    def _extract_featured_image(self, raw: RawContent) -> Optional[str]:
        """Extract featured image URL from metadata.
        
        Checks for common Open Graph and Twitter Card image meta tags.
        """
        metadata = raw.raw_metadata or {}
        
        # Check for Open Graph image
        if "og_image" in metadata:
            return metadata["og_image"]
        if "og:image" in metadata:
            return metadata["og:image"]
        
        # Check for Twitter Card image
        if "twitter_image" in metadata:
            return metadata["twitter_image"]
        if "twitter:image" in metadata:
            return metadata["twitter:image"]
        if "twitter:image:src" in metadata:
            return metadata["twitter:image:src"]
        
        # Check for other common image fields
        if "image" in metadata:
            return metadata["image"]
        if "thumbnail" in metadata:
            return metadata["thumbnail"]
        if "featured_image" in metadata:
            return metadata["featured_image"]
        
        # Check in external_url metadata for Reddit/HN
        external_url = metadata.get("external_url", "")
        if external_url and ("youtube.com" in external_url or "youtu.be" in external_url):
            # YouTube videos - could extract thumbnail if needed
            pass
        
        return None

    async def _fetch_semantic_image(self, title: Optional[str], category: str = "general") -> Optional[dict]:
        """Fetch a semantically relevant image for the article title.
        
        Uses semantic search first, then falls back to category-based search.
        Returns dict with 'url' and 'credit' keys, or None.
        """
        if not title or len(title.strip()) < 5:
            return None
        try:
            from app.services.image_fetcher import ImageFetcher
            fetcher = ImageFetcher(sources=["openverse", "wikimedia"])
            result = await fetcher.fetch_with_fallback(title, category=category, top_k=1)
            if result and result.get("url"):
                # Build attribution credit line
                creator = result.get("creator", "").strip()
                provider = result.get("provider", "").strip()
                lic = result.get("license", "").strip()
                source_url = result.get("source_url", "").strip()
                parts = []
                if creator:
                    parts.append(creator)
                if provider:
                    parts.append(provider.title())
                credit = " / ".join(parts) if parts else provider
                if lic:
                    credit += f" ({lic})"
                return {
                    "url": result["url"],
                    "credit": credit,
                    "source_url": source_url,
                    "provider": provider,
                    "license": lic,
                }
        except Exception:
            logger.debug("Semantic image fetch failed for: %s", title, exc_info=True)
        return None
    
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
