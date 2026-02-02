"""
Reddit Scraper - Alternative Method
Uses Reddit's JSON API (no auth required for read-only access).
This is more reliable than RSS which gets blocked.
"""

import httpx
from datetime import datetime
from typing import List, Dict, Any
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseScraper, ScrapedItem


class RedditScraper(BaseScraper):
    """Scraper for Reddit using JSON API."""
    
    # Student-relevant subreddits
    SUBREDDITS = {
        'technology': 'technology',
        'programming': 'programming',
        'cs Career Questions': 'cscareerquestions',
        'Machine Learning': 'MachineLearning',
        'Web Dev': 'webdev',
        'Python': 'Python',
        'JavaScript': 'javascript',
        'startups': 'startups',
        'Entrepreneur': 'Entrepreneur',
    }
    
    def __init__(self):
        super().__init__("Reddit", "community")
        self.json_base = "https://www.reddit.com/r/{}/hot.json"
        
    async def scrape_subreddit(self, subreddit: str, limit: int = 25) -> List[ScrapedItem]:
        """Scrape a single subreddit via JSON API."""
        items = []
        
        try:
            url = self.json_base.format(subreddit)
            self.logger.info(f"Fetching r/{subreddit}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            posts = data.get('data', {}).get('children', [])
            
            for post_data in posts[:limit]:
                try:
                    post = post_data.get('data', {})
                    
                    # Skip stickied posts
                    if post.get('stickied'):
                        continue
                    
                    item = ScrapedItem(
                        source=f"Reddit - r/{subreddit}",
                        source_type="community",
                        title=post.get('title', ''),
                        url=f"https://www.reddit.com{post.get('permalink', '')}",
                        content=post.get('selftext', '')[:500],
                        author=post.get('author', 'unknown'),
                        published_at=datetime.fromtimestamp(post.get('created_utc', 0)),
                        engagement={
                            'upvotes': post.get('ups', 0),
                            'comments': post.get('num_comments', 0)
                        },
                        metadata={
                            'subreddit': subreddit,
                            'post_id': post.get('id'),
                            'external_url': post.get('url'),
                            'is_self': post.get('is_self', False)
                        }
                    )
                    items.append(item)
                    
                except Exception as e:
                    self.logger.error(f"Error parsing post: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error fetching r/{subreddit}: {e}")
        
        return items
    
    async def scrape(self, subreddits: List[str] = None, limit: int = 25, **kwargs) -> List[ScrapedItem]:
        """
        Main scraping method.
        
        Args:
            subreddits: List of subreddit names to scrape (default: all)
            limit: Number of posts per subreddit
        """
        if subreddits is None:
            subreddits = list(self.SUBREDDITS.values())[:5]
        
        self.logger.info(f"Scraping {len(subreddits)} subreddits")
        
        all_items = []
        for subreddit in subreddits:
            items = await self.scrape_subreddit(subreddit, limit)
            all_items.extend(items)
        
        self.results = all_items
        self.logger.info(f"Scraped {len(all_items)} items from Reddit")
        return all_items


if __name__ == "__main__":
    import asyncio
    
    async def test():
        async with RedditScraper() as scraper:
            items = await scraper.scrape(subreddits=['technology', 'programming'], limit=5)
            
            for item in items[:3]:
                print(f"Source: {item.source}")
                print(f"Title: {item.title}")
                print(f"URL: {item.url}")
                print(f"Engagement: {item.engagement}")
                print("-" * 50)
    
    asyncio.run(test())
