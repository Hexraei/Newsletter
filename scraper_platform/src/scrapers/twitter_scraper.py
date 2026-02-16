"""
Twitter/X Scraper
Uses bird CLI for fetching tweets from X.

Credential options (preferred order):
1) BIRD_AUTH_TOKEN + BIRD_CT0 environment variables
2) AUTH_TOKEN + CT0 environment variables (bird default names)
3) Browser profile extraction via BIRD_CHROME_PROFILE/BIRD_FIREFOX_PROFILE
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseScraper, ScrapedItem


class TwitterScraper(BaseScraper):
    """Scraper for Twitter/X using bird CLI."""

    TECH_ACCOUNTS = [
        "sama",
        "OpenAI",
        "Google",
        "Microsoft",
        "AnthropicAI",
        "github",
        "TheVerge",
        "TechCrunch",
    ]

    DEFAULT_SEARCH_QUERIES = [
        "AI launch",
        "startup funding",
        "open source release",
    ]

    def __init__(self, bird_binary: str = "bird", auth_token: Optional[str] = None, ct0: Optional[str] = None):
        super().__init__("Twitter", "social")
        self.bird_binary = bird_binary
        self.auth_token = auth_token or os.getenv("BIRD_AUTH_TOKEN") or os.getenv("AUTH_TOKEN")
        self.ct0 = ct0 or os.getenv("BIRD_CT0") or os.getenv("CT0")

        self.chrome_profile = os.getenv("BIRD_CHROME_PROFILE")
        self.firefox_profile = os.getenv("BIRD_FIREFOX_PROFILE")

        timeout_env = os.getenv("BIRD_TIMEOUT_SECONDS", "30")
        try:
            self.timeout_seconds = max(10, int(timeout_env))
        except ValueError:
            self.timeout_seconds = 30

        self.enabled = True

    async def __aenter__(self):
        await super().__aenter__()

        # Verify bird CLI is installed and discoverable.
        try:
            process = await asyncio.create_subprocess_exec(
                self.bird_binary,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            if process.returncode != 0:
                self.logger.warning("bird CLI returned non-zero exit code during version check")
                self.enabled = False
                return self
        except FileNotFoundError:
            self.logger.error("bird CLI not found. Install bird CLI and ensure it is in PATH.")
            self.enabled = False
            return self

        if not self._has_credential_source():
            self.logger.warning(
                "Twitter scraper disabled: no bird credentials found. "
                "Set BIRD_AUTH_TOKEN+BIRD_CT0, AUTH_TOKEN+CT0, or browser profile env vars."
            )
            self.enabled = False
            return self

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)

    def _has_credential_source(self) -> bool:
        has_tokens = bool(self.auth_token and self.ct0)
        has_profile = bool(self.chrome_profile or self.firefox_profile)
        return has_tokens or has_profile

    def _build_auth_args(self) -> List[str]:
        args: List[str] = []

        if self.auth_token and self.ct0:
            args.extend(["--auth-token", self.auth_token, "--ct0", self.ct0])

        if self.chrome_profile:
            args.extend(["--chrome-profile", self.chrome_profile])
        if self.firefox_profile:
            args.extend(["--firefox-profile", self.firefox_profile])

        return args

    async def _run_bird_json(self, command_args: List[str]) -> Any:
        cmd = [
            self.bird_binary,
            "--plain",
            "--no-color",
            *self._build_auth_args(),
            *command_args,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise RuntimeError("bird CLI request timed out")

        out_text = stdout.decode("utf-8", errors="ignore").strip()
        err_text = stderr.decode("utf-8", errors="ignore").strip()

        if process.returncode != 0:
            raise RuntimeError(err_text or out_text or "bird CLI command failed")

        if not out_text:
            return []

        # bird --json should be valid JSON output.
        try:
            return json.loads(out_text)
        except json.JSONDecodeError:
            # Fallback: some versions may include non-JSON lines; parse last JSON line.
            for line in reversed(out_text.splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
            raise RuntimeError("bird CLI returned non-JSON output")

    async def _search_tweets(self, query: str, limit: int) -> List[Dict[str, Any]]:
        payload = await self._run_bird_json([
            "search",
            "--count",
            str(max(1, limit)),
            "--json",
            query,
        ])
        return self._extract_tweets(payload)

    def _extract_tweets(self, payload: Any) -> List[Dict[str, Any]]:
        tweets: List[Dict[str, Any]] = []
        seen_ids = set()

        def walk(node: Any):
            if node is None:
                return

            if isinstance(node, list):
                for item in node:
                    walk(item)
                return

            if isinstance(node, dict):
                if self._looks_like_tweet(node):
                    tweet_id = self._tweet_id(node)
                    key = tweet_id or id(node)
                    if key not in seen_ids:
                        seen_ids.add(key)
                        tweets.append(node)
                    return

                for value in node.values():
                    walk(value)

        walk(payload)
        return tweets

    @staticmethod
    def _looks_like_tweet(tweet: Dict[str, Any]) -> bool:
        id_keys = ("id", "id_str", "rest_id", "tweet_id")
        text_keys = ("text", "full_text", "rawContent")
        has_id = any(tweet.get(k) for k in id_keys)
        has_text = any(tweet.get(k) for k in text_keys)

        legacy = tweet.get("legacy") if isinstance(tweet.get("legacy"), dict) else {}
        has_legacy_text = bool(legacy.get("full_text") or legacy.get("text"))

        return has_id and (has_text or has_legacy_text)

    @staticmethod
    def _nested_get(data: Dict[str, Any], *keys):
        current: Any = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current

    def _tweet_id(self, tweet: Dict[str, Any]) -> str:
        return str(
            tweet.get("id")
            or tweet.get("id_str")
            or tweet.get("rest_id")
            or tweet.get("tweet_id")
            or ""
        )

    def _tweet_text(self, tweet: Dict[str, Any]) -> str:
        text = (
            tweet.get("rawContent")
            or tweet.get("full_text")
            or tweet.get("text")
            or self._nested_get(tweet, "legacy", "full_text")
            or self._nested_get(tweet, "legacy", "text")
            or ""
        )
        return self.clean_text(str(text), max_length=1000)

    def _tweet_username(self, tweet: Dict[str, Any]) -> str:
        username = (
            self._nested_get(tweet, "user", "username")
            or self._nested_get(tweet, "user", "screen_name")
            or self._nested_get(tweet, "author", "username")
            or self._nested_get(tweet, "legacy", "user", "screen_name")
            or self._nested_get(tweet, "core", "user_results", "result", "legacy", "screen_name")
            or tweet.get("username")
            or ""
        )
        return str(username).lstrip("@")

    def _tweet_url(self, tweet: Dict[str, Any], username: str, tweet_id: str) -> str:
        direct_url = tweet.get("url") or tweet.get("tweet_url")
        if direct_url:
            return str(direct_url)
        if username and tweet_id:
            return f"https://x.com/{username}/status/{tweet_id}"
        if tweet_id:
            return f"https://x.com/i/web/status/{tweet_id}"
        return ""

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _tweet_engagement(self, tweet: Dict[str, Any]) -> Dict[str, int]:
        legacy = tweet.get("legacy") if isinstance(tweet.get("legacy"), dict) else {}
        return {
            "likes": self._to_int(tweet.get("likeCount") or tweet.get("favorite_count") or legacy.get("favorite_count")),
            "retweets": self._to_int(tweet.get("retweetCount") or tweet.get("retweet_count") or legacy.get("retweet_count")),
            "replies": self._to_int(tweet.get("replyCount") or tweet.get("reply_count") or legacy.get("reply_count")),
            "views": self._to_int(tweet.get("viewCount") or tweet.get("view_count")),
        }

    def _tweet_datetime(self, tweet: Dict[str, Any]) -> datetime:
        raw = (
            tweet.get("date")
            or tweet.get("created_at")
            or self._nested_get(tweet, "legacy", "created_at")
            or tweet.get("timestamp")
        )

        if isinstance(raw, (int, float)):
            try:
                return datetime.fromtimestamp(raw)
            except Exception:
                return datetime.now()

        if isinstance(raw, str) and raw.strip():
            value = raw.strip()
            formats = [
                "%a %b %d %H:%M:%S %z %Y",  # Twitter classic created_at
                "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

        return datetime.now()

    def _tweet_to_item(self, tweet: Dict[str, Any], origin_query: str) -> Optional[ScrapedItem]:
        tweet_id = self._tweet_id(tweet)
        text = self._tweet_text(tweet)
        if not text:
            return None

        username = self._tweet_username(tweet)
        url = self._tweet_url(tweet, username, tweet_id)
        engagement = self._tweet_engagement(tweet)
        published_at = self._tweet_datetime(tweet)

        return ScrapedItem(
            source="Twitter",
            source_type="social",
            title=text[:120],
            url=url,
            content=text,
            author=username or "unknown",
            published_at=published_at,
            engagement=engagement,
            metadata={
                "tweet_id": tweet_id,
                "origin_query": origin_query,
                "is_retweet": bool(tweet.get("isRetweet") or tweet.get("retweeted")),
            },
        )

    async def scrape(
        self,
        usernames: Optional[List[str]] = None,
        search_queries: Optional[List[str]] = None,
        limit: int = 20,
        **kwargs,
    ) -> List[ScrapedItem]:
        """Main scraping method for Twitter/X using bird CLI."""
        if not self.enabled:
            self.results = []
            return self.results

        usernames = usernames or []
        search_queries = search_queries or []

        if not usernames and not search_queries:
            usernames = self.TECH_ACCOUNTS[:5]

        all_items: List[ScrapedItem] = []
        seen_tweet_ids = set()

        # Scrape user timelines via bird search query syntax.
        for username in usernames:
            query = f"from:{username} -filter:replies"
            try:
                tweets = await self._search_tweets(query, limit)
                for tweet in tweets:
                    item = self._tweet_to_item(tweet, origin_query=query)
                    if not item:
                        continue
                    tweet_id = item.metadata.get("tweet_id")
                    dedupe_key = tweet_id or item.url
                    if dedupe_key in seen_tweet_ids:
                        continue
                    seen_tweet_ids.add(dedupe_key)
                    all_items.append(item)
            except Exception as e:
                self.logger.error(f"Error scraping @{username} with bird CLI: {e}")

        # Scrape freeform queries.
        for query in search_queries:
            try:
                tweets = await self._search_tweets(query, limit)
                for tweet in tweets:
                    item = self._tweet_to_item(tweet, origin_query=query)
                    if not item:
                        continue
                    tweet_id = item.metadata.get("tweet_id")
                    dedupe_key = tweet_id or item.url
                    if dedupe_key in seen_tweet_ids:
                        continue
                    seen_tweet_ids.add(dedupe_key)
                    all_items.append(item)
            except Exception as e:
                self.logger.error(f"Error scraping query '{query}' with bird CLI: {e}")

        self.results = all_items
        self.logger.info(f"Scraped {len(all_items)} tweets from Twitter via bird CLI")
        return all_items


if __name__ == "__main__":
    async def test():
        async with TwitterScraper() as scraper:
            items = await scraper.scrape(usernames=["sama"], limit=5)
            for item in items[:3]:
                print(f"Author: @{item.author}")
                print(f"Title: {item.title}")
                print(f"URL: {item.url}")
                print(f"Engagement: {item.engagement}")
                print("-" * 50)

    asyncio.run(test())
