#!/usr/bin/env python
"""Pre-compute feed sections for every department and cache in DB.

Run this after scraping to ensure instant page loads.
Usage: python refresh_feed_cache.py
"""

import asyncio
import json
import sys
import os

_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, os.path.join(_root, "scraper_platform"))

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from sqlalchemy import text
from app.models.base import AsyncSessionLocal, engine
from app.services.feed_service import FeedService
from app.departments import DEPARTMENTS

BREAKING_LIMIT = 8
TRENDING_LIMIT = 3
DEPARTMENT_LIMIT = 3


def _serialise(obj):
    """JSON-safe serialiser for UUIDs, datetimes, etc."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "hex"):
        return str(obj)
    raise TypeError(f"Cannot serialise {type(obj)}")


async def build_section(dept_key: str) -> dict:
    """Compute all-sections payload for one department."""
    async with AsyncSessionLocal() as db:
        svc = FeedService(db)
        breaking = await svc.get_breaking_news(limit=BREAKING_LIMIT, department=dept_key)
        trending = await svc.get_trending_content(limit=TRENDING_LIMIT, department=dept_key)
        dept_feed = await svc.get_personalized_feed(department=dept_key, limit=DEPARTMENT_LIMIT)
        dept_items = dept_feed.get("items", [])
    return {
        "breaking": breaking,
        "department": dept_items,
        "trending": trending,
    }


async def refresh_all():
    dept_keys = [d["key"] for d in DEPARTMENTS]
    print(f"Refreshing cache for {len(dept_keys)} departments...")

    for key in dept_keys:
        try:
            data = await build_section(key)
            payload = json.loads(json.dumps(data, default=_serialise))

            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(
                        "INSERT INTO cached_feeds (department, data, updated_at) "
                        "VALUES (:d, :data, NOW()) "
                        "ON CONFLICT (department) DO UPDATE "
                        "SET data = EXCLUDED.data, updated_at = NOW()"
                    ),
                    {"d": key, "data": json.dumps(payload)},
                )
                await db.commit()

            b = len(data["breaking"])
            t = len(data["trending"])
            d = len(data["department"])
            print(f"  {key}: breaking={b} trending={t} department={d}")
        except Exception as e:
            print(f"  {key}: ERROR - {e}")

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(refresh_all())
