"""Complete system integration test."""

import asyncio
import sys

sys.path.insert(0, 'D:\\newsletter\\backend')
sys.path.insert(0, 'D:\\newsletter\\scraper_platform')

print('='*70)
print('COMPLETE SYSTEM INTEGRATION TEST')
print('='*70)

async def test_complete_system():
    from app.models.base import AsyncSessionLocal
    from app.services.scraper_service import ScraperService
    from app.services.content_processor import ContentProcessor
    from app.services.feed_service import FeedService
    from app.services.pipeline_service import PipelineService
    from app.integrations.ai_provider import AIProvider
    from sqlalchemy import select, func
    from app.models import RawContent, ProcessedContent, Source
    
    results = []
    
    async with AsyncSessionLocal() as db:
        # Test 1: AI Provider
        print('\n[TEST 1] AI Provider')
        try:
            ai = AIProvider()
            print(f'  ✓ Provider: {ai.provider}')
            
            # Test summarization
            summary = await ai.summarize(
                title="Test Article",
                content="This is a test article about AI technology.",
                category="tech"
            )
            print(f'  ✓ Summarization working')
            print(f'    Hook: {summary.get("hook", "N/A")[:50]}...')
            results.append(('AI Provider', 'PASS'))
        except Exception as e:
            print(f'  ✗ Error: {e}')
            results.append(('AI Provider', 'FAIL'))
        
        # Test 2: Scraper Service
        print('\n[TEST 2] Scraper Service')
        try:
            scraper = ScraperService(db)
            await scraper.ensure_sources_exist()
            
            # Count sources
            result = await db.execute(select(func.count(Source.id)))
            source_count = result.scalar()
            print(f'  ✓ Sources configured: {source_count}')
            results.append(('Scraper Service', 'PASS'))
        except Exception as e:
            print(f'  ✗ Error: {e}')
            results.append(('Scraper Service', 'FAIL'))
        
        # Test 3: Content Processing
        print('\n[TEST 3] Content Processing')
        try:
            processor = ContentProcessor(db)
            
            # Check pending items
            result = await db.execute(
                select(func.count(RawContent.id)).where(RawContent.status == 'pending')
            )
            pending_count = result.scalar()
            print(f'  ✓ Pending items: {pending_count}')
            
            # Process any pending
            if pending_count > 0:
                process_result = await processor.process_pending_items(limit=3)
                print(f'  ✓ Processed: {process_result["processed"]}')
            
            results.append(('Content Processing', 'PASS'))
        except Exception as e:
            print(f'  ✗ Error: {e}')
            results.append(('Content Processing', 'FAIL'))
        
        # Test 4: Feed Service
        print('\n[TEST 4] Feed Service')
        try:
            feed = FeedService(db)
            
            # Get personalized feed
            feed_data = await feed.get_personalized_feed(limit=5)
            print(f'  ✓ Feed items: {feed_data["total"]}')
            
            # Get trending
            trending = await feed.get_trending_content(limit=3)
            print(f'  ✓ Trending items: {len(trending)}')
            
            # Get stats
            stats = await feed.get_feed_stats()
            print(f'  ✓ Total published: {stats["total_published"]}')
            
            results.append(('Feed Service', 'PASS'))
        except Exception as e:
            print(f'  ✗ Error: {e}')
            results.append(('Feed Service', 'FAIL'))
        
        # Test 5: Pipeline Status
        print('\n[TEST 5] Pipeline Status')
        try:
            pipeline = PipelineService(db)
            status = await pipeline.get_pipeline_status()
            
            print(f'  ✓ Raw pending: {status["raw_content"]["pending"]}')
            print(f'  ✓ Processed: {status["processed_content"]}')
            print(f'  ✓ AI Provider: {status["ai_provider"]}')
            
            results.append(('Pipeline', 'PASS'))
        except Exception as e:
            print(f'  ✗ Error: {e}')
            results.append(('Pipeline', 'FAIL'))
        
        # Test 6: Full Pipeline Run
        print('\n[TEST 6] Full Pipeline Run')
        try:
            # Scrape 2 items from HackerNews
            scrape_result = await scraper.run_scraper('hackernews', limit=2)
            print(f'  ✓ Scraped: {scrape_result.get("items_scraped", 0)} items')
            
            # Process pending
            process_result = await processor.process_pending_items(limit=5)
            print(f'  ✓ Processed: {process_result["processed"]} items')
            
            # Check feed again
            feed_data = await feed.get_personalized_feed(limit=5)
            print(f'  ✓ Feed now has: {feed_data["total"]} items')
            
            results.append(('Full Pipeline', 'PASS'))
        except Exception as e:
            print(f'  ✗ Error: {e}')
            results.append(('Full Pipeline', 'FAIL'))
    
    return results

if __name__ == "__main__":
    try:
        results = asyncio.run(test_complete_system())
        
        print('\n' + '='*70)
        print('TEST SUMMARY')
        print('='*70)
        
        passed = sum(1 for _, r in results if r == 'PASS')
        failed = sum(1 for _, r in results if r == 'FAIL')
        
        for name, result in results:
            status = '✅' if result == 'PASS' else '❌'
            print(f'{status} {name}: {result}')
        
        print('='*70)
        print(f'Results: {passed} passed, {failed} failed')
        
        if failed == 0:
            print('\n🎉 ALL TESTS PASSED! System is fully operational.')
        else:
            print(f'\n⚠️  {failed} test(s) failed. Check errors above.')
            
        print('='*70)
        print('')
        print('Available Frontends:')
        print('  1. Test UI:      http://localhost:8000/static/index.html')
        print('  2. Reader UI:    http://localhost:8000/static/reader.html')
        print('')
        print('Key API Endpoints:')
        print('  GET  /api/v1/feed/personalized')
        print('  GET  /api/v1/feed/trending')
        print('  GET  /api/v1/feed/daily-digest')
        print('  POST /api/v1/scrapers/run/hackernews')
        print('  POST /api/v1/pipeline/run')
        print('='*70)
        
    except Exception as e:
        print(f'\n[FAIL] Fatal error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
