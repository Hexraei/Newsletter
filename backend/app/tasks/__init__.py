"""Celery tasks for background jobs."""

from app.tasks.scraper_tasks import (
    celery_app,
    process_pending_content,
    scrape_all,
    scrape_github,
    scrape_hackernews,
    scrape_medium,
    scrape_producthunt,
    scrape_reddit,
)

__all__ = [
    "celery_app",
    "scrape_hackernews",
    "scrape_reddit",
    "scrape_github",
    "scrape_medium",
    "scrape_producthunt",
    "scrape_all",
    "process_pending_content",
]
