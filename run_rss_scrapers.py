"""Run RSS scraper for all department sources and store results."""
import asyncio
import hashlib
import json
import sys
import os

_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, os.path.join(_root, "scraper_platform"))

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from datetime import datetime
from sqlalchemy import select
from app.models.base import AsyncSessionLocal
from app.models.content import Source, RawContent
from src.scrapers.rss_scraper import RSSFeedScraper


async def main():
    async with AsyncSessionLocal() as db:
        # Get all active RSS sources grouped by department
        result = await db.execute(
            select(Source).where(Source.platform == "rss", Source.is_active == True)
        )
        sources = result.scalars().all()
        print(f"Found {len(sources)} RSS sources")

        total_scraped = 0
        total_stored = 0
        errors = []

        async with RSSFeedScraper() as scraper:
            for source in sources:
                config = source.scrape_config or {}
                feed_name = config.get("feed_name", source.name)
                feed_type = config.get("feed_type", "news")
                dept_tags = list(source.department_tags or [])

                try:
                    items = await scraper.scrape_feed(
                        feed_url=source.url,
                        feed_name=feed_name,
                        feed_type=feed_type,
                        limit=15,
                        department_tags=dept_tags,
                    )
                    total_scraped += len(items)

                    # Store items as raw_content
                    stored = 0
                    for item in items:
                        content_str = f"{item.title}{item.url}{item.author}"
                        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:32]

                        # Check duplicate
                        dup = await db.execute(
                            select(RawContent).where(RawContent.content_hash == content_hash)
                        )
                        if dup.scalar_one_or_none():
                            continue

                        raw = RawContent(
                            source_id=source.id,
                            original_url=item.url[:500] if item.url else "",
                            original_title=(item.title or "")[:500],
                            original_content=(item.content or "")[:2000],
                            original_author=(item.author or "")[:255],
                            published_at=item.published_at,
                            raw_metadata={"feed_name": feed_name, "department_tags": dept_tags},
                            content_hash=content_hash,
                            status="pending",
                        )
                        db.add(raw)
                        stored += 1

                    await db.commit()
                    total_stored += stored
                    dept_str = ",".join(dept_tags) if dept_tags else "none"
                    print(f"  [{dept_str}] {feed_name}: {len(items)} scraped, {stored} new")

                    # Update source metadata
                    source.last_scraped_at = datetime.utcnow()
                    source.last_success_at = datetime.utcnow()

                except Exception as e:
                    await db.rollback()
                    errors.append(f"{feed_name}: {e}")
                    print(f"  [ERR] {feed_name}: {e}")

        print(f"\nDone: {total_scraped} scraped, {total_stored} stored, {len(errors)} errors")
        if errors:
            print("Errors:")
            for err in errors:
                print(f"  - {err}")


if __name__ == "__main__":
    asyncio.run(main())

    # Refresh feed cache after scraping
    print("\nRefreshing feed cache...")
    from refresh_feed_cache import refresh_all
    asyncio.run(refresh_all())
