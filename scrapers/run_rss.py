"""Run RSS scraper for all department sources with concurrent fetching."""
import asyncio
import hashlib
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, _root)  # for scrapers.lib imports

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from datetime import datetime, timezone
from sqlalchemy import select
from app.models.base import AsyncSessionLocal
from app.models.content import Source, RawContent
from scrapers.lib.scrapers.rss_scraper import RSSFeedScraper

# Max concurrent feed fetches (avoid overwhelming targets)
CONCURRENCY = 5


async def scrape_one_source(scraper, source, semaphore):
    """Scrape a single RSS source, guarded by semaphore."""
    config = source.scrape_config or {}
    feed_name = config.get("feed_name", source.name)
    feed_type = config.get("feed_type", "news")
    dept_tags = list(source.department_tags or [])

    async with semaphore:
        try:
            items = await scraper.scrape_feed(
                feed_url=source.url,
                feed_name=feed_name,
                feed_type=feed_type,
                limit=15,
                department_tags=dept_tags,
            )
            return source, items, None
        except Exception as e:
            return source, [], str(e)


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Source).where(Source.platform == "rss", Source.is_active == True)
        )
        sources = result.scalars().all()
        print(f"Found {len(sources)} active RSS sources")

        total_scraped = 0
        total_stored = 0
        errors = []

        semaphore = asyncio.Semaphore(CONCURRENCY)

        async with RSSFeedScraper() as scraper:
            # Launch all scrapes concurrently (bounded by semaphore)
            tasks = [scrape_one_source(scraper, s, semaphore) for s in sources]
            results = await asyncio.gather(*tasks)

        # Store results sequentially to avoid DB conflicts
        for source, items, error in results:
            config = source.scrape_config or {}
            feed_name = config.get("feed_name", source.name)
            dept_tags = list(source.department_tags or [])

            if error:
                errors.append(f"{feed_name}: {error}")
                print(f"  [ERR] {feed_name}: {error}")
                continue

            total_scraped += len(items)
            stored = 0
            seen_hashes = set()

            for item in items:
                content_str = f"{item.title}{item.url}{item.author}"
                content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:32]

                if content_hash in seen_hashes:
                    continue
                seen_hashes.add(content_hash)

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

            source.last_scraped_at = datetime.now(timezone.utc)
            source.last_success_at = datetime.now(timezone.utc)

        print(f"\nDone: {total_scraped} scraped, {total_stored} stored, {len(errors)} errors")
        if errors:
            print("Errors:")
            for err in errors:
                print(f"  - {err}")


if __name__ == "__main__":
    asyncio.run(main())
