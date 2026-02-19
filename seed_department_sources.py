#!/usr/bin/env python
"""Seed the sources table with department-specific sources from the registry."""

import asyncio
import sys
import os

_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_root, "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from app.departments import DEPARTMENTS, DEPARTMENT_SOURCES
from app.models.base import AsyncSessionLocal, engine, Base
from app.models.content import Source


async def seed():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        created = 0
        for dept in DEPARTMENTS:
            key = dept["key"]
            sources = DEPARTMENT_SOURCES.get(key, {})

            # Seed Reddit sources
            for sub in sources.get("reddit", []):
                src = Source(
                    name=f"Reddit r/{sub}",
                    source_type="community",
                    url=f"https://www.reddit.com/r/{sub}/.json",
                    platform="reddit",
                    scrape_config={"subreddit": sub, "limit": 15},
                    schedule_cron="*/30 * * * *",
                    default_categories=[key],
                    default_tags=["reddit", sub.lower()],
                    department_tags=[key],
                    is_active=True,
                )
                db.add(src)
                created += 1

            # Seed RSS sources
            for feed in sources.get("rss", []):
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
                created += 1

        await db.commit()
        print(f"Seeded {created} sources across {len(DEPARTMENTS)} departments.")


if __name__ == "__main__":
    asyncio.run(seed())
