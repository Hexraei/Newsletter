"""Test HackerNews scraper integration."""

import asyncio
import sys

sys.path.insert(0, 'D:\\newsletter\\backend')
sys.path.insert(0, 'D:\\newsletter\\scraper_platform')

print('='*60)
print('HACKERNEWS SCRAPER TEST')
print('='*60)

async def test_scraper():
    from src.scrapers.hackernews_scraper import HackerNewsScraper
    
    print('\n[Step 1] Initializing scraper...')
    scraper = HackerNewsScraper()
    
    print('[Step 2] Scraping top stories (limit=5)...')
    async with scraper:
        items = await scraper.scrape(limit=5)
    
    print(f'[OK] Scraped {len(items)} items')
    
    print('\n[Step 3] Sample items:')
    for i, item in enumerate(items[:3], 1):
        print(f'\n  Item {i}:')
        print(f'    Title: {item.title[:60]}...' if len(item.title) > 60 else f'    Title: {item.title}')
        print(f'    URL: {item.url}')
        print(f'    Source Type: {item.source_type}')
        print(f'    Metadata: {item.metadata}')
    
    return items

async def test_service():
    from app.models.base import AsyncSessionLocal
    from app.services.scraper_service import ScraperService
    
    print('\n[Step 4] Testing ScraperService...')
    
    async with AsyncSessionLocal() as db:
        service = ScraperService(db)
        
        # Run scraper and store results
        print('[Step 5] Running HackerNews scraper via service...')
        results = await service.run_scraper('hackernews', limit=3)
        
        print(f'[OK] Scraper completed:')
        print(f'    Scraper: {results["scraper"]}')
        print(f'    Items scraped: {results["items_scraped"]}')
        print(f'    Items stored: {results["items_stored"]}')
        print(f'    Status: {results["status"]}')
        
        # Show sample of stored items
        print('\n[Step 6] Checking stored items...')
        from app.models.content import RawContent
        from sqlalchemy import select
        
        result = await db.execute(
            select(RawContent).order_by(RawContent.scraped_at.desc()).limit(2)
        )
        stored = result.scalars().all()
        
        print(f'[OK] Found {len(stored)} recent items in database:')
        for item in stored:
            print(f'    - {item.original_title[:50]}... (status: {item.status})')

if __name__ == "__main__":
    try:
        asyncio.run(test_scraper())
        asyncio.run(test_service())
        
        print('\n' + '='*60)
        print('SUCCESS! HACKERNEWS SCRAPER WORKING END-TO-END')
        print('='*60)
    except Exception as e:
        print(f'\n[FAIL] Error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
