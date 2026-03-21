#!/usr/bin/env python
"""Pre-compute feed sections for every department and cache in DB.

Run this after scraping to ensure instant page loads.
Usage: python scrapers/refresh_cache.py
"""

import asyncio
import json
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, _root)  # for scrapers.lib imports

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from sqlalchemy import text
from app.models.base import AsyncSessionLocal, engine
from app.services.feed_service import FeedService
from app.departments import DEPARTMENTS

BREAKING_LIMIT = 12
TRENDING_LIMIT = 14
DEPARTMENT_LIMIT = 14
CAREER_LIMIT = 10
RESEARCH_FEATURED = 4
RESEARCH_GENERAL = 10


def _serialise(obj):
    """JSON-safe serialiser for UUIDs, datetimes, etc."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "hex"):
        return str(obj)
    raise TypeError(f"Cannot serialise {type(obj)}")


def _is_sqlite() -> bool:
    return str(engine.url).startswith("sqlite")


async def _ensure_cache_table() -> None:
    """Create cached_feeds table when running in local SQLite mode."""
    if not _is_sqlite():
        return
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS cached_feeds (
                    department TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        await db.commit()


async def build_section(dept_key: str) -> dict:
    """Compute all-sections payload for one department."""
    async with AsyncSessionLocal() as db:
        svc = FeedService(db)
        breaking = await svc.get_breaking_news(limit=BREAKING_LIMIT, department=dept_key)
        trending = await svc.get_trending_content(limit=TRENDING_LIMIT, department=dept_key)
        dept_feed = await svc.get_personalized_feed(department=dept_key, limit=DEPARTMENT_LIMIT)
        dept_items = dept_feed.get("items", [])
        career = await svc.get_career_content(limit=CAREER_LIMIT, department=dept_key)
        research = await svc.get_research_papers(
            department=dept_key, featured_limit=RESEARCH_FEATURED, general_limit=RESEARCH_GENERAL
        )
    return {
        "breaking": breaking,
        "department": dept_items,
        "trending": trending,
        "career": career,
        "research_papers": research,
    }


async def refresh_all():
    dept_keys = [d["key"] for d in DEPARTMENTS]
    print(f"Refreshing cache for {len(dept_keys)} departments...")
    await _ensure_cache_table()

    for key in dept_keys:
        try:
            data = await build_section(key)
            payload = json.loads(json.dumps(data, default=_serialise))

            async with AsyncSessionLocal() as db:
                if _is_sqlite():
                    await db.execute(
                        text(
                            "INSERT INTO cached_feeds (department, data, updated_at) "
                            "VALUES (:d, :data, CURRENT_TIMESTAMP) "
                            "ON CONFLICT(department) DO UPDATE "
                            "SET data = excluded.data, updated_at = CURRENT_TIMESTAMP"
                        ),
                        {"d": key, "data": json.dumps(payload)},
                    )
                else:
                    await db.execute(
                        text(
                            "INSERT INTO cached_feeds (department, data, updated_at) "
                            "VALUES (:d, CAST(:data AS JSONB), NOW()) "
                            "ON CONFLICT (department) DO UPDATE "
                            "SET data = EXCLUDED.data, updated_at = NOW()"
                        ),
                        {"d": key, "data": json.dumps(payload)},
                    )
                await db.commit()

            b = len(data["breaking"])
            t = len(data["trending"])
            d = len(data["department"])
            c = len(data["career"])
            print(f"  {key}: breaking={b} trending={t} department={d} career={c}")
        except Exception as e:
            print(f"  {key}: ERROR - {e}")

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(refresh_all())
