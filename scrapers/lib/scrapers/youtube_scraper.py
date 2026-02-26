"""
YouTube Scraper
Fetches video metadata and transcripts using youtube-transcript-api.
No audio download needed - directly fetches captions/subtitles.
"""

import httpx
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from scrapers.lib.base_scraper import BaseScraper, ScrapedItem


class YouTubeScraper(BaseScraper):
    """Scraper for YouTube videos using transcript API."""
    
    def __init__(self):
        super().__init__("YouTube", "video")
        self.ytt_api = YouTubeTranscriptApi()
        self.formatter = TextFormatter()
        
        # Tech-focused channels for college students
        DEFAULT_CHANNELS = {
            'Fireship': 'UCsBjURrPoezykLs9EqgamOA',
            'Traversy Media': 'UC29ju8bIPH5as8OGnQzwJyA',
            'The Coding Train': 'UCvjgXvBlbQiydffZUzzmgyA',
            'CS50': 'UCcabW7890RKJzL968QWEykA',
            'freeCodeCamp': 'UC8butISFwT-Wl7EV0hUK0BQ',
            'Programming with Mosh': 'UCWv7vMbMWH4-V0ZXdmDpPBA',
            'Tech With Tim': 'UC4JX40jDee_tINbkjycV4Sg',
            'NeetCode': 'UC_mYaQAE6-71rjSN6CeL-pw',
            'Sentdex': 'UCfzlCWGWYyIQ0aLC5w48gBQ',
            'Two Minute Papers': 'UCbfYPyITQ-7l4upoX8nvctg',
            'Y Combinator': 'UCcefcZRL2oaA_uBNeo5UOWg',
            'TechLinked': 'UCeeFfhMcJa1kjtfZAGskOCA',
        }
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$'  # Direct video ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """Get video metadata using oEmbed (no API key needed)."""
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            response = await self.client.get(oembed_url)
            response.raise_for_status()
            data = response.json()
            
            return {
                'title': data.get('title', ''),
                'author': data.get('author_name', ''),
                'author_url': data.get('author_url', ''),
                'thumbnail_url': data.get('thumbnail_url', ''),
                'type': data.get('type', 'video'),
            }
        except Exception as e:
            self.logger.warning(f"Could not fetch metadata for {video_id}: {e}")
            return {}
    
    def fetch_transcript(self, video_id: str, languages: List[str] = None) -> Dict[str, Any]:
        """
        Fetch transcript for a video.
        
        Returns:
            Dict with transcript text, language, and metadata
        """
        if languages is None:
            languages = ['en']
        
        try:
            # Try to fetch transcript
            transcript = self.ytt_api.fetch(video_id, languages=languages)
            
            # Format as plain text
            full_text = self.formatter.format_transcript(transcript)
            
            # Get first snippet for language info
            first_snippet = transcript[0] if transcript else None
            
            return {
                'success': True,
                'video_id': video_id,
                'transcript': full_text,
                'language': transcript.language if hasattr(transcript, 'language') else 'unknown',
                'is_generated': transcript.is_generated if hasattr(transcript, 'is_generated') else False,
                'snippet_count': len(transcript),
                'first_500_chars': full_text[:500] if full_text else ''
            }
            
        except Exception as e:
            return {
                'success': False,
                'video_id': video_id,
                'error': str(e)
            }
    
    async def scrape_video(self, video_url: str) -> Optional[ScrapedItem]:
        """Scrape a single video by URL."""
        video_id = self.extract_video_id(video_url)
        if not video_id:
            self.logger.error(f"Could not extract video ID from: {video_url}")
            return None
        
        # Get metadata
        metadata = await self.get_video_metadata(video_id)
        if not metadata:
            return None
        
        # Get transcript
        transcript_data = self.fetch_transcript(video_id)
        
        # Create item
        item = ScrapedItem(
            source="YouTube",
            source_type="video",
            title=metadata.get('title', ''),
            url=f"https://www.youtube.com/watch?v={video_id}",
            content=transcript_data.get('first_500_chars', '') if transcript_data.get('success') else '',
            author=metadata.get('author', ''),
            published_at=datetime.now(),  # oEmbed doesn't provide date
            metadata={
                'video_id': video_id,
                'thumbnail_url': metadata.get('thumbnail_url', ''),
                'has_transcript': transcript_data.get('success', False),
                'transcript_language': transcript_data.get('language', ''),
                'is_auto_generated': transcript_data.get('is_generated', False),
                'transcript_error': transcript_data.get('error', '') if not transcript_data.get('success') else ''
            }
        )
        
        return item
    
    async def scrape_playlist(self, playlist_id: str, limit: int = 10) -> List[ScrapedItem]:
        """
        Scrape videos from a playlist.
        Note: Requires yt-dlp or playlist scraping - simplified version here.
        """
        # For now, return empty - playlist scraping requires yt-dlp
        self.logger.info(f"Playlist scraping not implemented for {playlist_id}")
        return []
    
    async def scrape(self, 
                    video_urls: List[str] = None,
                    search_terms: List[str] = None,
                    **kwargs) -> List[ScrapedItem]:
        """
        Main scraping method.
        
        Args:
            video_urls: List of YouTube URLs to scrape
            search_terms: List of search terms (would need YouTube Data API)
        """
        items = []
        
        # Scrape specific videos
        if video_urls:
            self.logger.info(f"Scraping {len(video_urls)} videos")
            for url in video_urls:
                try:
                    item = await self.scrape_video(url)
                    if item:
                        items.append(item)
                except Exception as e:
                    self.logger.error(f"Error scraping {url}: {e}")
                    continue
        
        # Note: Search requires YouTube Data API v3
        if search_terms:
            self.logger.info("Search requires YouTube Data API - skipping")
        
        self.results = items
        self.logger.info(f"Scraped {len(items)} videos from YouTube")
        return items
    
    def get_transcript_text(self, video_id: str) -> str:
        """Get full transcript text for a video."""
        result = self.fetch_transcript(video_id)
        return result.get('transcript', '') if result.get('success') else ''


# List of trending tech videos for testing
TEST_VIDEOS = [
    "https://www.youtube.com/watch?v=8jLOx1hD3_o",  # Fireship - ChatGPT
    "https://www.youtube.com/watch?v=qz0aGYrrlhU",  # Programming with Mosh - Python
    "https://www.youtube.com/watch?v=PKwu15ldZ7k",  # Web Dev Simplified
    "https://www.youtube.com/watch?v=ysEN5RaKOlA",  # CS50 - Cybersecurity
]
