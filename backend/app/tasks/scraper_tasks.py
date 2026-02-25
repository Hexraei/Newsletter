"""Celery tasks for running scrapers."""

import logging
from celery import Celery
from celery.schedules import crontab

from app.config import settings
from app.models.base import AsyncSessionLocal
from app.services.scraper_service import ScraperService

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "newsletter",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes
    worker_prefetch_multiplier=1,
)

# Schedule tasks
celery_app.conf.beat_schedule = {
    "scrape-hackernews": {
        "task": "app.tasks.scraper_tasks.scrape_hackernews",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "scrape-reddit": {
        "task": "app.tasks.scraper_tasks.scrape_reddit",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    "scrape-twitter": {
        "task": "app.tasks.scraper_tasks.scrape_twitter",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    "scrape-github": {
        "task": "app.tasks.scraper_tasks.scrape_github",
        "schedule": crontab(minute="0", hour="*/6"),  # Every 6 hours
    },
    "scrape-medium": {
        "task": "app.tasks.scraper_tasks.scrape_medium",
        "schedule": crontab(minute="0", hour="*/6"),  # Every 6 hours
    },
    "scrape-producthunt": {
        "task": "app.tasks.scraper_tasks.scrape_producthunt",
        "schedule": crontab(minute="0", hour="*/12"),  # Every 12 hours
    },
    "process-pending-content": {
        "task": "app.tasks.scraper_tasks.process_pending_content",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}


async def get_db():
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@celery_app.task(bind=True, max_retries=3)
def scrape_hackernews(self):
    """Scrape Hacker News."""
    import asyncio
    
    async def _scrape():
        async with AsyncSessionLocal() as db:
            service = ScraperService(db)
            await service.ensure_sources_exist()
            result = await service.run_scraper("hackernews")
            return result
    
    try:
        return asyncio.run(_scrape())
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def scrape_reddit(self):
    """Scrape Reddit."""
    import asyncio
    
    async def _scrape():
        async with AsyncSessionLocal() as db:
            service = ScraperService(db)
            await service.ensure_sources_exist()
            result = await service.run_scraper("reddit")
            return result
    
    try:
        return asyncio.run(_scrape())
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def scrape_twitter(self):
    """Scrape Twitter/X via bird CLI."""
    import asyncio

    async def _scrape():
        async with AsyncSessionLocal() as db:
            service = ScraperService(db)
            await service.ensure_sources_exist()
            result = await service.run_scraper("twitter")
            return result

    try:
        return asyncio.run(_scrape())
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def scrape_github(self):
    """Scrape GitHub."""
    import asyncio
    
    async def _scrape():
        async with AsyncSessionLocal() as db:
            service = ScraperService(db)
            await service.ensure_sources_exist()
            result = await service.run_scraper("github")
            return result
    
    try:
        return asyncio.run(_scrape())
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def scrape_medium(self):
    """Scrape Medium."""
    import asyncio
    
    async def _scrape():
        async with AsyncSessionLocal() as db:
            service = ScraperService(db)
            await service.ensure_sources_exist()
            result = await service.run_scraper("medium")
            return result
    
    try:
        return asyncio.run(_scrape())
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def scrape_producthunt(self):
    """Scrape Product Hunt."""
    import asyncio
    
    async def _scrape():
        async with AsyncSessionLocal() as db:
            service = ScraperService(db)
            await service.ensure_sources_exist()
            result = await service.run_scraper("producthunt")
            return result
    
    try:
        return asyncio.run(_scrape())
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True)
def scrape_all(self):
    """Run all scrapers."""
    import asyncio
    
    async def _scrape_all():
        async with AsyncSessionLocal() as db:
            service = ScraperService(db)
            await service.ensure_sources_exist()
            result = await service.run_all_scrapers()
            return result
    
    return asyncio.run(_scrape_all())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_pending_content(self):
    """Process pending raw content with retry on failure."""
    import asyncio
    
    async def _process():
        async with AsyncSessionLocal() as db:
            from app.services.content_processor import ContentProcessor
            
            processor = ContentProcessor(db)
            result = await processor.process_pending_items(limit=10)
            return result
    
    try:
        return asyncio.run(_process())
    except Exception as e:
        logger.error("process_pending_content failed (attempt %d): %s", self.request.retries + 1, e)
        raise self.retry(exc=e)


# Manual trigger endpoint helpers
async def trigger_scraper(scraper_name: str) -> dict:
    """Manually trigger a scraper."""
    async with AsyncSessionLocal() as db:
        service = ScraperService(db)
        await service.ensure_sources_exist()
        result = await service.run_scraper(scraper_name)
        return result


async def trigger_all_scrapers() -> dict:
    """Manually trigger all scrapers."""
    async with AsyncSessionLocal() as db:
        service = ScraperService(db)
        await service.ensure_sources_exist()
        result = await service.run_all_scrapers()
        return result
