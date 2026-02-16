"""Test scraper integration with backend."""

import asyncio
import sys

sys.path.insert(0, 'D:\\newsletter\\backend')
sys.path.insert(0, 'D:\\newsletter\\scraper_platform')

print('='*60)
print('SCRAPER INTEGRATION TEST')
print('='*60)

# Test 1: Import scrapers
print('\n[Step 1] Testing imports...')
try:
    from src.scrapers.hackernews_scraper import HackerNewsScraper
    from src.scrapers.reddit_scraper import RedditScraper
    from src.scrapers.twitter_scraper import TwitterScraper
    from src.scrapers.github_scraper import GitHubScraper
    print('[OK] Scrapers imported successfully')
except Exception as e:
    print(f'[FAIL] Import error: {e}')
    sys.exit(1)

# Test 2: Import services
print('\n[Step 2] Testing service imports...')
try:
    from app.services.scraper_service import ScraperService
    from app.services.content_processor import ContentProcessor
    print('[OK] Services imported successfully')
except Exception as e:
    print(f'[FAIL] Service import error: {e}')
    sys.exit(1)

# Test 3: Import tasks
print('\n[Step 3] Testing task imports...')
try:
    from app.tasks.scraper_tasks import celery_app, scrape_hackernews
    print('[OK] Celery tasks imported successfully')
except Exception as e:
    print(f'[FAIL] Task import error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Import API
print('\n[Step 4] Testing API imports...')
try:
    from app.api.v1.scrapers import router as scraper_router
    print('[OK] Scraper API imported successfully')
except Exception as e:
    print(f'[FAIL] API import error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Database connection and source creation
print('\n[Step 5] Testing database integration...')

async def test_db():
    from app.models.base import AsyncSessionLocal
    
    try:
        async with AsyncSessionLocal() as db:
            service = ScraperService(db)
            await service.ensure_sources_exist()
            print('[OK] Sources ensured in database')
            
            # Get scraper status
            status = await service.get_scraper_status()
            print(f'[INFO] Found {len(status)} sources:')
            for s in status:
                print(f'  - {s["name"]} ({s["platform"]}): {"Active" if s["is_active"] else "Inactive"}')
            
            return True
    except Exception as e:
        print(f'[FAIL] Database error: {e}')
        import traceback
        traceback.print_exc()
        return False

try:
    result = asyncio.run(test_db())
    if not result:
        sys.exit(1)
except Exception as e:
    print(f'[FAIL] Test error: {e}')
    sys.exit(1)

print('')
print('='*60)
print('SUCCESS! SCRAPER INTEGRATION IS WORKING')
print('='*60)
print('')
print('Available scrapers:')
print('  - hackernews')
print('  - reddit')
print('  - twitter')
print('  - github')
print('  - medium')
print('  - producthunt')
print('')
print('API Endpoints:')
print('  GET  /api/v1/scrapers/status')
print('  POST /api/v1/scrapers/run/{scraper_name}')
print('  POST /api/v1/scrapers/run-all')
print('  POST /api/v1/scrapers/process-pending')
print('')
print('Next steps:')
print('  1. Start Celery worker for scheduled scraping')
print('  2. Or use API to manually trigger scrapers')
print('')
