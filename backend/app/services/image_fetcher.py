"""Semantic Image Fetcher — finds the most relevant image for any text.

Searches multiple free image APIs (Openverse, Wikimedia, Pixabay, Pexels),
builds text profiles from metadata, and ranks results using sentence-transformer
embeddings + cosine similarity.

Usage:
    fetcher = ImageFetcher()
    result = await fetcher.fetch_best_image("OpenAI releases GPT-5")
    # result = {"url": "https://...", "source_url": "...", "score": 0.45, "provider": "wikimedia"}
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)

CREDS_PATH = Path(__file__).parent.parent.parent.parent / ".openverse_creds.json"
_model = None


def _get_model():
    """Lazy-load the sentence-transformer model (cached after first call)."""
    global _model
    if _model is None:
        import torch
        # Force CPU to avoid CUDA compatibility issues
        device = "cpu"
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
        logger.info("Loaded sentence-transformer model: all-MiniLM-L6-v2 (device=%s)", device)
    return _model


class ImageCandidate:
    """A candidate image with metadata for ranking."""

    __slots__ = ("url", "source_url", "title", "tags", "description", "creator", "provider", "license")

    def __init__(self, url: str, source_url: str = "", title: str = "",
                 tags: str = "", description: str = "", creator: str = "",
                 provider: str = "", license: str = ""):
        self.url = url
        self.source_url = source_url
        self.title = title
        self.tags = tags
        self.description = description
        self.creator = creator
        self.provider = provider
        self.license = license

    def profile(self) -> str:
        """Build a text profile for embedding comparison."""
        parts = [self.title, self.tags, self.description, self.creator, self.provider]
        return " ".join(p for p in parts if p).strip()


class ImageFetcher:
    """Multi-source semantic image search with embedding-based ranking."""

    def __init__(self, sources: list[str] | None = None, timeout: float = 10.0):
        all_sources = ["openverse", "wikimedia", "pixabay", "pexels"]
        self.sources = sources or all_sources
        self.timeout = timeout
        self._openverse_token: str | None = None

    async def fetch_best_image(
        self, text: str, top_k: int = 1
    ) -> Optional[dict[str, Any]]:
        """Find the most semantically relevant image for the given text.

        Returns dict with keys: url, source_url, score, provider
        or None if no results found.
        """
        if not text or not text.strip():
            return None

        # Simplify query: extract key terms (3-5 words) for better API matches
        query = self._simplify_query(text.strip())
        candidates = await self._search_all(query)
        if not candidates:
            return None

        ranked = self._rank(text.strip(), candidates, top_k)
        if not ranked:
            return None

        best = ranked[0]
        return {
            "url": best["url"],
            "source_url": best["source_url"],
            "score": best["score"],
            "provider": best["provider"],
            "creator": best.get("creator", ""),
            "license": best.get("license", ""),
        }

    # Category keyword mapping for fallback searches
    CATEGORY_KEYWORDS = {
        "technology": "technology computer software",
        "tech": "technology computer software",
        "ai": "artificial intelligence robot",
        "artificial_intelligence": "artificial intelligence robot",
        "machine_learning": "machine learning data science",
        "programming": "programming code developer",
        "cybersecurity": "cybersecurity digital security",
        "security": "cybersecurity digital lock",
        "science": "science laboratory research",
        "engineering": "engineering circuit board",
        "robotics": "robotics automation machine",
        "data_science": "data analytics visualization",
        "web_development": "web development website",
        "mobile": "mobile phone smartphone app",
        "cloud": "cloud computing server data",
        "blockchain": "blockchain cryptocurrency digital",
        "gaming": "gaming video game controller",
        "space": "space exploration astronomy",
        "electronics": "electronics circuit board components",
        "business": "business office corporate",
        "education": "education university students",
        "research": "research laboratory science paper",
        "health": "health medical technology",
        "environment": "environment sustainability green",
        "startup": "startup business innovation",
        "career": "career professional office",
        "general": "technology digital innovation",
    }

    async def fetch_with_fallback(
        self, title: str, category: str = "general", top_k: int = 1
    ) -> Optional[dict[str, Any]]:
        """Try semantic search first, then fall back to category-based search."""
        # 1. Try semantic search with title
        result = await self.fetch_best_image(title, top_k=top_k)
        if result and result.get("score", 0) >= 0.15:
            return result

        # 2. Fallback: search by category keywords (broader, almost always returns results)
        cat_key = (category or "general").lower().replace(" ", "_")
        cat_query = self.CATEGORY_KEYWORDS.get(cat_key, self.CATEGORY_KEYWORDS["general"])
        candidates = await self._search_all(cat_query)
        if candidates:
            # Pick the first good-sized image (no ranking needed for generic category images)
            c = candidates[0]
            return {
                "url": c.url,
                "source_url": c.source_url,
                "score": 0.10,  # low score indicates category fallback
                "provider": c.provider,
                "creator": c.creator,
                "license": c.license,
            }
        return None

    @staticmethod
    def _simplify_query(text: str) -> str:
        """Extract key terms from a title for better image search results."""
        import re
        # Remove special chars, punctuation noise
        clean = re.sub(r"[^\w\s]", " ", text)
        clean = re.sub(r"\s+", " ", clean).strip()
        # Take first 5 significant words (skip very short ones)
        words = [w for w in clean.split() if len(w) >= 3]
        return " ".join(words[:5])

    async def _search_all(self, query: str) -> list[ImageCandidate]:
        """Search all configured sources and merge results."""
        tasks = []
        for source in self.sources:
            method = getattr(self, f"_search_{source}", None)
            if method:
                tasks.append(self._safe_search(method, query))

        results = await asyncio.gather(*tasks)
        candidates = []
        for result in results:
            if isinstance(result, list):
                candidates.extend(result)
        return candidates

    async def _safe_search(self, method, query: str) -> list[ImageCandidate]:
        """Wrap search in try/except to prevent one source from killing others."""
        try:
            return await method(query)
        except Exception as e:
            logger.debug("Image search source failed: %s", e)
            return []

    def _rank(self, query: str, candidates: list[ImageCandidate], top_k: int) -> list[dict]:
        """Rank candidates by cosine similarity to the query text."""
        profiles = [c.profile() for c in candidates]
        non_empty = [(i, p) for i, p in enumerate(profiles) if p.strip()]
        if not non_empty:
            # No profiles — return first candidate as-is
            c = candidates[0]
            return [{"url": c.url, "source_url": c.source_url, "score": 0.0, "provider": c.provider, "creator": c.creator, "license": c.license}]

        model = _get_model()
        indices, texts = zip(*non_empty)

        q_vec = model.encode([query], normalize_embeddings=True)
        c_vecs = model.encode(list(texts), normalize_embeddings=True)

        similarities = np.dot(c_vecs, q_vec.T).flatten()

        ranked_indices = np.argsort(-similarities)[:top_k]
        results = []
        for ri in ranked_indices:
            orig_idx = indices[ri]
            c = candidates[orig_idx]
            results.append({
                "url": c.url,
                "source_url": c.source_url,
                "score": float(similarities[ri]),
                "provider": c.provider,
                "creator": c.creator,
                "license": c.license,
            })
        return results

    # ── Openverse ──────────────────────────────────────────────

    async def _get_openverse_token(self, client: httpx.AsyncClient) -> str | None:
        """Get or refresh Openverse OAuth2 token (auto-registers if needed)."""
        if self._openverse_token:
            return self._openverse_token

        creds = self._load_openverse_creds()
        if not creds:
            creds = await self._register_openverse(client)
            if not creds:
                return None

        try:
            resp = await client.post(
                "https://api.openverse.org/v1/auth_tokens/token/",
                data={
                    "grant_type": "client_credentials",
                    "client_id": creds["client_id"],
                    "client_secret": creds["client_secret"],
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                self._openverse_token = resp.json().get("access_token")
                return self._openverse_token
        except Exception as e:
            logger.debug("Openverse token request failed: %s", e)
        return None

    async def _register_openverse(self, client: httpx.AsyncClient) -> dict | None:
        """Auto-register for Openverse API credentials."""
        try:
            resp = await client.post(
                "https://api.openverse.org/v1/auth_tokens/register/",
                json={
                    "name": "newsday-image-fetcher",
                    "description": "Semantic image search for college newsletter",
                    "email": "newsday@localhost",
                },
                timeout=self.timeout,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                creds = {
                    "client_id": data["client_id"],
                    "client_secret": data["client_secret"],
                }
                self._save_openverse_creds(creds)
                logger.info("Openverse credentials registered and saved")
                return creds
        except Exception as e:
            logger.debug("Openverse registration failed: %s", e)
        return None

    def _load_openverse_creds(self) -> dict | None:
        if CREDS_PATH.exists():
            try:
                return json.loads(CREDS_PATH.read_text())
            except Exception:
                pass
        return None

    def _save_openverse_creds(self, creds: dict):
        try:
            CREDS_PATH.write_text(json.dumps(creds, indent=2))
        except Exception as e:
            logger.warning("Could not save Openverse credentials: %s", e)

    async def _search_openverse(self, query: str) -> list[ImageCandidate]:
        async with httpx.AsyncClient() as client:
            token = await self._get_openverse_token(client)
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            resp = await client.get(
                "https://api.openverse.org/v1/images/",
                params={"q": query, "page_size": 10, "mature": "false"},
                headers=headers,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return []

            results = []
            for item in resp.json().get("results", []):
                url = item.get("url", "")
                if not url:
                    continue
                results.append(ImageCandidate(
                    url=url,
                    source_url=item.get("foreign_landing_url", ""),
                    title=item.get("title", ""),
                    tags=" ".join(t.get("name", "") for t in (item.get("tags") or [])),
                    description="",
                    creator=item.get("creator", ""),
                    provider="openverse",
                    license=item.get("license", ""),
                ))
            return results

    # ── Wikimedia Commons ──────────────────────────────────────

    async def _search_wikimedia(self, query: str) -> list[ImageCandidate]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrnamespace": 6,  # File namespace
                    "gsrlimit": 10,
                    "prop": "imageinfo",
                    "iiprop": "url|extmetadata|size",
                    "iiurlwidth": 800,
                    "format": "json",
                },
                headers={"User-Agent": "NewsDay/1.0 (https://github.com/newsday; newsday@localhost) python-httpx"},
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return []

            pages = resp.json().get("query", {}).get("pages", {})
            results = []
            for page in pages.values():
                imageinfo = (page.get("imageinfo") or [{}])[0]
                url = imageinfo.get("thumburl") or imageinfo.get("url", "")
                if not url:
                    continue

                ext = imageinfo.get("extmetadata", {})
                desc = ext.get("ImageDescription", {}).get("value", "")
                cats = ext.get("Categories", {}).get("value", "")
                author = ext.get("Artist", {}).get("value", "")
                lic = ext.get("LicenseShortName", {}).get("value", "")
                # Strip HTML tags from metadata
                import re
                desc = re.sub(r"<[^>]+>", " ", desc).strip()
                author = re.sub(r"<[^>]+>", " ", author).strip()

                results.append(ImageCandidate(
                    url=url,
                    source_url=f"https://commons.wikimedia.org/wiki/{page.get('title', '')}",
                    title=page.get("title", "").replace("File:", "").rsplit(".", 1)[0],
                    tags=cats,
                    description=desc[:200],
                    creator=author[:100],
                    provider="wikimedia",
                    license=lic,
                ))
            return results

    # ── Pixabay ────────────────────────────────────────────────

    async def _search_pixabay(self, query: str) -> list[ImageCandidate]:
        api_key = os.environ.get("PIXABAY_API_KEY", "")
        if not api_key:
            return []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://pixabay.com/api/",
                params={"key": api_key, "q": query, "per_page": 10, "safesearch": "true"},
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return []

            results = []
            for hit in resp.json().get("hits", []):
                results.append(ImageCandidate(
                    url=hit.get("webformatURL", ""),
                    source_url=hit.get("pageURL", ""),
                    title=hit.get("tags", ""),
                    tags=hit.get("tags", ""),
                    description="",
                    creator=hit.get("user", ""),
                    provider="pixabay",
                    license="Pixabay License",
                ))
            return results

    # ── Pexels ─────────────────────────────────────────────────

    async def _search_pexels(self, query: str) -> list[ImageCandidate]:
        api_key = os.environ.get("PEXELS_API_KEY", "")
        if not api_key:
            return []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "per_page": 10},
                headers={"Authorization": api_key},
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return []

            results = []
            for photo in resp.json().get("photos", []):
                results.append(ImageCandidate(
                    url=photo.get("src", {}).get("medium", ""),
                    source_url=photo.get("url", ""),
                    title=photo.get("alt", ""),
                    tags="",
                    description=photo.get("alt", ""),
                    creator=photo.get("photographer", ""),
                    provider="pexels",
                    license="Pexels License",
                ))
            return results
