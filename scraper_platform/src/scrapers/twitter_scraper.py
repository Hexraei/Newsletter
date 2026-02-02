"""
Twitter/X Scraper
Uses twscrape library (Python) - actively maintained in 2025.
Requires Twitter account credentials.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseScraper, ScrapedItem

# Try to import twscrape
try:
    from twscrape import API, gather, Tweet
    TWSCRAPE_AVAILABLE = True
except ImportError:
    TWSCRAPE_AVAILABLE = False
    print("Warning: twscrape not installed. Run: pip install twscrape")


class TwitterScraper(BaseScraper):
    """Scraper for Twitter/X using twscrape library."""
    
    # Tech accounts to monitor
    TECH_ACCOUNTS = [
        'sama',           # Sam Altman (OpenAI)
        'elonmusk',       # Elon Musk
        'ylecun',         # Yann LeCun
        'karpathy',       # Andrej Karpathy
        'bindureddy',     # Bindu Reddy
        'DrJimFan',       # Jim Fan (NVIDIA)
        'goodside',       # Riley Goodside
        'alexalbert__',   # Alex Albert
        'sarahsaurus_',   # Sarah (AI researcher)
        'jeremyphoward',  # Jeremy Howard
    ]
    
    def __init__(self, accounts: List[Dict[str, str]] = None):
        super().__init__("Twitter", "social")
        self.api = None
        self.accounts = accounts or []  # List of {username, password, email, email_password}
        self.is_logged_in = False
        
    async def __aenter__(self):
        await super().__aenter__()
        
        if not TWSCRAPE_AVAILABLE:
            raise ImportError("twscrape not installed. Run: pip install twscrape")
        
        self.api = API()
        
        # Add accounts if provided
        if self.accounts:
            for acc in self.accounts:
                await self.api.pool.add_account(
                    acc['username'],
                    acc['password'],
                    acc['email'],
                    acc.get('email_password', '')
                )
            # Try to login
            await self.api.pool.login_all()
            self.is_logged_in = True
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)
    
    async def search_tweets(self, 
                           query: str, 
                           limit: int = 20) -> List[ScrapedItem]:
        """Search tweets by query."""
        items = []
        
        if not self.is_logged_in:
            self.logger.warning("Not logged in - cannot search")
            return items
        
        try:
            self.logger.info(f"Searching Twitter for: {query}")
            tweets = await gather(self.api.search(query, limit=limit))
            
            for tweet in tweets:
                item = self._tweet_to_item(tweet)
                if item:
                    items.append(item)
                    
        except Exception as e:
            self.logger.error(f"Error searching tweets: {e}")
        
        return items
    
    async def get_user_tweets(self, 
                              username: str, 
                              limit: int = 20) -> List[ScrapedItem]:
        """Get tweets from a specific user."""
        items = []
        
        if not self.is_logged_in:
            self.logger.warning("Not logged in - cannot get user tweets")
            return items
        
        try:
            self.logger.info(f"Fetching tweets from @{username}")
            tweets = await gather(self.api.user_tweets(username, limit=limit))
            
            for tweet in tweets:
                item = self._tweet_to_item(tweet)
                if item:
                    items.append(item)
                    
        except Exception as e:
            self.logger.error(f"Error fetching @{username}: {e}")
        
        return items
    
    async def get_tweet_details(self, tweet_id: str) -> Optional[ScrapedItem]:
        """Get details of a specific tweet."""
        if not self.is_logged_in:
            return None
        
        try:
            tweet = await self.api.tweet_details(tweet_id)
            return self._tweet_to_item(tweet)
        except Exception as e:
            self.logger.error(f"Error fetching tweet {tweet_id}: {e}")
            return None
    
    def _tweet_to_item(self, tweet: Any) -> Optional[ScrapedItem]:
        """Convert twscrape Tweet to ScrapedItem."""
        if not tweet:
            return None
        
        try:
            # Parse date
            created_at = datetime.now()
            if hasattr(tweet, 'date') and tweet.date:
                try:
                    created_at = datetime.strptime(tweet.date, '%Y-%m-%d %H:%M:%S%z')
                except:
                    pass
            
            # Build metadata
            metadata = {
                'tweet_id': tweet.id if hasattr(tweet, 'id') else '',
                'reply_count': tweet.replyCount if hasattr(tweet, 'replyCount') else 0,
                'retweet_count': tweet.retweetCount if hasattr(tweet, 'retweetCount') else 0,
                'like_count': tweet.likeCount if hasattr(tweet, 'likeCount') else 0,
                'quote_count': tweet.quoteCount if hasattr(tweet, 'quoteCount') else 0,
                'is_reply': tweet.inReplyToTweetId is not None if hasattr(tweet, 'inReplyToTweetId') else False,
                'is_retweet': tweet.isRetweet if hasattr(tweet, 'isRetweet') else False,
                'has_media': len(tweet.media) > 0 if hasattr(tweet, 'media') else False,
            }
            
            return ScrapedItem(
                source="Twitter",
                source_type="social",
                title=tweet.rawContent[:100] if hasattr(tweet, 'rawContent') else '',
                url=f"https://twitter.com/{tweet.user.username}/status/{tweet.id}" if hasattr(tweet, 'user') else '',
                content=tweet.rawContent if hasattr(tweet, 'rawContent') else '',
                author=tweet.user.username if hasattr(tweet, 'user') else '',
                published_at=created_at,
                engagement={
                    'replies': metadata['reply_count'],
                    'retweets': metadata['retweet_count'],
                    'likes': metadata['like_count'],
                    'quotes': metadata['quote_count']
                },
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error converting tweet: {e}")
            return None
    
    async def scrape(self, 
                    usernames: List[str] = None,
                    search_queries: List[str] = None,
                    limit: int = 20,
                    **kwargs) -> List[ScrapedItem]:
        """
        Main scraping method.
        
        Args:
            usernames: List of usernames to fetch tweets from
            search_queries: List of search queries
            limit: Number of tweets per query/user
        """
        all_items = []
        
        if not self.is_logged_in:
            self.logger.error("Not logged in. Add accounts before scraping.")
            return all_items
        
        # Fetch from specific users
        if usernames:
            for username in usernames:
                items = await self.get_user_tweets(username, limit=limit)
                all_items.extend(items)
        
        # Search for tweets
        if search_queries:
            for query in search_queries:
                items = await self.search_tweets(query, limit=limit)
                all_items.extend(items)
        
        self.results = all_items
        self.logger.info(f"Scraped {len(all_items)} tweets from Twitter")
        return all_items


class TwitterScraperMock(BaseScraper):
    """
    Mock Twitter scraper for testing without credentials.
    Returns sample data to demonstrate the structure.
    """
    
    def __init__(self):
        super().__init__("Twitter (Mock)", "social")
    
    async def scrape(self, limit: int = 5, **kwargs) -> List[ScrapedItem]:
        """Return mock data."""
        self.logger.info("Using MOCK Twitter scraper (no credentials)")
        
        mock_items = [
            ScrapedItem(
                source="Twitter (Mock)",
                source_type="social",
                title="GPT-5 announcement: 10x performance improvement...",
                url="https://twitter.com/sama/status/1234567890",
                content="GPT-5 announcement: 10x performance improvement over GPT-4. Available now for ChatGPT Plus users.",
                author="sama",
                published_at=datetime.now(),
                engagement={'replies': 1200, 'retweets': 5000, 'likes': 25000},
                metadata={'tweet_id': '1234567890', 'is_mock': True}
            ),
            ScrapedItem(
                source="Twitter (Mock)",
                source_type="social",
                title="New AI model released by Anthropic...",
                url="https://twitter.com/AnthropicAI/status/1234567891",
                content="Claude 4 is here with breakthrough reasoning capabilities.",
                author="AnthropicAI",
                published_at=datetime.now(),
                engagement={'replies': 800, 'retweets': 3000, 'likes': 15000},
                metadata={'tweet_id': '1234567891', 'is_mock': True}
            ),
        ]
        
        self.results = mock_items[:limit]
        return self.results


# Use mock if twscrape not available or no accounts configured
TwitterScraper = TwitterScraper if TWSCRAPE_AVAILABLE else TwitterScraperMock


if __name__ == "__main__":
    async def test():
        # Test with mock (no credentials needed)
        async with TwitterScraperMock() as scraper:
            items = await scraper.scrape(limit=2)
            
            for item in items:
                print(f"\nAuthor: @{item.author}")
                print(f"Content: {item.content[:100]}...")
                print(f"Engagement: {item.engagement}")
                print(f"URL: {item.url}")
                print("-" * 50)
    
    asyncio.run(test())
