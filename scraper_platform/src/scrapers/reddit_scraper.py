"""
Reddit Scraper - Alternative Method
Uses Reddit's JSON API (no auth required for read-only access).
This is more reliable than RSS which gets blocked.
"""

import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urlparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseScraper, ScrapedItem


class RedditScraper(BaseScraper):
    """Scraper for Reddit using JSON API."""
    
    # ── Subreddits organized by newsletter section relevance ──
    # Department News (CS core)
    # Student Stories (career, campus, projects)
    # Industrial Insights (industry, futurism, markets)
    # General Tech (cross-section)
    SUBREDDITS = {
        # ── CS / Department core ──
        'technology': 'technology',
        'programming': 'programming',
        'Machine Learning': 'MachineLearning',
        'Web Dev': 'webdev',
        'Python': 'Python',
        'JavaScript': 'javascript',
        'Comp Sci': 'compsci',
        'Netsec': 'netsec',
        'Artificial': 'artificial',
        'LocalLLaMA': 'LocalLLaMA',
        'SelfHosted': 'selfhosted',
        # ── Student Stories / Career ──
        'cs Career Questions': 'cscareerquestions',
        'CS Majors': 'csMajors',
        'Experience Dev': 'ExperiencedDevs',
        'Learn Programming': 'learnprogramming',
        'CS Students': 'cs50',
        # ── Industrial Insights / Futurism ──
        'Singularity': 'singularity',
        'Futurology': 'Futurology',
        'Startups': 'startups',
        'Entrepreneur': 'Entrepreneur',
        'Tech News': 'technews',
        'Artificial Intelligence': 'ArtificialInteligence',
        'Economics': 'economics',
        'Stocks': 'stocks',
        'Energy': 'energy',
        'Climate Tech': 'climatetech',
        'Biotech': 'biotech',
    }
    
    def __init__(self):
        super().__init__("Reddit", "community")
        self.json_base = "https://www.reddit.com/r/{}/hot.json"

    def _is_reddit_url(self, url: str) -> bool:
        """Check if URL points to Reddit itself."""
        try:
            host = urlparse(url).netloc.lower()
            return "reddit.com" in host or "redd.it" in host
        except Exception:
            return False

    async def _fetch_external_preview(self, url: str) -> tuple:
        """Fetch article preview text and image for external Reddit link posts.
        
        Returns:
            tuple: (content_text, image_url)
        """
        if not url or self._is_reddit_url(url):
            return "", None

        try:
            response = await self.client.get(url, timeout=15.0)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                return "", None

            html = response.text
            
            # Extract description
            description = ""
            desc_patterns = [
                r'<meta[^>]+property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:description["\']',
                r'<meta[^>]+name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*name=["\']description["\']',
                r'<meta[^>]+name=["\']twitter:description["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*name=["\']twitter:description["\']',
            ]

            for pattern in desc_patterns:
                match = re.search(pattern, html, flags=re.IGNORECASE)
                if match:
                    text = self.clean_text(match.group(1), max_length=500)
                    if text:
                        description = text
                        break

            if not description:
                description = self.clean_text(html, max_length=500)
            
            # Extract image
            image_url = None
            image_patterns = [
                # Open Graph image
                r'<meta[^>]+property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
                # Twitter Card image
                r'<meta[^>]+name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta[^>]+name=["\']twitter:image:src["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*name=["\']twitter:image["\']',
                # Generic image
                r'<meta[^>]+property=["\']image["\'][^>]*content=["\']([^"\']+)["\']',
            ]

            for pattern in image_patterns:
                match = re.search(pattern, html, flags=re.IGNORECASE)
                if match:
                    image_url = match.group(1).strip()
                    # Ensure HTTPS
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    elif image_url.startswith('http://'):
                        image_url = image_url.replace('http://', 'https://')
                    break

            return description, image_url

        except Exception as e:
            self.logger.debug(f"Could not fetch external preview for {url}: {e}")
            return "", None
        
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

            semaphore = asyncio.Semaphore(5)

            async def parse_post(post_data: Dict[str, Any]) -> ScrapedItem:
                post = post_data.get('data', {})

                if post.get('stickied'):
                    return None

                external_url = post.get('url', '')
                content = (post.get('selftext', '') or '').strip()
                image_url = None

                # Most news posts are external links with empty selftext.
                # Fetch a short preview and image so content is useful downstream.
                if not content and external_url and not self._is_reddit_url(external_url):
                    async with semaphore:
                        preview_content, preview_image = await self._fetch_external_preview(external_url)
                        content = preview_content
                        image_url = preview_image

                clean_content = self.clean_text(content, max_length=500)
                if not clean_content:
                    clean_content = self.clean_text(post.get('title', ''), max_length=500)

                # Build metadata with image if available
                metadata = {
                    'subreddit': subreddit,
                    'post_id': post.get('id'),
                    'external_url': external_url,
                    'is_self': post.get('is_self', False)
                }
                if image_url:
                    metadata['og_image'] = image_url
                    metadata['image'] = image_url

                return ScrapedItem(
                    source=f"Reddit - r/{subreddit}",
                    source_type="community",
                    title=post.get('title', ''),
                    url=f"https://www.reddit.com{post.get('permalink', '')}",
                    content=clean_content,
                    author=post.get('author', 'unknown'),
                    published_at=datetime.fromtimestamp(post.get('created_utc', 0)),
                    engagement={
                        'upvotes': post.get('ups', 0),
                        'comments': post.get('num_comments', 0)
                    },
                    metadata=metadata
                )

            parsed_posts = await asyncio.gather(*[
                parse_post(post_data) for post_data in posts[:limit]
            ], return_exceptions=True)

            for parsed in parsed_posts:
                if isinstance(parsed, Exception):
                    self.logger.error(f"Error parsing post: {parsed}")
                    continue
                if parsed:
                    items.append(parsed)
                     
        except Exception as e:
            self.logger.error(f"Error fetching r/{subreddit}: {e}")
        
        return items
    
    async def scrape(self, subreddits: List[str] = None, limit: int = 25, department_tags: List[str] = None, **kwargs) -> List[ScrapedItem]:
        """
        Main scraping method.
        
        Args:
            subreddits: List of subreddit names to scrape (default: all)
            limit: Number of posts per subreddit
            department_tags: Tags to assign to all scraped items
        """
        if subreddits is None:
            subreddits = list(self.SUBREDDITS.values())[:5]
        
        self.logger.info(f"Scraping {len(subreddits)} subreddits")
        
        all_items = []
        for subreddit in subreddits:
            items = await self.scrape_subreddit(subreddit, limit)
            if department_tags:
                for item in items:
                    item.department_tags = department_tags
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
