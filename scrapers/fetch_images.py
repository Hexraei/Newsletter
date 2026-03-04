#!/usr/bin/env python
"""Backfill article images — OG scraping first, Unsplash fallback.

Strategy (per article):
  1. Scrape the original article URL for og:image / twitter:image meta tags
  2. If OG scraping fails, search Unsplash with a smart title-based query
  3. Store the winning URL in processed_content.featured_image_url

Usage:
  python scrapers/fetch_images.py [--limit 200] [--batch-size 50]
  python scrapers/fetch_images.py --clear-bad   # clear duplicate/generic images
  python scrapers/fetch_images.py --stats        # show image source stats
"""

import asyncio
import argparse
import re
import sqlite3
import sys
import os
import time
from html.parser import HTMLParser

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
    "FQe0eshVZdey7aFWSmwJacsyNEe5JxDHA3XZdKdhaLM",
)

# ── Category → visual search context for Unsplash fallback ──────────
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

_VISUAL_NOISE = frozenset({
    "patch", "tuesday", "edition", "january", "february", "march", "april",
    "may", "june", "july", "august", "september", "october", "november",
    "december", "2024", "2025", "2026", "2027", "heres", "built", "released",
    "launches", "announces", "introduces", "raises", "million", "billion",
    "sixteen", "twelve", "hundred", "thousand", "annually", "produce",
    "early", "late", "ends", "begins", "opens", "closes", "seeks",
})


# ── OG Image Scraping ───────────────────────────────────────────────

class _OGParser(HTMLParser):
    """Fast HTML parser that only extracts og:image and twitter:image."""

    def __init__(self):
        super().__init__()
        self.og_image = ""
        self.twitter_image = ""
        self._in_head = False
        self._done = False

    def handle_starttag(self, tag, attrs):
        if self._done:
            return
        if tag == "head":
            self._in_head = True
            return
        if tag == "body":
            self._done = True
            return
        if tag != "meta":
            return
        d = dict(attrs)
        prop = d.get("property", "").lower()
        name = d.get("name", "").lower()
        content = d.get("content", "").strip()
        if not content:
            return
        if prop == "og:image" and not self.og_image:
            self.og_image = content
        elif name == "twitter:image" and not self.twitter_image:
            self.twitter_image = content


def _is_valid_image_url(url: str) -> bool:
    """Check if a URL looks like a valid, displayable image."""
    if not url or len(url) < 10:
        return False
    if not url.startswith(("http://", "https://")):
        return False
    # Reject SVGs (often logos), data URIs, and tiny placeholders
    low = url.lower()
    if low.endswith(".svg") or low.startswith("data:"):
        return False
    # Reject common placeholder/logo patterns
    reject_patterns = [
        "logo", "favicon", "icon", "badge", "avatar",
        "1x1", "pixel", "spacer", "blank", "placeholder",
    ]
    # Only reject if the pattern is in the filename part, not the domain
    path_part = low.split("?")[0].split("/")[-1] if "/" in low else low
    for pat in reject_patterns:
        if pat in path_part:
            return False
    return True


async def scrape_og_image(client: httpx.AsyncClient, url: str) -> str:
    """Fetch a page and extract its og:image or twitter:image meta tag.
    Only reads the first 50KB to be fast and respectful.
    """
    if not url or not url.startswith("http"):
        return ""
    try:
        # Use stream to limit download size — only need the <head>
        async with client.stream("GET", url, follow_redirects=True, timeout=8) as resp:
            if resp.status_code != 200:
                return ""
            ct = resp.headers.get("content-type", "")
            if "html" not in ct and "text" not in ct:
                return ""
            # Read first 50KB — og:image is always in <head>
            chunks = []
            total = 0
            async for chunk in resp.aiter_bytes(chunk_size=8192):
                chunks.append(chunk)
                total += len(chunk)
                if total >= 50_000:
                    break
            html = b"".join(chunks).decode("utf-8", errors="replace")

        parser = _OGParser()
        try:
            parser.feed(html)
        except Exception:
            pass

        # Prefer og:image over twitter:image
        img = parser.og_image or parser.twitter_image
        if _is_valid_image_url(img):
            return img
    except (httpx.TimeoutException, httpx.ConnectError, httpx.TooManyRedirects):
        pass
    except Exception:
        pass
    return ""


# ── Unsplash Search (fallback) ──────────────────────────────────────

def build_search_query(title: str, category: str = "general") -> str:
    """Build a 2-4 word search query from title + category context."""
    clean = title.encode("ascii", "ignore").decode()
    clean = re.sub(r"[^\w\s]", " ", clean.lower())
    words = clean.split()
    meaningful = [
        w for w in words
        if w not in _STOP and w not in _VISUAL_NOISE and len(w) >= 3
    ]
    meaningful.sort(key=lambda w: len(w), reverse=True)
    title_keywords = meaningful[:2]
    title_part = " ".join(title_keywords)
    ctx = CATEGORY_VISUAL.get(category, "technology")
    if not title_part:
        return ctx
    if any(kw in ctx.lower() for kw in title_keywords):
        return f"{title_part} technology"
    return f"{title_part} {ctx}"


async def fetch_unsplash(client: httpx.AsyncClient, query: str) -> str:
    """Search Unsplash for a landscape photo. Returns URL or empty string."""
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
                dl = photo.get("links", {}).get("download_location", "")
                if dl:
                    try:
                        await client.get(dl, params={"client_id": UNSPLASH_KEY}, timeout=5)
                    except Exception:
                        pass
                return url
        elif resp.status_code == 403:
            print("  [RATE LIMITED] Unsplash 50 req/hr limit hit")
    except Exception as e:
        print(f"  [ERROR] Unsplash: {e}")
    return ""


# ── Database helpers ────────────────────────────────────────────────

def get_db_path() -> str:
    """Find the SQLite database file."""
    db_url = os.environ.get("DATABASE_URL", "")
    if "sqlite" in db_url:
        path = db_url.split("///")[-1]
        if os.path.isabs(path):
            return path
        return os.path.join(_root, path)
    return os.path.join(_root, "newsletter.db")


def clear_bad_images(conn: sqlite3.Connection):
    """Remove duplicate/generic images (same URL used for 3+ articles)."""
    c = conn.cursor()
    # Find URLs used by 3+ articles — these are generic/irrelevant
    dupes = c.execute("""
        SELECT featured_image_url, COUNT(*) as cnt
        FROM processed_content
        WHERE featured_image_url IS NOT NULL
        GROUP BY featured_image_url
        HAVING cnt >= 3
    """).fetchall()
    total_cleared = 0
    for url, cnt in dupes:
        c.execute(
            "UPDATE processed_content SET featured_image_url = NULL WHERE featured_image_url = ?",
            (url,),
        )
        total_cleared += cnt
    conn.commit()
    print(f"Cleared {total_cleared} duplicate images ({len(dupes)} unique URLs used 3+ times)")
    return total_cleared


def show_stats(conn: sqlite3.Connection):
    """Print image source statistics."""
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM processed_content WHERE status='published'").fetchone()[0]
    with_img = c.execute("SELECT COUNT(*) FROM processed_content WHERE featured_image_url IS NOT NULL AND status='published'").fetchone()[0]
    print(f"\nImage coverage: {with_img}/{total} articles ({100*with_img//total}%)\n")
    rows = c.execute("""
        SELECT
            CASE WHEN featured_image_url LIKE '%flickr%' THEN 'flickr/openverse'
                 WHEN featured_image_url LIKE '%unsplash%' THEN 'unsplash'
                 WHEN featured_image_url LIKE '%wikimedia%' THEN 'wikimedia'
                 WHEN featured_image_url LIKE '%wp-content%' THEN 'og:image (wordpress)'
                 WHEN featured_image_url LIKE '%cdn%' THEN 'og:image (cdn)'
                 WHEN featured_image_url IS NULL THEN 'missing'
                 ELSE 'og:image (other)' END as src,
            COUNT(*) as cnt
        FROM processed_content WHERE status='published'
        GROUP BY src ORDER BY cnt DESC
    """).fetchall()
    for src, cnt in rows:
        print(f"  {src}: {cnt}")
    # Check duplicates
    dupes = c.execute("""
        SELECT COUNT(*) FROM (
            SELECT featured_image_url FROM processed_content
            WHERE featured_image_url IS NOT NULL
            GROUP BY featured_image_url HAVING COUNT(*) >= 3
        )
    """).fetchone()[0]
    print(f"\n  Duplicate URLs (used 3+ times): {dupes}")


# ── Main backfill logic ─────────────────────────────────────────────

async def backfill_images(limit: int = 200, batch_size: int = 50):
    """Backfill images: OG scraping (primary) + Unsplash (fallback)."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    total_missing = c.execute(
        "SELECT COUNT(*) FROM processed_content WHERE featured_image_url IS NULL AND status = 'published'"
    ).fetchone()[0]
    print(f"Articles missing images: {total_missing}")
    print(f"Processing up to {limit} in batches of {batch_size}")
    print(f"Strategy: OG scrape article URL → Unsplash fallback\n")

    # JOIN to get original_url from raw_content
    rows = c.execute("""
        SELECT p.id, p.title, p.category, r.original_url
        FROM processed_content p
        JOIN raw_content r ON REPLACE(p.raw_content_id, '-', '') = r.id
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

    og_ok = 0
    unsplash_ok = 0
    failed = 0
    start_time = time.time()
    unsplash_remaining = 45  # leave ~5 req buffer for frontend

    async with httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (NewsDay/1.0; image-backfill)"},
    ) as client:
        for batch_start in range(0, len(rows), batch_size):
            batch = rows[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(rows) + batch_size - 1) // batch_size
            print(f"=== Batch {batch_num}/{total_batches} ({len(batch)} articles) ===")

            for row in batch:
                article_id = row["id"]
                title = row["title"] or ""
                category = row["category"] or "general"
                original_url = row["original_url"] or ""

                # Step 1: Try OG image scraping from actual article
                url = await scrape_og_image(client, original_url)
                source = "OG"

                # Step 2: Unsplash fallback (if OG failed and budget remains)
                if not url and unsplash_remaining > 0:
                    query = build_search_query(title, category)
                    url = await fetch_unsplash(client, query)
                    if url:
                        unsplash_remaining -= 1
                        source = "Unsplash"

                if url:
                    c.execute(
                        "UPDATE processed_content SET featured_image_url = ? WHERE id = ?",
                        (url, article_id),
                    )
                    if source == "OG":
                        og_ok += 1
                    else:
                        unsplash_ok += 1
                    print(f"  [{source:8s}] {title[:65]}")
                else:
                    failed += 1
                    print(f"  [MISS    ] {title[:65]}")

                # Brief pause to be respectful to article servers
                await asyncio.sleep(0.3)

            conn.commit()
            elapsed = time.time() - start_time
            total_ok = og_ok + unsplash_ok
            print(f"    Progress: {total_ok}/{batch_start + len(batch)} | OG:{og_ok} Unsplash:{unsplash_ok} Miss:{failed} | {elapsed:.0f}s")

            if batch_start + batch_size < len(rows):
                await asyncio.sleep(1)

    conn.close()
    elapsed = time.time() - start_time
    total_ok = og_ok + unsplash_ok
    print(f"\nDone! Updated {total_ok}/{len(rows)} articles in {elapsed:.0f}s")
    print(f"  OG images: {og_ok}")
    print(f"  Unsplash:  {unsplash_ok}")
    print(f"  Failed:    {failed}")
    print(f"  Remaining: {total_missing - total_ok}")


def main():
    parser = argparse.ArgumentParser(description="Backfill article images (OG scrape + Unsplash)")
    parser.add_argument("--limit", type=int, default=200, help="Max articles to process")
    parser.add_argument("--batch-size", type=int, default=50, help="Articles per batch")
    parser.add_argument("--clear-bad", action="store_true", help="Clear duplicate/generic images first")
    parser.add_argument("--stats", action="store_true", help="Show image statistics and exit")
    args = parser.parse_args()

    if args.stats:
        conn = sqlite3.connect(get_db_path())
        show_stats(conn)
        conn.close()
        return

    if args.clear_bad:
        conn = sqlite3.connect(get_db_path())
        clear_bad_images(conn)
        show_stats(conn)
        conn.close()
        return

    asyncio.run(backfill_images(limit=args.limit, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
