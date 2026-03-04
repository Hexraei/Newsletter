#!/usr/bin/env python
"""Backfill article images using Unsplash as the primary source.

Strategy:
  1. Build a smart search query from article title + category
  2. Fetch a relevant landscape photo from Unsplash
  3. Store the URL in processed_content.featured_image_url

Uses direct SQLite access to avoid UUID format mismatch between tables.

Usage: python scrapers/fetch_images.py [--limit 200] [--batch-size 45]
"""

import asyncio
import argparse
import json
import re
import sqlite3
import sys
import os
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, _root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

import httpx

# ── Unsplash config ──────────────────────────────────────────────────
UNSPLASH_KEY = os.environ.get(
    "UNSPLASH_ACCESS_KEY",
    "FQe0eshVZdey7aFWSmwJacsyNEe5JxDHA3XZdKdhaLM",  # frontend public key
)
UNSPLASH_RATE_LIMIT = 50   # free tier: 50 req/hr
UNSPLASH_BATCH_DELAY = 3   # seconds between batches to stay under rate limit

# ── Category → visual search context ────────────────────────────────
# Maps article categories to 1-2 words that produce visually relevant
# Unsplash results when combined with title keywords.
CATEGORY_VISUAL = {
    "ai_ml":       "artificial intelligence",
    "backend":     "programming code",
    "webdev":      "web development",
    "security":    "cybersecurity",
    "career":      "career workplace",
    "startup":     "startup business",
    "devops":      "cloud servers",
    "mobile":      "smartphone app",
    "robotics":    "robot technology",
    "electronics": "circuit board",
    "research":    "scientific research",
    "biotech":     "biotechnology lab",
    "energy":      "renewable energy",
    "general":     "technology",
}

# Stop words for title keyword extraction
_STOP = frozenset({
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "has", "have", "how", "why", "what", "when", "where",
    "it", "its", "this", "that", "with", "by", "as", "if", "be", "not", "now",
    "new", "just", "will", "can", "get", "all", "more", "over", "per", "vs",
    "via", "says", "their", "your", "our", "from", "into", "about", "than",
    "still", "after", "before", "same", "year", "years", "day", "days", "week",
    "work", "find", "think", "make", "does", "want", "need", "best", "good",
    "using", "ever", "only", "also", "even", "both", "here", "there", "been",
    "being", "could", "would", "should", "they", "them", "who", "which", "but",
    "first", "last", "says", "announces", "update", "roundup", "daily", "weekly",
    "watch", "look", "see", "show", "take", "give", "keep", "put", "tell",
    "know", "come", "goes", "went", "help", "open", "close", "start", "stop",
    "together", "every", "between", "through", "while", "during", "without",
    "hundreds", "millions", "billions", "thousands", "several", "many", "much",
})

# Domain-specific keywords that are visually meaningless on Unsplash
_VISUAL_NOISE = frozenset({
    "patch", "tuesday", "edition", "january", "february", "march", "april",
    "may", "june", "july", "august", "september", "october", "november",
    "december", "2024", "2025", "2026", "2027", "heres", "built", "released",
    "launches", "announces", "introduces", "raises", "million", "billion",
    "sixteen", "twelve", "hundred", "thousand", "annually", "produce",
    "early", "late", "ends", "begins", "opens", "closes", "seeks",
})


def build_unsplash_query(title: str, category: str = "general") -> str:
    """Build a relevant 2-4 word Unsplash search query from title + category.

    Strategy:
      1. Extract meaningful noun-like words from title (skip stopwords + visual noise)
      2. Pick the 2 most descriptive words
      3. Append category visual context if title keywords are too generic
      4. Result: "python programming code" or "cybersecurity breach"
    """
    # Clean non-ASCII and punctuation
    clean = title.encode("ascii", "ignore").decode()
    clean = re.sub(r"[^\w\s]", " ", clean.lower())
    words = clean.split()

    # Filter: skip stopwords, visual noise, very short words
    meaningful = [
        w for w in words
        if w not in _STOP and w not in _VISUAL_NOISE and len(w) >= 3
    ]

    # Prefer longer, more descriptive words (they produce better image results)
    meaningful.sort(key=lambda w: len(w), reverse=True)

    # Take top 2 meaningful words
    title_keywords = meaningful[:2]
    title_part = " ".join(title_keywords)

    # Get category visual context
    ctx = CATEGORY_VISUAL.get(category, "technology")

    if not title_part:
        return ctx
    # If title keywords overlap with category context, just use title + "technology"
    if any(kw in ctx.lower() for kw in title_keywords):
        return f"{title_part} technology"
    return f"{title_part} {ctx}"


async def fetch_unsplash(
    client: httpx.AsyncClient, query: str
) -> tuple[str, str]:
    """Search Unsplash for a landscape photo. Returns (url, photographer_name)."""
    try:
        resp = await client.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": query,
                "per_page": 1,
                "orientation": "landscape",
                "content_filter": "high",
            },
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            timeout=10,
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                photo = results[0]
                url = photo.get("urls", {}).get("regular", "")
                name = photo.get("user", {}).get("name", "Unsplash")
                # Trigger download event (Unsplash guidelines)
                dl = photo.get("links", {}).get("download_location", "")
                if dl:
                    try:
                        await client.get(dl, params={"client_id": UNSPLASH_KEY}, timeout=5)
                    except Exception:
                        pass
                return url, name
        elif resp.status_code == 403:
            print("  [RATE LIMITED] Unsplash rate limit hit!")
    except Exception as e:
        print(f"  [ERROR] Unsplash: {e}")
    return "", ""


async def fetch_openverse(
    client: httpx.AsyncClient, query: str
) -> tuple[str, str]:
    """Search Openverse for a relevant image. Returns (url, creator_name).
    Free API, no key needed, generous rate limits.
    """
    try:
        resp = await client.get(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "page_size": 3},
            timeout=10,
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            for r in results:
                url = r.get("url", "")
                # Skip SVGs, PDFs, and very small thumbnails
                if url.startswith("http") and not url.endswith((".svg", ".pdf", ".gif")):
                    creator = r.get("creator", "Openverse")
                    return url, creator or "Openverse"
        elif resp.status_code == 429:
            print("  [RATE LIMITED] Openverse rate limit hit!")
    except Exception as e:
        print(f"  [ERROR] Openverse: {e}")
    return "", ""


async def fetch_image(
    client: httpx.AsyncClient, query: str, fallback_query: str = ""
) -> str:
    """Try Openverse first (free, high rate limit), then Unsplash, then fallback query."""
    # Primary: Openverse
    url, _ = await fetch_openverse(client, query)
    if url:
        return url

    # Secondary: Unsplash
    url, _ = await fetch_unsplash(client, query)
    if url:
        return url

    # Fallback: simpler query
    if fallback_query and fallback_query != query:
        url, _ = await fetch_openverse(client, fallback_query)
        if url:
            return url

    return ""


def get_db_path() -> str:
    """Find the SQLite database file."""
    db_url = os.environ.get("DATABASE_URL", "")
    if "sqlite" in db_url:
        path = db_url.split("///")[-1]
        if os.path.isabs(path):
            return path
        return os.path.join(_root, path)
    # Default fallback
    return os.path.join(_root, "newsletter.db")


async def backfill_images(limit: int = 200, batch_size: int = 50):
    """Backfill images using Openverse (free) + Unsplash."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Count articles missing images
    total_missing = c.execute(
        "SELECT COUNT(*) FROM processed_content WHERE featured_image_url IS NULL AND status = 'published'"
    ).fetchone()[0]
    print(f"Articles missing images: {total_missing}")
    print(f"Processing up to {limit} in batches of {batch_size}")
    print(f"Sources: Openverse (primary, free) + Unsplash (secondary)\n")

    # Load articles missing images (ordered by attractiveness for priority)
    rows = c.execute("""
        SELECT p.id, p.title, p.category, p.department_tags
        FROM processed_content p
        WHERE p.featured_image_url IS NULL
          AND p.status = 'published'
        ORDER BY p.attractiveness_score DESC
        LIMIT ?
    """, (limit,)).fetchall()

    if not rows:
        print("No articles need images!")
        conn.close()
        return

    print(f"Fetching images for {len(rows)} articles...\n")

    updated = 0
    failed = 0
    start_time = time.time()

    async with httpx.AsyncClient(timeout=10) as client:
        for batch_start in range(0, len(rows), batch_size):
            batch = rows[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(rows) + batch_size - 1) // batch_size
            print(f"=== Batch {batch_num}/{total_batches} ({len(batch)} articles) ===")

            for row in batch:
                article_id = row["id"]
                title = row["title"] or ""
                category = row["category"] or "general"

                query = build_unsplash_query(title, category)
                ctx = CATEGORY_VISUAL.get(category, "technology")
                fallback_q = f"{ctx} abstract"

                url = await fetch_image(client, query, fallback_q)

                if url:
                    c.execute(
                        "UPDATE processed_content SET featured_image_url = ? WHERE id = ?",
                        (url, article_id),
                    )
                    updated += 1
                    print(f"  [OK] q='{query}' | {title[:55]}")
                else:
                    failed += 1
                    print(f"  [--] q='{query}' | {title[:55]}")

                # Openverse rate limit is ~100/min; be gentle
                await asyncio.sleep(0.8)

            conn.commit()
            elapsed = time.time() - start_time
            print(f"    Progress: {updated}/{batch_start + len(batch)} images in {elapsed:.0f}s")

            if batch_start + batch_size < len(rows):
                print(f"    Pausing 2s between batches...")
                await asyncio.sleep(2)

    conn.close()
    elapsed = time.time() - start_time
    print(f"\nDone! Updated {updated}/{len(rows)} articles in {elapsed:.0f}s")
    print(f"  {failed} failed")
    print(f"  Remaining without images: {total_missing - updated}")


def main():
    parser = argparse.ArgumentParser(description="Backfill article images from Unsplash")
    parser.add_argument("--limit", type=int, default=200, help="Max articles to process")
    parser.add_argument("--batch-size", type=int, default=50, help="Articles per batch")
    args = parser.parse_args()
    asyncio.run(backfill_images(limit=args.limit, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
