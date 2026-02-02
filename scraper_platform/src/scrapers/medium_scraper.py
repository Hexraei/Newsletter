"""
Medium Scraper
Uses RSS feeds from publications (no auth required).
"""

import feedparser
from datetime import datetime
from typing import List, Dict, Any
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseScraper, ScrapedItem


class MediumScraper(BaseScraper):
    """Scraper for Medium using publication RSS feeds."""
    
    # Student-relevant Medium publications
    PUBLICATIONS = {
        'Better Programming': 'https://betterprogramming.pub/feed',
        'Towards Data Science': 'https://towardsdatascience.com/feed',
        'JavaScript in Plain English': 'https://javascript.plainenglish.io/feed',
        'Python in Plain English': 'https://python.plainenglish.io/feed',
        'Geek Culture': 'https://medium.com/geekculture/feed',
        'Free Code Camp': 'https://medium.freecodecamp.org/feed',
        'Hacker Noon': 'https://hackernoon.com/feed',
        'The Startup': 'https://medium.com/swlh/feed',
        'Level Up Coding': 'https://levelup.gitconnected.com/feed',
        'Bits and Pretzels': 'https://bitsandpretzels.com/feed',
    }
    
    def __init__(self):
        super().__init__("Medium", "blog")
        
    async def scrape_publication(self, name: str, url: str, limit: int = 10) -> List[ScrapedItem]:
        """Scrape a single Medium publication."""
        items = []
        
        try:
            self.logger.info(f"Fetching {name}")
            feed = feedparser.parse(url)
            
            if feed.bozo:
                self.logger.warning(f"Feed error for {name}: {feed.bozo_exception}")
                return items
            
            for entry in feed.entries[:limit]:
                try:
                    # Clean URL (remove tracking params)
                    clean_url = entry.link.split('?')[0]
                    
                    # Extract reading time if available
                    reading_time = self._estimate_reading_time(entry.get('summary', ''))
                    
                    item = ScrapedItem(
                        source=f"Medium - {name}",
                        source_type="blog",
                        title=entry.title,
                        url=clean_url,
                        content=entry.get('summary', '')[:1000],
                        author=entry.get('author', 'Unknown'),
                        published_at=self._parse_date(entry.get('published')),
                        metadata={
                            'publication': name,
                            'reading_time_minutes': reading_time,
                            'tags': [tag.term for tag in entry.get('tags', [])]
                        }
                    )
                    items.append(item)
                    
                except Exception as e:
                    self.logger.error(f"Error parsing entry from {name}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error fetching {name}: {e}")
        
        return items
    
    async def scrape(self, publications: Dict[str, str] = None, limit: int = 10, **kwargs) -> List[ScrapedItem]:
        """
        Main scraping method.
        
        Args:
            publications: Dict of {name: rss_url} (default: predefined)
            limit: Number of articles per publication
        """
        if publications is None:
            publications = self.PUBLICATIONS
        
        self.logger.info(f"Scraping {len(publications)} Medium publications")
        
        all_items = []
        for name, url in publications.items():
            items = await self.scrape_publication(name, url, limit)
            all_items.extend(items)
        
        self.results = all_items
        self.logger.info(f"Scraped {len(all_items)} items from Medium")
        return all_items
    
    def _estimate_reading_time(self, content: str) -> int:
        """Estimate reading time in minutes (avg 200 wpm)."""
        word_count = len(content.split())
        return max(1, round(word_count / 200))
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime."""
        try:
            return datetime.fromtimestamp(
                feedparser._parse_date(date_str)[0]
            )
        except:
            return datetime.now()
    
    def calculate_quality_score(self, item: ScrapedItem) -> int:
        """
        Calculate quality score for Medium articles.
        Score 0-100 based on publication, length, recency.
        """
        score = 0
        
        # Publication reputation (0-30)
        pub_scores = {
            'Towards Data Science': 30,
            'Better Programming': 28,
            'Free Code Camp': 30,
            'Hacker Noon': 25,
            'The Startup': 25,
            'Level Up Coding': 22,
            'Geek Culture': 20,
        }
        pub = item.metadata.get('publication', '')
        score += pub_scores.get(pub, 15)
        
        # Content length (0-20)
        word_count = len(item.content.split())
        if word_count > 2000: score += 20
        elif word_count > 1500: score += 15
        elif word_count > 1000: score += 10
        elif word_count > 500: score += 5
        
        # Reading time sweet spot (0-20)
        reading_time = item.metadata.get('reading_time_minutes', 0)
        if 3 <= reading_time <= 8: score += 20  # Ideal for newsletter
        elif 2 <= reading_time <= 10: score += 15
        elif reading_time <= 15: score += 10
        
        # Recency (0-15)
        age_days = (datetime.now() - item.published_at).days
        if age_days <= 1: score += 15
        elif age_days <= 3: score += 12
        elif age_days <= 7: score += 10
        elif age_days <= 14: score += 5
        
        # Category bonus (0-15)
        tags = item.metadata.get('tags', [])
        if any(t in ['career', 'interview', 'salary'] for t in tags):
            score += 15
        elif any(t in ['tutorial', 'how-to', 'guide'] for t in tags):
            score += 12
        elif any(t in ['programming', 'python', 'javascript'] for t in tags):
            score += 10
        
        return min(100, score)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        scraper = MediumScraper()
        
        # Test with just 2 publications
        pubs = dict(list(scraper.PUBLICATIONS.items())[:2])
        items = await scraper.scrape(publications=pubs, limit=3)
        
        for item in items[:3]:
            print(f"Source: {item.source}")
            print(f"Title: {item.title}")
            print(f"Author: {item.author}")
            print(f"Reading time: {item.metadata.get('reading_time_minutes')} min")
            quality = scraper.calculate_quality_score(item)
            print(f"Quality Score: {quality}/100")
            print("-" * 50)
    
    asyncio.run(test())
