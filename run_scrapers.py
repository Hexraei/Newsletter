"""Run scrapers and process content directly (no auth required)."""
import asyncio
import sys
import os

_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, os.path.join(_root, "scraper_platform"))

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from app.models.base import AsyncSessionLocal
from app.services.scraper_service import ScraperService
from app.services.content_processor import ContentProcessor


async def main():
    async with AsyncSessionLocal() as db:
        service = ScraperService(db)
        
        # Run scrapers that work without API keys
        for name in ["hackernews", "reddit", "github", "medium", "producthunt"]:
            print(f"\n--- Running {name} scraper ---")
            result = await service.run_scraper(name)
            print(f"  Result: {result}")
        
        # Process pending content
        print("\n--- Processing pending content ---")
        processor = ContentProcessor(db)
        processed = await processor.process_pending_items(limit=100)
        print(f"  Processed {processed} items")


if __name__ == "__main__":
    asyncio.run(main())
