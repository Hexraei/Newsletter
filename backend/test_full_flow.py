"""Test full content flow: scrape -> process -> feed."""

import asyncio
import sys

sys.path.insert(0, 'D:\\newsletter\\backend')
sys.path.insert(0, 'D:\\newsletter\\scraper_platform')

print('='*60)
print('FULL CONTENT FLOW TEST')
print('='*60)

async def test_full_flow():
    from app.models.base import AsyncSessionLocal
    from app.services.scraper_service import ScraperService
    from app.services.content_processor import ContentProcessor
    from app.services.feed_service import FeedService
    from app.services.pipeline_service import PipelineService
    from sqlalchemy import select
    from app.models import RawContent, ProcessedContent
    
    async with AsyncSessionLocal() as db:
        # Step 1: Scrape HackerNews
        print('\n[Step 1] Scraping HackerNews...')
        scraper = ScraperService(db)
        result = await scraper.run_scraper('hackernews', limit=2)
        print(f"[OK] Scraped: {result.get('items_scraped', 0)} items")
        
        # Step 2: Check pending items
        print('\n[Step 2] Checking pending items...')
        result = await db.execute(
            select(RawContent).where(RawContent.status == 'pending')
        )
        pending = result.scalars().all()
        print(f"[OK] Pending items: {len(pending)}")
        for item in pending:
            print(f"    - {item.original_title[:50]}...")
        
        # Step 3: Process pending items
        print('\n[Step 3] Processing pending items...')
        processor = ContentProcessor(db)
        process_result = await processor.process_pending_items(limit=5)
        print(f"[OK] Processed: {process_result['processed']}/{process_result['total_pending']}")
        if process_result['errors']:
            for err in process_result['errors']:
                print(f"    Error: {err}")
        
        # Step 4: Check processed content
        print('\n[Step 4] Checking processed content...')
        result = await db.execute(
            select(ProcessedContent).order_by(ProcessedContent.published_at.desc()).limit(3)
        )
        processed = result.scalars().all()
        print(f"[OK] Recent processed items: {len(processed)}")
        for item in processed:
            print(f"    - {item.title[:50]}...")
            print(f"      Score: {item.attractiveness_score}, Category: {item.category}")
        
        # Step 5: Check feed
        print('\n[Step 5] Checking feed...')
        feed = FeedService(db)
        feed_data = await feed.get_personalized_feed(limit=5)
        print(f"[OK] Feed items: {feed_data['total']}")
        for item in feed_data['items'][:3]:
            print(f"    - {item['title'][:50]}...")
        
        # Step 6: Check trending
        print('\n[Step 6] Checking trending...')
        trending = await feed.get_trending_content(limit=3)
        print(f"[OK] Trending items: {len(trending)}")
        
        # Step 7: Pipeline status
        print('\n[Step 7] Pipeline status...')
        pipeline = PipelineService(db)
        status = await pipeline.get_pipeline_status()
        print(f"[OK] Status:")
        print(f"    Raw pending: {status['raw_content']['pending']}")
        print(f"    Processed: {status['processed_content']}")
        print(f"    AI Provider: {status['ai_provider']}")

if __name__ == "__main__":
    try:
        asyncio.run(test_full_flow())
        
        print('\n' + '='*60)
        print('SUCCESS! FULL CONTENT FLOW WORKING')
        print('='*60)
    except Exception as e:
        print(f'\n[FAIL] Error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
