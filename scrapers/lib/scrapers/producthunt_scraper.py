"""
Product Hunt Scraper
Uses RSS feeds (official, free, no auth required).
"""

import feedparser
from datetime import datetime
from typing import List, Dict, Any

from scrapers.lib.base_scraper import BaseScraper, ScrapedItem


class ProductHuntScraper(BaseScraper):
    """Scraper for Product Hunt using RSS feeds."""
    
    RSS_FEEDS = {
        'Featured': 'https://www.producthunt.com/feed',
        'Tech': 'https://www.producthunt.com/feed?category=tech',
        'Developer Tools': 'https://www.producthunt.com/feed?category=developer-tools',
        'AI': 'https://www.producthunt.com/feed?category=artificial-intelligence',
        'Productivity': 'https://www.producthunt.com/feed?category=productivity',
    }
    
    def __init__(self):
        super().__init__("Product Hunt", "product_launch")
        
    async def scrape_category(self, name: str, url: str, limit: int = 20) -> List[ScrapedItem]:
        """Scrape a single Product Hunt category."""
        items = []
        
        try:
            self.logger.info(f"Fetching Product Hunt {name}")
            feed = feedparser.parse(url)
            
            if feed.bozo:
                self.logger.warning(f"Feed error for {name}: {feed.bozo_exception}")
                return items
            
            for entry in feed.entries[:limit]:
                try:
                    # Parse votes from title if available
                    votes = self._extract_votes(entry.title)
                    clean_summary = self.clean_text(entry.get('summary', ''))
                    if not clean_summary:
                        clean_summary = self.clean_text(entry.get('description', ''))
                    
                    item = ScrapedItem(
                        source=f"Product Hunt - {name}",
                        source_type="product_launch",
                        title=entry.title,
                        url=entry.link,
                        content=clean_summary,
                        author=entry.get('author', 'Unknown'),
                        published_at=self._parse_date(entry.get('published')),
                        engagement={'upvotes': votes},
                        metadata={
                            'category': name,
                            'description': clean_summary
                        }
                    )
                    items.append(item)
                    
                except Exception as e:
                    self.logger.error(f"Error parsing entry from {name}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error fetching {name}: {e}")
        
        return items
    
    async def scrape(self, categories: Dict[str, str] = None, limit: int = 20, **kwargs) -> List[ScrapedItem]:
        """
        Main scraping method.
        
        Args:
            categories: Dict of {name: rss_url} (default: predefined)
            limit: Number of products per category
        """
        if categories is None:
            categories = self.RSS_FEEDS
        
        self.logger.info(f"Scraping {len(categories)} Product Hunt categories")
        
        all_items = []
        for name, url in categories.items():
            items = await self.scrape_category(name, url, limit)
            all_items.extend(items)
        
        self.results = all_items
        self.logger.info(f"Scraped {len(all_items)} items from Product Hunt")
        return all_items
    
    def _extract_votes(self, title: str) -> int:
        """Try to extract vote count from title."""
        import re
        # Common patterns: "(123 votes)", "- 123 points"
        match = re.search(r'[(\[]?(\d+)\s*(?:votes?|points?)[)\]]?', title.lower())
        return int(match.group(1)) if match else 0
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime."""
        try:
            return datetime.fromtimestamp(
                feedparser._parse_date(date_str)[0]
            )
        except:
            return datetime.now()
