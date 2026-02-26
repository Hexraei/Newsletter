#!/usr/bin/env python
"""Scrape research papers from Semantic Scholar, Crossref, PubMed, and OpenAlex.

All APIs are free and require no API key.
Usage: python scrapers/run_research.py
"""

import asyncio
import hashlib
import json
import sys
import os
from datetime import datetime, timezone

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, _root)  # for scrapers.lib imports

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

import aiohttp
from sqlalchemy import select, text
from app.models.base import AsyncSessionLocal, engine
from app.models.content import Source, RawContent

# Department -> search queries (career-relevant, student-useful)
DEPT_QUERIES = {
    "CSE": ["software engineering", "algorithms distributed systems", "cybersecurity vulnerability"],
    "IT":  ["cloud computing infrastructure", "network security", "DevOps continuous deployment"],
    "AIDS": ["deep learning neural network", "large language model", "computer vision object detection"],
    "ECE": ["embedded systems IoT", "VLSI design", "signal processing 5G"],
    "EEE": ["renewable energy smart grid", "power electronics", "electric vehicle battery"],
    "ME":  ["robotics manufacturing", "additive manufacturing 3D printing", "computational fluid dynamics"],
    "CE":  ["structural engineering seismic", "sustainable construction materials", "geotechnical foundation"],
    "BT":  ["CRISPR gene editing", "bioinformatics genomics", "drug discovery molecular"],
    "CH":  ["green chemistry catalysis", "polymer materials", "electrochemistry energy storage"],
    "AE":  ["aerodynamics UAV", "satellite propulsion", "hypersonic aerospace"],
}

HEADERS = {"User-Agent": "NewsDay-College-Newsletter/1.0 (research-aggregator)"}
RESULTS_PER_QUERY = 5


async def fetch_semantic_scholar(session: aiohttp.ClientSession, query: str, limit: int = 5) -> list:
    """Fetch papers from Semantic Scholar Academic Graph API."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,authors,year,citationCount,url,externalIds,venue,publicationDate",
        "sort": "citationCount:desc",
    }
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 429:
                await asyncio.sleep(3)
                return []
            if resp.status != 200:
                return []
            data = await resp.json()
            papers = []
            for p in (data.get("data") or []):
                if not p.get("title") or not p.get("abstract"):
                    continue
                doi = (p.get("externalIds") or {}).get("DOI", "")
                papers.append({
                    "title": p["title"],
                    "abstract": p["abstract"][:500],
                    "authors": ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:5]),
                    "year": p.get("year"),
                    "citations": p.get("citationCount", 0),
                    "url": f"https://doi.org/{doi}" if doi else (p.get("url") or ""),
                    "doi": doi,
                    "venue": p.get("venue", ""),
                    "published_date": p.get("publicationDate"),
                    "source_api": "semantic_scholar",
                })
            return papers
    except Exception:
        return []


async def fetch_crossref(session: aiohttp.ClientSession, query: str, limit: int = 5) -> list:
    """Fetch papers from Crossref (DOI registry)."""
    import re
    url = "https://api.crossref.org/works"
    params = {
        "query": query, "rows": limit, "sort": "published", "order": "desc",
        "filter": "type:journal-article", "mailto": "newsletter@example.com",
    }
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            papers = []
            for item in (data.get("message", {}).get("items") or []):
                title_parts = item.get("title", [])
                title = title_parts[0] if title_parts else ""
                if not title:
                    continue
                abstract = re.sub(r"<[^>]+>", "", item.get("abstract", ""))[:500]
                doi = item.get("DOI", "")
                authors = ", ".join(
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in (item.get("author") or [])[:5]
                )
                date_parts = item.get("published", {}).get("date-parts", [[]])
                year = date_parts[0][0] if date_parts and date_parts[0] else None
                pub_date = None
                if date_parts and date_parts[0] and len(date_parts[0]) >= 3:
                    pub_date = f"{date_parts[0][0]}-{date_parts[0][1]:02d}-{date_parts[0][2]:02d}"
                papers.append({
                    "title": title, "abstract": abstract, "authors": authors,
                    "year": year, "citations": item.get("is-referenced-by-count", 0),
                    "url": f"https://doi.org/{doi}" if doi else "",
                    "doi": doi, "venue": (item.get("container-title") or [""])[0],
                    "published_date": pub_date, "source_api": "crossref",
                })
            return papers
    except Exception:
        return []


async def fetch_openalex(session: aiohttp.ClientSession, query: str, limit: int = 5) -> list:
    """Fetch papers from OpenAlex (250M+ works)."""
    url = "https://api.openalex.org/works"
    params = {
        "search": query, "per_page": limit, "sort": "cited_by_count:desc",
        "filter": "type:article,is_oa:true", "mailto": "newsletter@example.com",
    }
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            papers = []
            for w in (data.get("results") or []):
                title = w.get("title", "")
                if not title:
                    continue
                abstract = ""
                inv = w.get("abstract_inverted_index")
                if inv:
                    word_positions = []
                    for word, positions in inv.items():
                        for pos in positions:
                            word_positions.append((pos, word))
                    word_positions.sort()
                    abstract = " ".join(w for _, w in word_positions)[:500]
                doi_raw = w.get("doi", "")
                doi = doi_raw.replace("https://doi.org/", "") if doi_raw else ""
                authors = ", ".join(
                    a.get("author", {}).get("display_name", "")
                    for a in (w.get("authorships") or [])[:5]
                )
                papers.append({
                    "title": title, "abstract": abstract, "authors": authors,
                    "year": w.get("publication_year"),
                    "citations": w.get("cited_by_count", 0),
                    "url": doi_raw or (w.get("primary_location", {}) or {}).get("landing_page_url", ""),
                    "doi": doi,
                    "venue": ((w.get("primary_location", {}) or {}).get("source", {}) or {}).get("display_name", ""),
                    "published_date": w.get("publication_date"),
                    "source_api": "openalex",
                })
            return papers
    except Exception:
        return []


async def fetch_pubmed(session: aiohttp.ClientSession, query: str, limit: int = 5) -> list:
    """Fetch papers from PubMed (NCBI E-utilities). Best for BT/CH/biomedical."""
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    try:
        async with session.get(search_url, params={
            "db": "pubmed", "term": query, "retmax": limit,
            "sort": "relevance", "retmode": "json",
        }, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return []
            ids = (await resp.json()).get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

        async with session.get(fetch_url, params={
            "db": "pubmed", "id": ",".join(ids), "retmode": "json",
        }, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return []
            result = (await resp.json()).get("result", {})
            papers = []
            for pmid in ids:
                item = result.get(pmid, {})
                if not item or not item.get("title"):
                    continue
                authors = ", ".join(
                    a.get("name", "") for a in (item.get("authors") or [])[:5]
                )
                doi_list = [eid["value"] for eid in (item.get("articleids") or []) if eid.get("idtype") == "doi"]
                doi = doi_list[0] if doi_list else ""
                papers.append({
                    "title": item["title"],
                    "abstract": "",
                    "authors": authors,
                    "year": int(item.get("pubdate", "0")[:4]) if item.get("pubdate") else None,
                    "citations": 0,
                    "url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "doi": doi,
                    "venue": item.get("fulljournalname", item.get("source", "")),
                    "published_date": item.get("pubdate"),
                    "source_api": "pubmed",
                })
            return papers
    except Exception:
        return []


def dedup_papers(papers: list) -> list:
    """Deduplicate papers by DOI, then by normalized title."""
    seen_dois = set()
    seen_titles = set()
    unique = []
    for p in papers:
        doi = p.get("doi", "").lower().strip()
        if doi and doi in seen_dois:
            continue
        norm_title = p["title"].lower().strip()[:80]
        if norm_title in seen_titles:
            continue
        if doi:
            seen_dois.add(doi)
        seen_titles.add(norm_title)
        unique.append(p)
    return unique


async def scrape_department(session: aiohttp.ClientSession, dept_key: str, queries: list) -> list:
    """Scrape all APIs for one department's queries."""
    all_papers = []
    for query in queries:
        results = await asyncio.gather(
            fetch_semantic_scholar(session, query, RESULTS_PER_QUERY),
            fetch_crossref(session, query, RESULTS_PER_QUERY),
            fetch_openalex(session, query, RESULTS_PER_QUERY),
            *(([fetch_pubmed(session, query, RESULTS_PER_QUERY)]
               if dept_key in ("BT", "CH", "ME", "AE") else [])),
        )
        for batch in results:
            all_papers.extend(batch)
        await asyncio.sleep(1)

    return dedup_papers(all_papers)


async def store_papers(papers: list, dept_key: str) -> tuple[int, int]:
    """Store papers as raw_content in the DB."""
    stored = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Source).where(
                Source.platform == "research",
                Source.department_tags.contains([dept_key]),
            )
        )
        source = result.scalars().first()

        if not source:
            source = Source(
                name=f"{dept_key} Research Papers",
                source_type="academic",
                url="https://api.semanticscholar.org/graph/v1/paper/search",
                platform="research",
                is_active=True,
                department_tags=[dept_key],
                scrape_config={"feed_type": "research"},
            )
            db.add(source)
            await db.commit()
            await db.refresh(source)

        for paper in papers:
            content_hash = hashlib.sha256(
                (paper.get("doi") or paper["title"]).encode()
            ).hexdigest()

            existing = await db.execute(
                select(RawContent.id).where(RawContent.content_hash == content_hash)
            )
            if existing.first():
                skipped += 1
                continue

            pub_date = None
            if paper.get("published_date"):
                try:
                    date_str = str(paper["published_date"])
                    if len(date_str) == 10:
                        pub_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    elif len(date_str) >= 4:
                        pub_date = datetime(int(date_str[:4]), 1, 1, tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass

            raw = RawContent(
                source_id=source.id,
                original_url=paper.get("url", ""),
                original_title=paper["title"][:500],
                original_content=paper.get("abstract", "")[:2000],
                original_author=paper.get("authors", "")[:255],
                published_at=pub_date,
                content_hash=content_hash,
                status="pending",
                raw_metadata={
                    "department_tags": [dept_key],
                    "content_type": "research_paper",
                    "citations": paper.get("citations", 0),
                    "doi": paper.get("doi", ""),
                    "venue": paper.get("venue", ""),
                    "year": paper.get("year"),
                    "source_api": paper.get("source_api", ""),
                },
            )
            db.add(raw)
            stored += 1

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"    DB error: {e}")
            stored = 0

    return stored, skipped


async def main():
    print("=" * 60)
    print("RESEARCH PAPER SCRAPER")
    print("=" * 60)

    total_fetched = 0
    total_stored = 0

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for dept_key, queries in DEPT_QUERIES.items():
            print(f"\n[{dept_key}] Searching: {', '.join(queries)}")
            papers = await scrape_department(session, dept_key, queries)
            print(f"  Found {len(papers)} unique papers")
            total_fetched += len(papers)

            stored, skipped = await store_papers(papers, dept_key)
            print(f"  Stored: {stored}, Skipped (duplicate): {skipped}")
            total_stored += stored

    await engine.dispose()
    print(f"\nTotal: {total_fetched} fetched, {total_stored} stored")


if __name__ == "__main__":
    asyncio.run(main())
