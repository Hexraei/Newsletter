"""
Hacker News Scraper
Uses official Firebase API - free, no auth required, generous rate limits.
"""

import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Any

from scrapers.lib.base_scraper import BaseScraper, ScrapedItem


class HackerNewsScraper(BaseScraper):
    """Scraper for Hacker News using official Firebase API."""
    
    def __init__(self):
        super().__init__("Hacker News", "community")
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.api_client = None
        
    async def __aenter__(self):
        await super().__aenter__()
        self.api_client = httpx.AsyncClient(timeout=30)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.api_client:
            await self.api_client.aclose()
        await super().__aexit__(exc_type, exc_val, exc_tb)
    
    async def get_top_stories(self, limit: int = 30) -> List[Dict]:
        """Get current front page stories."""
        try:
            response = await self.api_client.get(f"{self.base_url}/topstories.json")
            response.raise_for_status()
            story_ids = response.json()[:limit]
            
            # Fetch story details in parallel
            stories = await asyncio.gather(*[
                self.get_story(sid) for sid in story_ids
            ])
            return [s for s in stories if s]
        except Exception as e:
            self.logger.error(f"Error fetching top stories: {e}")
            return []
    
    async def get_story(self, story_id: int) -> Dict:
        """Get full story details."""
        try:
            response = await self.api_client.get(
                f"{self.base_url}/item/{story_id}.json"
            )
            response.raise_for_status()
            story = response.json()
            
            if story and story.get("type") == "story":
                return {
                    "id": story_id,
                    "title": story.get("title"),
                    "url": story.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                    "score": story.get("score", 0),
                    "comments": story.get("descendants", 0),
                    "author": story.get("by"),
                    "time": datetime.fromtimestamp(story.get("time", 0)),
                    "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                    "is_ask_hn": story.get("title", "").startswith("Ask HN:"),
                    "is_show_hn": story.get("title", "").startswith("Show HN:"),
                }
        except Exception as e:
            self.logger.warning(f"Error fetching story {story_id}: {e}")
        return None
    
    async def scrape(self, limit: int = 30, **kwargs) -> List[ScrapedItem]:
        """Main scraping method."""
        self.logger.info(f"Scraping Hacker News (limit={limit})")
        
        stories = await self.get_top_stories(limit)
        items = []
        
        for story in stories:
            try:
                category = self._categorize(story['title'])
                
                item = ScrapedItem(
                    source="Hacker News",
                    source_type="community",
                    title=story['title'],
                    url=story['url'],
                    content=f"Score: {story['score']} | Comments: {story['comments']}",
                    author=story['author'],
                    published_at=story['time'],
                    engagement={
                        'upvotes': story['score'],
                        'comments': story['comments']
                    },
                    metadata={
                        'hn_url': story['hn_url'],
                        'is_ask_hn': story['is_ask_hn'],
                        'is_show_hn': story['is_show_hn'],
                        'category': category,
                        'story_id': story['id']
                    }
                )
                items.append(item)
                
            except Exception as e:
                self.logger.error(f"Error processing story: {e}")
                continue
        
        self.results = items
        self.logger.info(f"Scraped {len(items)} items from Hacker News")
        return items
    
    def _categorize(self, title: str) -> str:
        """Categorize story by title."""
        title_lower = title.lower()
        
        if any(k in title_lower for k in ['cve', 'vulnerability', 'security', 'breach', 'exploit']):
            return 'security'
        elif any(k in title_lower for k in ['layoff', 'firing', 'hiring freeze', 'riff']):
            return 'layoffs'
        elif any(k in title_lower for k in ['gpt', 'llm', 'ai model', 'machine learning', 'openai']):
            return 'ai_ml'
        elif title_lower.startswith('show hn:'):
            return 'show_hn'
        elif title_lower.startswith('ask hn:'):
            return 'ask_hn'
        elif any(k in title_lower for k in ['raises', 'funding', 'acquired', 'series a', 'series b']):
            return 'startup'
        return 'general'
