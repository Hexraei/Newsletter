# College Newsletter Platform - Automated Scraping System

## Overview

This repository contains a production-ready content aggregation and scraping system designed for a college newsletter platform. The system automatically collects, processes, and organizes technology-focused content from multiple sources to deliver curated news to college students.

## Current State

### Implemented Components

1. **Scraping Platform** (`scraper_platform/`)
   - Modular scraper architecture with base classes
   - Support for 7 content sources
   - Excel-based tracking and data persistence
   - Automated newsletter generation

2. **Content Sources**
   - Hacker News (Firebase API)
   - Reddit (JSON API)
   - GitHub (Search API)
   - Medium (RSS Feeds)
   - Product Hunt (RSS Feeds)
   - YouTube (Transcript API)
   - Twitter/X (twscrape library with mock fallback)

3. **Documentation** (`reports/`)
   - Architecture specifications
   - Source categorization matrix
   - Scraping methodology documentation

### System Capabilities

- Automated content collection from 7 major platforms
- Deduplication via content hashing
- Engagement tracking (upvotes, comments, stars, etc.)
- Excel-based data persistence
- Newsletter generation in Markdown format
- Category classification (security, AI/ML, startups, etc.)

## Project Structure

```
newsletter/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── context/                          # Original PRD documents
│   ├── College_Newsletter_PRD_v1.docx
│   ├── docx_content.txt
│   ├── pdf_content.txt
│   ├── pdf_tables.json
│   └── Untitled 21.pdf
├── reports/                          # Architecture documentation
│   ├── AGENTS.md
│   ├── Master_Scraping_Logic.md
│   ├── scraping_logic.md
│   ├── Scraping_Logic_Architecture.pdf
│   ├── Source_Categories.md
│   ├── Twitter_Scraping_Options.md
│   └── Ultimate_Free_Scraping_Architecture.md
└── scraper_platform/                 # Production scraping code
    ├── main.py                       # Main orchestrator
    ├── requirements.txt              # Platform dependencies
    └── src/
        ├── base_scraper.py           # Base scraper class
        ├── excel_tracker.py          # Excel logging system
        └── scrapers/
            ├── hackernews_scraper.py
            ├── reddit_scraper.py
            ├── github_scraper.py
            ├── medium_scraper.py
            ├── producthunt_scraper.py
            ├── youtube_scraper.py
            └── twitter_scraper.py
```

## Installation

### Prerequisites
- Python 3.11 or higher
- pip package manager

### Setup
```bash
# Clone repository and navigate to scraper platform
cd scraper_platform

# Install dependencies
pip install -r requirements.txt
```

### Dependencies
Core dependencies include:
- httpx (async HTTP client)
- feedparser (RSS parsing)
- pandas (data manipulation)
- openpyxl (Excel handling)
- youtube-transcript-api (YouTube captions)
- twscrape (Twitter scraping - optional)

## Usage

### Run Full Scraping Cycle
```bash
cd scraper_platform
python main.py
```

This executes the complete scraping pipeline:
1. Fetches content from all 7 sources
2. Stores data in Excel format
3. Generates JSON export
4. Creates Markdown newsletter

### Output Files
All outputs are stored in `scraper_platform/data/`:
- `scraper_tests.xlsx` - Complete dataset with all scraped items
- `scraped_YYYYMMDD_HHMMSS.json` - JSON export
- `newsletter_YYYYMMDD.md` - Generated newsletter

### Individual Scraper Testing
Each scraper can be tested independently:
```bash
python -m src.scrapers.hackernews_scraper
python -m src.scrapers.youtube_scraper
```

## Technical Architecture

### Base Scraper Pattern
All scrapers inherit from `BaseScraper` which provides:
- HTTP client with retry logic
- Standardized item format (`ScrapedItem`)
- Logging infrastructure
- Content deduplication (SHA-256 hashing)

### Data Schema
Each scraped item contains:
- `source`: Platform name
- `source_type`: Category classification
- `title`: Content title
- `url`: Direct link
- `content`: Text snippet or transcript
- `author`: Content creator
- `published_at`: Original publication date
- `scraped_at`: Collection timestamp
- `engagement`: Platform-specific metrics
- `metadata`: Source-specific fields
- `content_hash`: Deduplication identifier

### Source-Specific Implementation Details

**Hacker News**
- Method: Official Firebase API
- Auth: None required
- Rate Limit: 1000 requests/minute
- Data: Top stories, Ask HN, Show HN

**Reddit**
- Method: JSON API (replaces blocked RSS)
- Auth: None for read-only
- Rate Limit: ~30 requests/minute
- Data: Hot posts from configured subreddits

**GitHub**
- Method: Search API
- Auth: Optional (increases rate limit from 60 to 5000/hour)
- Data: Trending repositories by language

**Medium**
- Method: Publication RSS feeds
- Auth: None
- Data: Articles from tech publications

**Product Hunt**
- Method: Category RSS feeds
- Auth: None
- Data: Featured products and launches

**YouTube**
- Method: youtube-transcript-api library
- Auth: None
- Data: Video transcripts and metadata
- Note: Fetches captions directly without audio download

**Twitter/X**
- Method: twscrape library
- Auth: Requires Twitter account credentials
- Fallback: Mock mode for testing without credentials
- Data: Tweets, replies, engagement metrics

## Changes Made

### Phase 1: Core Architecture (Initial)
- Established base scraper pattern
- Implemented Hacker News, Reddit, GitHub scrapers
- Created Excel tracking system
- Built main orchestrator

### Phase 2: Content Expansion
- Added Medium publication RSS scraper
- Added Product Hunt RSS scraper
- Implemented quality scoring for Medium articles
- Added category classification system

### Phase 3: Video and Social Integration
- Implemented YouTube transcript scraper using youtube-transcript-api
- Added Twitter scraper using twscrape library
- Created mock mode for Twitter testing without credentials
- Added transcript availability tracking

### Phase 4: Cleanup and Documentation
- Removed deprecated test files and utilities
- Moved documentation to reports folder
- Cleaned Python cache files
- Consolidated requirements

## Limitations and Considerations

### Rate Limits
- GitHub: 60 requests/hour without authentication
- Reddit: Subject to IP blocking if abused
- Twitter: Requires valid account credentials for real data

### Content Availability
- YouTube videos without captions return no transcript
- Some Medium RSS feeds may be malformed (handled gracefully)
- Twitter scraping requires active accounts and may break with platform changes

### Data Volume
Typical collection per run:
- Hacker News: 30 items
- Reddit: 50-60 items
- GitHub: 40 items
- Medium: 60-70 items
- Product Hunt: 70-80 items
- YouTube: Variable based on video list
- Twitter: Variable based on search/users

## Future Enhancements

1. **Database Integration**
   - Migrate from Excel to PostgreSQL
   - Implement proper queue system (Redis/BullMQ)

2. **Deployment**
   - Docker containerization
   - Oracle Cloud deployment configuration
   - Scheduled execution via cron or GitHub Actions

3. **Monitoring**
   - Health check endpoints
   - Failure alerting
   - Metrics dashboard

4. **Content Processing**
   - NLP-based summarization
   - Duplicate detection across sources
   - Breaking news detection algorithm

## License

Project documentation and specifications are proprietary. Scraping implementations respect robots.txt and platform terms of service.

## Contact

For questions regarding the architecture or implementation, refer to documentation in the `reports/` directory.
