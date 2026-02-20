#!/usr/bin/env python
"""Seed the sources table with department-specific sources from the registry."""

import asyncio
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from app.departments import (
    DEPARTMENTS, DEPARTMENT_SOURCES,
    get_all_rss_feeds_for_department,
    get_all_reddit_subs_for_department,
)
from app.models.base import AsyncSessionLocal, engine, Base
from app.models.content import Source


async def seed():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Collect existing source URLs to avoid duplicates
        from sqlalchemy import select
        result = await db.execute(select(Source.url))
        existing_urls = {row[0] for row in result.all()}

        created = 0
        for dept in DEPARTMENTS:
            key = dept["key"]

            # Seed Reddit sources (includes India subs)
            for sub in get_all_reddit_subs_for_department(key):
                url = f"https://www.reddit.com/r/{sub}/.json"
                if url in existing_urls:
                    continue
                src = Source(
                    name=f"Reddit r/{sub}",
                    source_type="community",
                    url=url,
                    platform="reddit",
                    scrape_config={"subreddit": sub, "limit": 15},
                    schedule_cron="*/30 * * * *",
                    default_categories=[key],
                    default_tags=["reddit", sub.lower()],
                    department_tags=[key],
                    is_active=True,
                )
                db.add(src)
                existing_urls.add(url)
                created += 1

            # Seed RSS sources (includes India common + dept-specific)
            for feed in get_all_rss_feeds_for_department(key):
                if feed["url"] in existing_urls:
                    continue
                src = Source(
                    name=feed["name"],
                    source_type=feed.get("type", "news"),
                    url=feed["url"],
                    platform="rss",
                    scrape_config={"feed_name": feed["name"], "feed_type": feed.get("type", "news")},
                    schedule_cron="0 */6 * * *",
                    default_categories=[key],
                    default_tags=["rss", feed.get("type", "news")],
                    department_tags=[key],
                    is_active=True,
                )
                db.add(src)
                existing_urls.add(feed["url"])
                created += 1

        await db.commit()
        print(f"Seeded {created} new sources across {len(DEPARTMENTS)} departments.")


if __name__ == "__main__":
    asyncio.run(seed())
