"""Scraper service for integrating existing scrapers."""

import asyncio
import hashlib
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProcessedContent, RawContent, Source
import sys
import os

# Add scraper_platform to path
scraper_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scraper_platform')
if scraper_path not in sys.path:
    sys.path.insert(0, scraper_path)

from src.scrapers.github_scraper import GitHubScraper
from src.scrapers.hackernews_scraper import HackerNewsScraper
from src.scrapers.medium_scraper import MediumScraper
from src.scrapers.producthunt_scraper import ProductHuntScraper
from src.scrapers.reddit_scraper import RedditScraper


class ScraperService:
    """Service for running scrapers and storing results."""
    
    # Map scraper names to classes
    SCRAPERS = {
        "hackernews": HackerNewsScraper,
        "reddit": RedditScraper,
        "github": GitHubScraper,
        "medium": MediumScraper,
        "producthunt": ProductHuntScraper,
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.results = []
    
    async def ensure_sources_exist(self):
        """Ensure all scraper sources exist in database."""
        sources_config = [
            {
                "name": "Hacker News",
                "source_type": "api",
                "url": "https://hacker-news.firebaseio.com",
                "platform": "hackernews",
                "schedule_cron": "*/15 * * * *",  # Every 15 min
                "default_categories": ["tech", "startup"],
            },
            {
                "name": "Reddit",
                "source_type": "api",
                "url": "https://www.reddit.com",
                "platform": "reddit",
                "schedule_cron": "*/30 * * * *",  # Every 30 min
                "default_categories": ["tech", "career"],
            },
            {
                "name": "GitHub",
                "source_type": "api",
                "url": "https://api.github.com",
                "platform": "github",
                "schedule_cron": "0 */6 * * *",  # Every 6 hours
                "default_categories": ["opensource", "tools"],
            },
            {
                "name": "Medium",
                "source_type": "rss",
                "url": "https://medium.com",
                "platform": "medium",
                "schedule_cron": "0 */6 * * *",  # Every 6 hours
                "default_categories": ["tutorial", "career"],
            },
            {
                "name": "Product Hunt",
                "source_type": "rss",
                "url": "https://www.producthunt.com",
                "platform": "producthunt",
                "schedule_cron": "0 */12 * * *",  # Every 12 hours
                "default_categories": ["tools", "startup"],
            },
        ]
        
        for config in sources_config:
            # Check if source exists
            result = await self.db.execute(
                select(Source).where(Source.platform == config["platform"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                source = Source(**config)
                self.db.add(source)
                print(f"Created source: {config['name']}")
        
        await self.db.commit()
    
    async def run_scraper(self, scraper_name: str, **kwargs) -> Dict:
        """Run a specific scraper and store results."""
        
        if scraper_name not in self.SCRAPERS:
            return {"error": f"Unknown scraper: {scraper_name}"}
        
        scraper_class = self.SCRAPERS[scraper_name]
        items_scraped = 0
        items_stored = 0
        
        try:
            # Get source ID from database
            result = await self.db.execute(
                select(Source).where(Source.platform == scraper_name)
            )
            source = result.scalar_one_or_none()
            
            if not source:
                return {"error": f"Source not configured: {scraper_name}"}
            
            # Run scraper
            print(f"Running scraper: {scraper_name}")
            
            if scraper_name == "hackernews":
                items = await self._scrape_hackernews(source.id, **kwargs)
            elif scraper_name == "reddit":
                items = await self._scrape_reddit(source.id, **kwargs)
            elif scraper_name == "github":
                items = await self._scrape_github(source.id, **kwargs)
            elif scraper_name == "medium":
                items = await self._scrape_medium(source.id, **kwargs)
            elif scraper_name == "producthunt":
                items = await self._scrape_producthunt(source.id, **kwargs)
            else:
                items = []
            
            # Store items
            for item in items:
                stored = await self._store_raw_content(item, source.id)
                if stored:
                    items_stored += 1
            
            # Update source last scraped
            source.last_scraped_at = datetime.utcnow()
            source.last_success_at = datetime.utcnow()
            await self.db.commit()
            
            return {
                "scraper": scraper_name,
                "items_scraped": len(items),
                "items_stored": items_stored,
                "status": "success"
            }
            
        except Exception as e:
            print(f"Error running {scraper_name}: {e}")
            import traceback
            traceback.print_exc()
            
            # Update source failure count
            if source:
                source.failure_count += 1
                await self.db.commit()
            
            return {
                "scraper": scraper_name,
                "error": str(e),
                "status": "failed"
            }
    
    async def _scrape_hackernews(self, source_id: int, limit: int = 30) -> List[Dict]:
        """Scrape Hacker News."""
        items = []
        
        async with HackerNewsScraper() as scraper:
            scraped_items = await scraper.scrape(limit=limit)
            
            for item in scraped_items:
                items.append({
                    "title": item.title,
                    "url": item.url,
                    "content": item.content,
                    "author": item.author,
                    "published_at": item.published_at,
                    "source_platform": "hackernews",
                    "metadata": item.metadata,
                    "engagement": item.engagement,
                })
        
        return items
    
    async def _scrape_reddit(self, source_id: int, limit: int = 25) -> List[Dict]:
        """Scrape Reddit."""
        items = []
        
        async with RedditScraper() as scraper:
            scraped_items = await scraper.scrape(
                subreddits=['technology', 'programming', 'cscareerquestions'],
                limit=limit
            )
            
            for item in scraped_items:
                items.append({
                    "title": item.title,
                    "url": item.url,
                    "content": item.content,
                    "author": item.author,
                    "published_at": item.published_at,
                    "source_platform": "reddit",
                    "metadata": item.metadata,
                    "engagement": item.engagement,
                })
        
        return items
    
    async def _scrape_github(self, source_id: int, limit: int = 20) -> List[Dict]:
        """Scrape GitHub trending."""
        items = []
        
        async with GitHubScraper() as scraper:
            scraped_items = await scraper.scrape(
                languages=['Python', 'JavaScript', 'TypeScript'],
                limit=limit
            )
            
            for item in scraped_items:
                items.append({
                    "title": item.title,
                    "url": item.url,
                    "content": item.content,
                    "author": item.author,
                    "published_at": item.published_at,
                    "source_platform": "github",
                    "metadata": item.metadata,
                    "engagement": item.engagement,
                })
        
        return items
    
    async def _scrape_medium(self, source_id: int, limit: int = 20) -> List[Dict]:
        """Scrape Medium publications."""
        items = []
        
        scraper = MediumScraper()
        scraped_items = await scraper.scrape(limit=limit)
        
        for item in scraped_items:
            items.append({
                "title": item.title,
                "url": item.url,
                "content": item.content,
                "author": item.author,
                "published_at": item.published_at,
                "source_platform": "medium",
                "metadata": item.metadata,
                "engagement": item.engagement,
            })
        
        return items
    
    async def _scrape_producthunt(self, source_id: int, limit: int = 20) -> List[Dict]:
        """Scrape Product Hunt."""
        items = []
        
        scraper = ProductHuntScraper()
        scraped_items = await scraper.scrape(limit=limit)
        
        for item in scraped_items:
            items.append({
                "title": item.title,
                "url": item.url,
                "content": item.content,
                "author": item.author,
                "published_at": item.published_at,
                "source_platform": "producthunt",
                "metadata": item.metadata,
                "engagement": item.engagement,
            })
        
        return items
    
    async def _store_raw_content(self, item: Dict, source_id: int) -> bool:
        """Store scraped item in raw_content table."""
        
        # Generate content hash for deduplication
        content_str = f"{item['title']}{item['url']}{item.get('author', '')}"
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:32]
        
        # Check for duplicates
        result = await self.db.execute(
            select(RawContent).where(RawContent.content_hash == content_hash)
        )
        if result.scalar_one_or_none():
            return False  # Duplicate
        
        # Create raw content entry
        metadata = item.get("metadata", {})
        # Merge engagement data into metadata so scoring can use it
        engagement = item.get("engagement", {})
        if engagement:
            metadata["engagement"] = engagement

        raw = RawContent(
            source_id=source_id,
            original_url=item["url"],
            original_title=item["title"],
            original_content=item.get("content", "")[:2000],  # Truncate
            original_author=item.get("author", ""),
            published_at=item.get("published_at"),
            raw_metadata=metadata,
            content_hash=content_hash,
            status="pending"
        )
        
        self.db.add(raw)
        await self.db.flush()
        return True
    
    async def run_all_scrapers(self) -> Dict:
        """Run all scrapers."""
        results = {}
        
        for scraper_name in self.SCRAPERS.keys():
            result = await self.run_scraper(scraper_name)
            results[scraper_name] = result
        
        return results
    
    async def get_scraper_status(self) -> List[Dict]:
        """Get status of all scrapers."""
        result = await self.db.execute(select(Source))
        sources = result.scalars().all()
        
        status_list = []
        for source in sources:
            # Count pending items
            pending_result = await self.db.execute(
                select(RawContent).where(
                    RawContent.source_id == source.id,
                    RawContent.status == "pending"
                )
            )
            pending_count = len(pending_result.scalars().all())
            
            status_list.append({
                "id": str(source.id),
                "name": source.name,
                "platform": source.platform,
                "is_active": source.is_active,
                "last_scraped": source.last_scraped_at.isoformat() if source.last_scraped_at else None,
                "last_success": source.last_success_at.isoformat() if source.last_success_at else None,
                "failure_count": source.failure_count,
                "pending_items": pending_count,
                "schedule": source.schedule_cron
            })
        
        return status_list
