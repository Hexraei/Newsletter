#!/usr/bin/env python
"""Backfill images for articles by fetching OG images from article URLs.

Fetches each article's original URL and extracts the og:image meta tag —
these are the article's own cover images, so they're always relevant.

Usage: python scrapers/fetch_images.py [--limit 200] [--workers 10]
"""

import asyncio
import argparse
import re
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, _root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

import httpx

_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property=["\']og:image["\']|name=["\']og:image["\'])[^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_OG_IMAGE_RE2 = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property=["\']og:image["\']|name=["\']og:image["\'])',
    re.IGNORECASE,
)
_TWITTER_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property=["\']twitter:image["\']|name=["\']twitter:image["\'])[^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def extract_og_image(html: str) -> str:
    """Extract og:image or twitter:image URL from HTML."""
    for pattern in (_OG_IMAGE_RE, _OG_IMAGE_RE2, _TWITTER_IMAGE_RE):
        m = pattern.search(html)
        if m:
            url = m.group(1).strip()
            if url.startswith("http") and not url.endswith(".svg"):
                return url
    return ""


async def fetch_og_image(client: httpx.AsyncClient, url: str) -> str:
    """Fetch article URL and extract og:image. Returns empty string on failure."""
    try:
        resp = await client.get(url, timeout=8, follow_redirects=True)
        if resp.status_code != 200:
            return ""
        # Only read first 8KB — og:image is always in <head>
        html = resp.text[:8192]
        return extract_og_image(html)
    except Exception:
        return ""


async def backfill_images(limit: int = 200, workers: int = 8):
    """Fetch og:image for articles missing featured_image_url."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, func, update, text
    import uuid

    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Import models after engine is ready
    sys.path.insert(0, os.path.join(_root, "backend"))
    from app.models import ProcessedContent, RawContent

    # Step 1: Fetch article data
    async with Session() as db:
        count_result = await db.execute(
            select(func.count(ProcessedContent.id))
            .where(ProcessedContent.featured_image_url.is_(None))
            .where(ProcessedContent.status == "published")
        )
        total_missing = count_result.scalar() or 0
        print(f"Articles missing images: {total_missing}")
        print(f"Processing up to {limit} articles with {workers} workers\n")

        result = await db.execute(
            select(ProcessedContent.id, ProcessedContent.title, RawContent.original_url)
            .join(RawContent, RawContent.id == ProcessedContent.raw_content_id)
            .where(ProcessedContent.featured_image_url.is_(None))
            .where(ProcessedContent.status == "published")
            .where(RawContent.original_url.isnot(None))
            .order_by(ProcessedContent.attractiveness_score.desc())
            .limit(limit)
        )
        rows = [(str(r.id), r.title, r.original_url) for r in result.all()]

    if not rows:
        print("No articles need images!")
        await engine.dispose()
        return

    # Step 2: Fetch OG images (no DB connection held open)
    semaphore = asyncio.Semaphore(workers)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    results = {}

    async def process_one(article_id, title, url):
        async with semaphore:
            img = await fetch_og_image(client, url)
            if img:
                results[article_id] = img
                print(f"  [OK] {title[:70]}")
                print(f"       {img[:80]}")
            else:
                print(f"  [--] {title[:70]}")

    print(f"Fetching OG images from {len(rows)} article URLs...")
    async with httpx.AsyncClient(headers=headers, timeout=8) as client:
        for i in range(0, len(rows), 20):
            batch = rows[i:i + 20]
            bn = i // 20 + 1
            tb = (len(rows) + 19) // 20
            print(f"--- Batch {bn}/{tb} ---")
            await asyncio.gather(*[process_one(aid, t, u) for aid, t, u in batch])
            print()

    # Step 3: Save results in batches
    if not results:
        print("No images found.")
        await engine.dispose()
        return

    updated = 0
    async with Session() as db:
        ids = list(results.keys())
        for i in range(0, len(ids), 50):
            batch_ids = ids[i:i + 50]
            for article_id in batch_ids:
                await db.execute(
                    update(ProcessedContent)
                    .where(ProcessedContent.id == uuid.UUID(article_id))
                    .values(featured_image_url=results[article_id])
                )
                updated += 1
            await db.commit()

    await engine.dispose()
    print(f"\nDone! Updated: {updated}, No image found: {len(rows) - updated}")
    print(f"Remaining without images: {total_missing - updated}")


def main():
    parser = argparse.ArgumentParser(description="Backfill OG images for articles")
    parser.add_argument("--limit", type=int, default=200, help="Max articles to process")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent HTTP workers")
    args = parser.parse_args()
    asyncio.run(backfill_images(limit=args.limit, workers=args.workers))


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
