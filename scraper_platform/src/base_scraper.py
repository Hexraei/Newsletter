"""
Base scraper class for all sources.
Provides common functionality for HTTP requests, logging, and error handling.
"""

import httpx
import asyncio
import logging
import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from fake_useragent import UserAgent
import json
from html import unescape

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScrapedItem:
    """Standardized scraped item format."""
    
    def __init__(self, 
                 source: str,
                 source_type: str,
                 title: str,
                 url: str,
                 content: str = "",
                 author: str = "",
                 published_at: Optional[datetime] = None,
                 scraped_at: Optional[datetime] = None,
                 engagement: Dict[str, int] = None,
                 metadata: Dict[str, Any] = None,
                 department_tags: List[str] = None):
        self.source = source
        self.source_type = source_type
        self.title = title
        self.url = url
        self.content = content
        self.author = author
        self.published_at = published_at or datetime.now()
        self.scraped_at = scraped_at or datetime.now()
        self.engagement = engagement or {}
        self.metadata = metadata or {}
        self.department_tags = department_tags or []
        self.content_hash = self._generate_hash()
    
    def _generate_hash(self) -> str:
        """Generate unique hash for deduplication."""
        content = f"{self.title}{self.url}{self.author}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()[:32]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'source': self.source,
            'source_type': self.source_type,
            'title': self.title,
            'url': self.url,
            'content': self.content[:1000] if self.content else "",  # Truncate for Excel
            'author': self.author,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'engagement': json.dumps(self.engagement),
            'metadata': json.dumps(self.metadata),
            'content_hash': self.content_hash,
            'department_tags': self.department_tags,
        }


class BaseScraper(ABC):
    """Base class for all scrapers."""
    
    def __init__(self, source_name: str, source_type: str):
        self.source_name = source_name
        self.source_type = source_type
        self.logger = logging.getLogger(f"{__name__}.{source_name}")
        self.ua = UserAgent()
        self.client = None
        self.results = []
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=lambda e: isinstance(e, (httpx.HTTPError, httpx.TimeoutException))
    )
    async def fetch(self, url: str, **kwargs) -> httpx.Response:
        """Fetch URL with retries and error handling."""
        try:
            self.logger.info(f"Fetching: {url}")
            response = await self.client.get(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP {e.response.status_code} for {url}")
            raise
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            raise
    
    @abstractmethod
    async def scrape(self, **kwargs) -> List[ScrapedItem]:
        """Main scraping method. Must be implemented by subclasses."""
        pass
    
    def test_connection(self) -> bool:
        """Test if scraper can connect to source."""
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        return {
            'source': self.source_name,
            'source_type': self.source_type,
            'items_scraped': len(self.results),
            'last_scraped': datetime.now().isoformat(),
            'status': 'active'
        }

    @staticmethod
    def clean_text(raw_text: str, max_length: Optional[int] = None) -> str:
        """Convert HTML-heavy feed content into clean plain text."""
        if not raw_text:
            return ""

        text = raw_text

        # Remove script/style and code-heavy blocks first
        text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<pre[^>]*>.*?</pre>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<code[^>]*>.*?</code>", " ", text, flags=re.IGNORECASE | re.DOTALL)

        # Strip remaining HTML tags and normalize text
        text = re.sub(r"<[^>]+>", " ", text)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()

        if max_length and len(text) > max_length:
            return text[:max_length].rstrip() + "..."

        return text
