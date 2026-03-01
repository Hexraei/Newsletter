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

        # Seed platform sources (hackernews, github, medium, producthunt)
        # These are looked up by platform name in ScraperService.run_scraper()
        platform_sources = [
            {
                "name": "Hacker News",
                "platform": "hackernews",
                "url": "https://hacker-news.firebaseio.com/v0",
                "source_type": "tech",
                "scrape_config": {"limit": 30},
                "schedule_cron": "0 */6 * * *",
                "default_categories": ["technology"],
                "default_tags": ["hackernews", "tech"],
                "department_tags": ["technology"],
            },
            {
                "name": "GitHub Trending",
                "platform": "github",
                "url": "https://github.com/trending",
                "source_type": "tech",
                "scrape_config": {"limit": 20},
                "schedule_cron": "0 */6 * * *",
                "default_categories": ["technology"],
                "default_tags": ["github", "opensource"],
                "department_tags": ["technology"],
            },
            {
                "name": "Medium",
                "platform": "medium",
                "url": "https://medium.com",
                "source_type": "blog",
                "scrape_config": {"limit": 20},
                "schedule_cron": "0 */6 * * *",
                "default_categories": ["general"],
                "default_tags": ["medium", "blog"],
                "department_tags": [],
            },
            {
                "name": "Product Hunt",
                "platform": "producthunt",
                "url": "https://www.producthunt.com",
                "source_type": "tech",
                "scrape_config": {"limit": 20},
                "schedule_cron": "0 */6 * * *",
                "default_categories": ["technology"],
                "default_tags": ["producthunt", "startups"],
                "department_tags": ["technology"],
            },
        ]
        platform_created = 0
        async with AsyncSessionLocal() as db2:
            result2 = await db2.execute(select(Source.platform))
            existing_platforms = {row[0] for row in result2.all()}
            for ps in platform_sources:
                if ps["platform"] in existing_platforms:
                    continue
                src = Source(
                    name=ps["name"],
                    source_type=ps["source_type"],
                    url=ps["url"],
                    platform=ps["platform"],
                    scrape_config=ps["scrape_config"],
                    schedule_cron=ps["schedule_cron"],
                    default_categories=ps["default_categories"],
                    default_tags=ps["default_tags"],
                    department_tags=ps["department_tags"],
                    is_active=True,
                )
                db2.add(src)
                platform_created += 1
            await db2.commit()
        print(f"Seeded {platform_created} platform sources (hackernews/github/medium/producthunt).")


if __name__ == "__main__":
    asyncio.run(seed())
