#!/usr/bin/env python
"""Backfill images for articles missing featured_image_url.

Queries the database for processed content without images and uses the
semantic image fetcher to find relevant images. Falls back to category-based
search to guarantee every article gets an image.

Usage: python scrapers/fetch_images.py [--limit 100] [--min-score 0.1]
"""

import asyncio
import argparse
import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, _root)  # for scrapers.lib imports

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))


async def backfill_images(limit: int = 100, min_score: float = 0.1):
    """Find and set images for articles that are missing them."""
    from sqlalchemy import select, func
    from app.models.base import AsyncSessionLocal
    from app.models import ProcessedContent
    from app.services.image_fetcher import ImageFetcher

    fetcher = ImageFetcher(sources=["openverse", "wikimedia"])
    semaphore = asyncio.Semaphore(3)  # max 3 concurrent API calls

    async with AsyncSessionLocal() as db:
        # Count total missing
        count_result = await db.execute(
            select(func.count(ProcessedContent.id))
            .where(ProcessedContent.featured_image_url.is_(None))
            .where(ProcessedContent.status == "published")
        )
        total_missing = count_result.scalar() or 0
        print(f"Articles missing images: {total_missing}")
        print(f"Processing up to {limit} articles (min score: {min_score})\n")

        # Fetch articles without images
        result = await db.execute(
            select(ProcessedContent)
            .where(ProcessedContent.featured_image_url.is_(None))
            .where(ProcessedContent.status == "published")
            .order_by(ProcessedContent.attractiveness_score.desc())
            .limit(limit)
        )
        articles = result.scalars().all()

        if not articles:
            print("No articles need images!")
            return

        updated = 0
        failed = 0

        async def fetch_one(article):
            nonlocal updated, failed
            async with semaphore:
                try:
                    category = (article.category or "general").lower()
                    result = await fetcher.fetch_with_fallback(
                        article.title, category=category, top_k=1
                    )
                    if result and result.get("url"):
                        article.featured_image_url = result["url"]
                        credit_data = {
                            "credit": result.get("creator", ""),
                            "source_url": result.get("source_url", ""),
                            "provider": result.get("provider", ""),
                            "license": result.get("license", ""),
                        }
                        vis = article.visualizations or {}
                        vis["image_credit"] = credit_data
                        article.visualizations = vis
                        updated += 1
                        score = result.get("score", 0)
                        tag = "SEM" if score >= 0.15 else "CAT"
                        print(f"  [{tag}] [{score:.3f}] [{result['provider']}] {article.title[:60]}")
                    else:
                        failed += 1
                        print(f"  [--] [no results] {article.title[:60]}")
                except Exception as e:
                    failed += 1
                    print(f"  [ERR] {article.title[:60]}: {e}")

        # Process in batches of 10
        for i in range(0, len(articles), 10):
            batch = articles[i:i + 10]
            batch_num = i // 10 + 1
            total_batches = (len(articles) + 9) // 10
            print(f"Batch {batch_num}/{total_batches}:")
            await asyncio.gather(*[fetch_one(a) for a in batch])
            await db.commit()
            print()

        print(f"Done! Updated: {updated}, Skipped/Failed: {failed}")
        print(f"Remaining without images: {total_missing - updated}")

        print(f"Done! Updated: {updated}, Skipped/Failed: {failed}")
        print(f"Remaining without images: {total_missing - updated}")


def main():
    parser = argparse.ArgumentParser(description="Backfill images for articles")
    parser.add_argument("--limit", type=int, default=100, help="Max articles to process")
    parser.add_argument("--min-score", type=float, default=0.2, help="Minimum similarity score")
    args = parser.parse_args()

    asyncio.run(backfill_images(limit=args.limit, min_score=args.min_score))


if __name__ == "__main__":
    main()
