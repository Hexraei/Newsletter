"""
GitHub Scraper
Uses GitHub Search API (works without auth with rate limits).
"""

import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any

from scrapers.lib.base_scraper import BaseScraper, ScrapedItem


class GitHubScraper(BaseScraper):
    """Scraper for GitHub trending repositories."""
    
    def __init__(self, token: str = None):
        super().__init__("GitHub", "open_source")
        self.token = token
        self.api_base = "https://api.github.com"
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'College-Newsletter-Scraper'
        }
        if token:
            self.headers['Authorization'] = f'token {token}'
    
    async def get_trending_repos(self, 
                                  language: str = None,
                                  since: str = "daily",
                                  limit: int = 30) -> List[Dict]:
        """
        Get trending repositories.
        
        Args:
            language: Filter by programming language
            since: daily, weekly, or monthly
            limit: Number of repos to fetch
        """
        repos = []
        
        try:
            # Calculate date range based on 'since'
            date_map = {
                'daily': 1,
                'weekly': 7,
                'monthly': 30
            }
            days = date_map.get(since, 1)
            date_since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Build query
            query = f"created:>{date_since}"
            if language:
                query += f" language:{language}"
            
            params = {
                'q': query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': min(limit, 100)
            }
            
            response = await self.client.get(
                f"{self.api_base}/search/repositories",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            for repo in data.get('items', []):
                repos.append({
                    'id': repo['id'],
                    'name': repo['full_name'],
                    'url': repo['html_url'],
                    'description': repo.get('description', ''),
                    'stars': repo['stargazers_count'],
                    'forks': repo['forks_count'],
                    'language': repo.get('language', 'Unknown'),
                    'created_at': datetime.fromisoformat(repo['created_at'].replace('Z', '+00:00')),
                    'owner': repo['owner']['login'],
                    'topics': repo.get('topics', [])
                })
                
        except Exception as e:
            self.logger.error(f"Error fetching trending repos: {e}")
        
        return repos
    
    async def scrape(self, 
                    languages: List[str] = None,
                    limit: int = 10,
                    **kwargs) -> List[ScrapedItem]:
        """
        Main scraping method.
        
        Args:
            languages: List of programming languages to track
            limit: Number of repos per language
        """
        if languages is None:
            languages = ['Python', 'JavaScript']  # Default to reduce API calls
        
        self.logger.info(f"Scraping GitHub trending for {len(languages)} languages")
        
        all_items = []
        
        # Scrape trending repos
        for language in languages:
            try:
                repos = await self.get_trending_repos(language=language, since='weekly', limit=limit)
                
                for repo in repos:
                    item = ScrapedItem(
                        source="GitHub",
                        source_type="open_source",
                        title=repo['name'],
                        url=repo['url'],
                        content=repo['description'] or "",
                        author=repo['owner'],
                        published_at=repo['created_at'],
                        engagement={
                            'stars': repo['stars'],
                            'forks': repo['forks']
                        },
                        metadata={
                            'language': repo['language'],
                            'topics': repo['topics'],
                            'repo_id': repo['id']
                        }
                    )
                    all_items.append(item)
                    
            except Exception as e:
                self.logger.error(f"Error scraping {language}: {e}")
                continue
        
        self.results = all_items
        self.logger.info(f"Scraped {len(all_items)} items from GitHub")
        return all_items
