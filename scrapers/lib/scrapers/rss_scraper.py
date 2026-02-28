"""
Generic RSS/Atom Feed Scraper
Pulls from arbitrary RSS/Atom feeds — IEEE Spectrum, ArXiv, NASA, ASCE, Nature, etc.
Configured via the department source registry.
"""

import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree

from scrapers.lib.base_scraper import BaseScraper, ScrapedItem


class RSSFeedScraper(BaseScraper):
    """Scraper for arbitrary RSS/Atom feeds."""

    # Common XML namespaces
    NS = {
        "atom": "http://www.w3.org/2005/Atom",
        "dc": "http://purl.org/dc/elements/1.1/",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "media": "http://search.yahoo.com/mrss/",
    }

    def __init__(self):
        super().__init__("RSS Feed", "rss")

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Try common RSS/Atom date formats (incl. IST/Indian feeds)."""
        if not date_str:
            return None
        date_str = date_str.strip()
        # Normalize "GMT" / "IST" to offset for strptime
        date_str = date_str.replace(" GMT", " +0000").replace(" IST", " +0530")
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _extract_text(self, html: str, max_length: int = 800) -> str:
        """Strip HTML tags and return plain text."""
        if not html:
            return ""
        return self.clean_text(html, max_length=max_length)

    async def scrape_feed(
        self,
        feed_url: str,
        feed_name: str = "RSS",
        feed_type: str = "news",
        limit: int = 20,
        department_tags: List[str] = None,
    ) -> List[ScrapedItem]:
        """Scrape a single RSS/Atom feed."""
        items: List[ScrapedItem] = []
        try:
            self.logger.info(f"Fetching RSS: {feed_name} ({feed_url})")
            response = await self.client.get(feed_url, timeout=20.0)
            response.raise_for_status()
            xml_text = response.text

            root = ElementTree.fromstring(xml_text)

            # Detect format: RSS 2.0 vs Atom
            if root.tag == "rss" or root.find("channel") is not None:
                items = self._parse_rss(root, feed_name, feed_type, limit, department_tags)
            elif root.tag.endswith("feed") or root.tag == "{http://www.w3.org/2005/Atom}feed":
                items = self._parse_atom(root, feed_name, feed_type, limit, department_tags)
            else:
                # Try RSS items at root level (RDF-based RSS 1.0)
                items = self._parse_rss(root, feed_name, feed_type, limit, department_tags)

        except Exception as e:
            self.logger.error(f"Error fetching RSS feed {feed_name}: {e}")

        return items

    _IMG_TAG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)

    def _extract_image_from_entry(self, entry) -> str:
        """Extract image URL from RSS entry via media:content, enclosure, or img tag."""
        # media:content (most common in modern feeds)
        media_content = entry.find("media:content", namespaces=self.NS)
        if media_content is not None:
            url = media_content.get("url", "")
            if url and not url.endswith(".svg"):
                return url

        # media:thumbnail
        media_thumb = entry.find("media:thumbnail", namespaces=self.NS)
        if media_thumb is not None:
            url = media_thumb.get("url", "")
            if url and not url.endswith(".svg"):
                return url

        # enclosure (podcasts + some news feeds)
        enclosure = entry.find("enclosure")
        if enclosure is not None:
            enc_type = enclosure.get("type", "")
            if enc_type.startswith("image/"):
                url = enclosure.get("url", "")
                if url:
                    return url

        # img tag inside description or content:encoded
        for tag in ("description", "content:encoded"):
            ns = self.NS if tag == "content:encoded" else None
            text = (entry.findtext(tag, namespaces=ns) if ns else entry.findtext(tag)) or ""
            m = self._IMG_TAG_RE.search(text)
            if m:
                url = m.group(1)
                if url.startswith("http") and not url.endswith(".svg"):
                    return url

        return ""

        self, root, feed_name, feed_type, limit, department_tags
    ) -> List[ScrapedItem]:
        """Parse RSS 2.0 format."""
        items = []
        channel = root.find("channel")
        entries = (channel.findall("item") if channel is not None else root.findall("item"))

        for entry in entries[:limit]:
            title = (entry.findtext("title") or "").strip()
            link = (entry.findtext("link") or "").strip()
            if not title or not link:
                continue

            description = entry.findtext("description") or ""
            content_encoded = entry.findtext("content:encoded", namespaces=self.NS) or ""
            content = self._extract_text(content_encoded or description)

            author = (
                entry.findtext("dc:creator", namespaces=self.NS)
                or entry.findtext("author")
                or ""
            ).strip()

            pub_date = self._parse_date(entry.findtext("pubDate") or entry.findtext("dc:date", namespaces=self.NS) or "")

            image_url = self._extract_image_from_entry(entry)
            metadata = {"feed_name": feed_name, "feed_type": feed_type}
            if image_url:
                metadata["og_image"] = image_url

            items.append(
                ScrapedItem(
                    source=f"RSS - {feed_name}",
                    source_type=feed_type,
                    title=title,
                    url=link,
                    content=content,
                    author=author,
                    published_at=pub_date,
                    engagement={},
                    metadata=metadata,
                    department_tags=department_tags or [],
                )
            )
        self, root, feed_name, feed_type, limit, department_tags
    ) -> List[ScrapedItem]:
        """Parse Atom format."""
        items = []
        ns = self.NS["atom"]
        entries = root.findall(f"{{{ns}}}entry") or root.findall("entry")

        for entry in entries[:limit]:
            title = (entry.findtext(f"{{{ns}}}title") or entry.findtext("title") or "").strip()

            # Get link — prefer alternate
            link = ""
            for link_el in entry.findall(f"{{{ns}}}link") + entry.findall("link"):
                rel = link_el.get("rel", "alternate")
                if rel == "alternate" or not link:
                    link = link_el.get("href", "")

            if not title or not link:
                continue

            summary = entry.findtext(f"{{{ns}}}summary") or entry.findtext("summary") or ""
            content_el = entry.find(f"{{{ns}}}content") or entry.find("content")
            content_text = content_el.text if content_el is not None else ""
            content = self._extract_text(content_text or summary)

            author_el = entry.find(f"{{{ns}}}author") or entry.find("author")
            author = ""
            if author_el is not None:
                author = (author_el.findtext(f"{{{ns}}}name") or author_el.findtext("name") or "").strip()

            updated = (
                entry.findtext(f"{{{ns}}}updated")
                or entry.findtext(f"{{{ns}}}published")
                or entry.findtext("updated")
                or entry.findtext("published")
                or ""
            )
            pub_date = self._parse_date(updated)

            image_url = self._extract_image_from_entry(entry)
            metadata = {"feed_name": feed_name, "feed_type": feed_type}
            if image_url:
                metadata["og_image"] = image_url

            items.append(
                ScrapedItem(
                    source=f"RSS - {feed_name}",
                    source_type=feed_type,
                    title=title,
                    url=link,
                    content=content,
                    author=author,
                    published_at=pub_date,
                    engagement={},
                    metadata=metadata,
                    department_tags=department_tags or [],
                )
            )

        return items

    async def scrape(
        self,
        feeds: List[Dict[str, str]] = None,
        limit: int = 15,
        department_tags: List[str] = None,
        **kwargs,
    ) -> List[ScrapedItem]:
        """
        Scrape multiple RSS feeds.

        Args:
            feeds: List of dicts with keys: name, url, type
            limit: Max items per feed
            department_tags: Tags to assign to all items
        """
        if not feeds:
            self.logger.warning("No feeds provided to RSSFeedScraper")
            return []

        self.logger.info(f"Scraping {len(feeds)} RSS feeds")
        all_items: List[ScrapedItem] = []

        for feed in feeds:
            items = await self.scrape_feed(
                feed_url=feed["url"],
                feed_name=feed.get("name", "RSS"),
                feed_type=feed.get("type", "news"),
                limit=limit,
                department_tags=department_tags,
            )
            all_items.extend(items)

        self.results = all_items
        self.logger.info(f"Scraped {len(all_items)} items from RSS feeds")
        return all_items
