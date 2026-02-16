"""Quick test of the full pipeline."""
import asyncio
import sys
sys.path.insert(0, r'D:\newsletter\backend')
sys.path.insert(0, r'D:\newsletter\scraper_platform')

from app.models.base import AsyncSessionLocal
from app.services.scraper_service import ScraperService
from app.services.content_processor import ContentProcessor
from app.services.feed_service import FeedService

async def run():
    async with AsyncSessionLocal() as db:
        print('='*50)
        print('1. Scraping HackerNews...')
        scraper = ScraperService(db)
        result = await scraper.run_scraper('hackernews', limit=3)
        print(f'   Scraped: {result.get("items_scraped", 0)} items')
        
        print('2. Processing content...')
        processor = ContentProcessor(db)
        proc = await processor.process_pending_items(limit=5)
        print(f'   Processed: {proc["processed"]} items')
        
        print('3. Getting feed...')
        feed = FeedService(db)
        feed_data = await feed.get_personalized_feed(limit=5)
        print(f'   Feed items: {feed_data["total"]}')
        
        for item in feed_data['items']:
            print(f'   - {item["title"][:50]}...')
        
        print('='*50)
        print('Done!')

if __name__ == "__main__":
    asyncio.run(run())
