"""Test content pipeline end-to-end."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraper_platform'))

print('='*60)
print('CONTENT PIPELINE TEST')
print('='*60)

async def test_pipeline():
    from app.models.base import AsyncSessionLocal
    from app.services.pipeline_service import PipelineService
    from app.services.content_processor import ContentProcessor
    from app.services.feed_service import FeedService
    
    async with AsyncSessionLocal() as db:
        # Test 1: Get pipeline status
        print('\n[Step 1] Checking pipeline status...')
        pipeline = PipelineService(db)
        status = await pipeline.get_pipeline_status()
        print(f'[OK] Pipeline status:')
        print(f'    Raw content pending: {status["raw_content"]["pending"]}')
        print(f'    Processed content: {status["processed_content"]}')
        print(f'    Pending embeddings: {status["pending_embeddings"]}')
        print(f'    AI Provider: {status["ai_provider"]}')
        
        # Test 2: Process any pending raw content
        print('\n[Step 2] Processing pending content...')
        processor = ContentProcessor(db)
        result = await processor.process_pending_items(limit=5)
        print(f'[OK] Processing result:')
        print(f'    Processed: {result["processed"]}')
        print(f'    Total pending: {result["total_pending"]}')
        if result["errors"]:
            print(f'    Errors: {len(result["errors"])}')
        
        # Test 3: Get processing stats
        print('\n[Step 3] Getting processing stats...')
        stats = await processor.get_processing_stats()
        print(f'[OK] Stats:')
        print(f'    Raw content: {stats["raw_content"]}')
        print(f'    Processed content: {stats["processed_content"]}')
        print(f'    Avg attractiveness: {stats["average_attractiveness_score"]}')
        
        # Test 4: Get feed stats
        print('\n[Step 4] Getting feed stats...')
        feed = FeedService(db)
        feed_stats = await feed.get_feed_stats()
        print(f'[OK] Feed stats:')
        print(f'    Total published: {feed_stats["total_published"]}')
        print(f'    Today count: {feed_stats["today_count"]}')
        print(f'    By category: {feed_stats["by_category"]}')
        
        # Test 5: Get trending content
        print('\n[Step 5] Getting trending content...')
        trending = await feed.get_trending_content(limit=3)
        print(f'[OK] Found {len(trending)} trending items:')
        for item in trending:
            print(f'    - {item["title"][:50]}... (score: {item["attractiveness_score"]})')
        
        # Test 6: Get daily digest
        print('\n[Step 6] Getting daily digest...')
        digest = await feed.get_daily_digest(limit=5)
        print(f'[OK] Daily digest:')
        print(f'    Date: {digest["date"]}')
        print(f'    Total stories: {digest["total_stories"]}')
        print(f'    Categories: {list(digest["categories"].keys())}')
        
        # Test 7: Get personalized feed (no auth)
        print('\n[Step 7] Getting personalized feed...')
        personalized = await feed.get_personalized_feed(limit=5)
        print(f'[OK] Personalized feed:')
        print(f'    Items: {personalized["total"]}')
        print(f'    Has more: {personalized["has_more"]}')
        for item in personalized["items"][:3]:
            print(f'    - {item["title"][:50]}...')

if __name__ == "__main__":
    try:
        asyncio.run(test_pipeline())
        
        print('\n' + '='*60)
        print('SUCCESS! CONTENT PIPELINE WORKING')
        print('='*60)
        print('')
        print('Available endpoints:')
        print('  GET  /api/v1/pipeline/status')
        print('  POST /api/v1/pipeline/run')
        print('  POST /api/v1/pipeline/process')
        print('  GET  /api/v1/feed/personalized')
        print('  GET  /api/v1/feed/trending')
        print('  GET  /api/v1/feed/daily-digest')
        print('')
    except Exception as e:
        print(f'\n[FAIL] Error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
