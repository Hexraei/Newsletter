#!/usr/bin/env python
"""Run the full scraper pipeline: seed → scrape RSS → scrape research → process → cache.

Usage: python scrapers/run_all.py [--skip-seed] [--skip-research]
"""

import asyncio
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, _root)  # for scrapers.lib imports

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from app.models.base import AsyncSessionLocal
from app.services.content_processor import ContentProcessor


async def process_pending():
    """Process all pending content in batches of 50."""
    print("\n" + "=" * 60)
    print("PROCESSING PENDING CONTENT")
    print("=" * 60)
    total = 0
    async with AsyncSessionLocal() as db:
        cp = ContentProcessor(db)
        while True:
            r = await cp.process_pending_items(limit=50)
            batch = r.get("processed", 0)
            total += batch
            if batch > 0:
                print(f"  Processed batch: {batch} items (total: {total})")
            if batch == 0:
                break
    print(f"  Total processed: {total}")


async def main():
    skip_seed = "--skip-seed" in sys.argv
    skip_research = "--skip-research" in sys.argv

    # Step 1: Seed sources
    if not skip_seed:
        print("=" * 60)
        print("STEP 1: SEEDING SOURCES")
        print("=" * 60)
        from scrapers.seed_sources import seed
        await seed()
    else:
        print("Skipping seed (--skip-seed)")

    # Step 2: Scrape RSS feeds
    print("\n" + "=" * 60)
    print("STEP 2: SCRAPING RSS FEEDS")
    print("=" * 60)
    from scrapers.run_rss import main as rss_main
    await rss_main()

    # Step 3: Scrape research papers
    if not skip_research:
        from scrapers.run_research import main as research_main
        await research_main()
    else:
        print("\nSkipping research (--skip-research)")

    # Step 4: Process pending content
    await process_pending()

    # Step 5: Refresh cache
    print("\n" + "=" * 60)
    print("STEP 5: REFRESHING FEED CACHE")
    print("=" * 60)
    from scrapers.refresh_cache import refresh_all
    await refresh_all()

    print("\n" + "=" * 60)
    print("ALL DONE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
