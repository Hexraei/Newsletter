#!/usr/bin/env python
"""Backfill images for articles.

Phase 1 (OG image): Fetches each article's original URL and extracts og:image.
Phase 2 (stock photo): For articles still missing images, searches Unsplash / Pexels /
                        Openverse (free, no key needed) using the article title as query.

Usage: python scrapers/fetch_images.py [--limit 200] [--workers 10]

Set keys in backend/.env to activate Unsplash/Pexels:
  UNSPLASH_ACCESS_KEY=...   (https://unsplash.com/developers — free, 50 req/hr)
  PEXELS_API_KEY=...        (https://www.pexels.com/api/ — free, 200 req/hr)
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
        html = resp.text[:8192]  # og:image is always in <head>, first 8KB is enough
        return extract_og_image(html)
    except Exception:
        return ""


def _stock_query(title: str, category: str = "") -> str:
    """Build a 2-3 word stock photo search query from article title + category.

    Uses just 2 title words + 1 category context word.
    Simpler queries work better with image search APIs.
    """
    stop = {
        "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is",
        "are", "was", "were", "has", "have", "how", "why", "what", "when", "where",
        "it", "its", "this", "that", "with", "by", "as", "if", "be", "not", "now",
        "new", "just", "will", "can", "get", "all", "more", "over", "per", "vs",
        "via", "says", "their", "your", "our", "from", "into", "about", "than",
        "still", "after", "before", "same", "year", "years", "day", "days", "week",
        "work", "find", "think", "make", "does", "want", "need", "best", "good",
        "using", "ever", "only", "also", "even", "both", "here", "there",
    }
    # Category → visual search context (1 word that returns good stock photos)
    CATEGORY_CONTEXT = {
        "ai_ml": "AI",
        "backend": "programming",
        "webdev": "developer",
        "security": "cybersecurity",
        "career": "career",
        "startup": "business",
        "devops": "cloud",
        "mobile": "smartphone",
        "general": "technology",
    }

    # Clean unicode artifacts from AI-generated titles (e.g. ΓÇ», Γ, etc.)
    clean_title = title.encode("ascii", "ignore").decode()
    words = re.sub(r"[^\w\s]", "", clean_title.lower()).split()
    filtered = [w for w in words if w not in stop and len(w) >= 4]

    # Use at most 2 title words + 1 category context word
    title_part = " ".join(filtered[:2])
    ctx = CATEGORY_CONTEXT.get(category, "technology")

    return f"{title_part} {ctx}" if title_part else f"{ctx} technology"


async def search_stock_photo(client: httpx.AsyncClient, query: str) -> str:
    """Search for a stock photo. Returns image URL or empty string.

    Priority: Unsplash (if key set) → Pexels (if key set) → Openverse (free, no key).
    """
    unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    pexels_key = os.environ.get("PEXELS_API_KEY", "")

    # Unsplash — best quality, requires free API key
    if unsplash_key:
        try:
            resp = await client.get(
                "https://api.unsplash.com/search/photos",
                params={"query": query, "per_page": 1, "orientation": "landscape"},
                headers={"Authorization": f"Client-ID {unsplash_key}"},
                timeout=8,
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    return results[0].get("urls", {}).get("regular", "")
        except Exception:
            pass

    # Pexels — good quality, requires free API key
    if pexels_key:
        try:
            resp = await client.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "per_page": 1, "orientation": "landscape"},
                headers={"Authorization": pexels_key},
                timeout=8,
            )
            if resp.status_code == 200:
                photos = resp.json().get("photos", [])
                if photos:
                    return photos[0].get("src", {}).get("large", "")
        except Exception:
            pass

    # Openverse — free, no key needed, uses Wikimedia Commons + open licensed photos
    try:
        resp = await client.get(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "license_type": "commercial", "page_size": 5},
            timeout=8,
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            for r in results:
                url = r.get("url", "")
                if url.startswith("http") and not url.endswith((".svg", ".pdf")):
                    return url
    except Exception:
        pass

    return ""


async def backfill_images(limit: int = 200, workers: int = 8):
    """Backfill images: Phase 1 = OG image from article URL; Phase 2 = stock photo."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, func, update
    import uuid

    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    sys.path.insert(0, os.path.join(_root, "backend"))
    from app.models import ProcessedContent, RawContent

    # Step 1: Load articles missing images
    async with Session() as db:
        count_result = await db.execute(
            select(func.count(ProcessedContent.id))
            .where(ProcessedContent.featured_image_url.is_(None))
            .where(ProcessedContent.status == "published")
        )
        total_missing = count_result.scalar() or 0
        print(f"Articles missing images: {total_missing}")
        print(f"Processing up to {limit} with {workers} OG workers\n")

        result = await db.execute(
            select(
                ProcessedContent.id,
                ProcessedContent.title,
                ProcessedContent.category,
                RawContent.original_url,
            )
            .join(RawContent, RawContent.id == ProcessedContent.raw_content_id)
            .where(ProcessedContent.featured_image_url.is_(None))
            .where(ProcessedContent.status == "published")
            .where(RawContent.original_url.isnot(None))
            .order_by(ProcessedContent.attractiveness_score.desc())
            .limit(limit)
        )
        rows = [(str(r.id), r.title or "", r.category or "", r.original_url) for r in result.all()]

    if not rows:
        print("No articles need images!")
        await engine.dispose()
        return

    # Phase 1: Fetch OG images from article URLs
    semaphore = asyncio.Semaphore(workers)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    og_results: dict[str, str] = {}
    no_og: list[tuple[str, str, str]] = []

    async def fetch_og_one(article_id: str, title: str, category: str, url: str):
        async with semaphore:
            img = await fetch_og_image(client, url)
            if img:
                og_results[article_id] = img
            else:
                no_og.append((article_id, title, category))

    print(f"Phase 1: Fetching OG images from {len(rows)} article URLs...")
    async with httpx.AsyncClient(headers=headers, timeout=8) as client:
        for i in range(0, len(rows), 20):
            batch = rows[i:i + 20]
            print(f"--- Batch {i // 20 + 1}/{(len(rows) + 19) // 20} ---")
            await asyncio.gather(*[fetch_og_one(aid, t, cat, u) for aid, t, cat, u in batch])

    print(f"\nPhase 1 done: {len(og_results)} OG images found, {len(no_og)} still missing\n")

    # Phase 2: Stock photo fallback for articles without OG image
    stock_results: dict[str, str] = {}
    if no_og:
        unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
        pexels_key = os.environ.get("PEXELS_API_KEY", "")
        if unsplash_key:
            source_label = "Unsplash"
        elif pexels_key:
            source_label = "Pexels"
        else:
            source_label = "Openverse (free)"

        print(f"Phase 2: Searching {source_label} stock photos for {len(no_og)} articles...")
        sem2 = asyncio.Semaphore(4)  # stock APIs have rate limits — be gentle

        async def fetch_stock_one(article_id: str, title: str, category: str):
            async with sem2:
                query = _stock_query(title, category)
                async with httpx.AsyncClient(timeout=10) as sc:
                    img = await search_stock_photo(sc, query)
                if img:
                    stock_results[article_id] = img
                    print(f"  [STOCK] {title[:60]}")
                    print(f"          query='{query}' -> {img[:70]}")
                else:
                    print(f"  [----]  {title[:60]}")

        await asyncio.gather(*[fetch_stock_one(aid, t, cat) for aid, t, cat in no_og])
        print(f"\nPhase 2 done: {len(stock_results)} stock photos found\n")

    # Save all results to DB
    all_results = {**og_results, **stock_results}
    if not all_results:
        print("No images found at all.")
        await engine.dispose()
        return

    updated = 0
    async with Session() as db:
        ids = list(all_results.keys())
        for i in range(0, len(ids), 50):
            for article_id in ids[i:i + 50]:
                await db.execute(
                    update(ProcessedContent)
                    .where(ProcessedContent.id == uuid.UUID(article_id))
                    .values(featured_image_url=all_results[article_id])
                )
                updated += 1
            await db.commit()

    await engine.dispose()
    print(f"Done! Updated {updated} articles ({len(og_results)} OG + {len(stock_results)} stock photos)")
    print(f"Remaining without images: {total_missing - updated}")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill article images: OG image from URL, then Unsplash/Pexels/Openverse fallback"
    )
    parser.add_argument("--limit", type=int, default=200, help="Max articles to process")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent OG fetch workers")
    args = parser.parse_args()
    asyncio.run(backfill_images(limit=args.limit, workers=args.workers))


if __name__ == "__main__":
    main()
