# Twitter Scraping Options for College Newsletter Platform

**Version:** 1.3  
**Date:** January 31, 2026  
**Purpose:** Analysis of Twitter and YouTube scraping methods for newsletter platform


# Executive Summary

This document analyzes approaches for scraping 300 Twitter accounts and YouTube content for a college newsletter platform.

**Key Finding:** 
- Twitter: Free scraping at scale is no longer viable. Cheapest reliable option is $13-20 per month.
- YouTube: Completely free scraping is possible using yt-dlp and RSS feeds.

**Recommended Architecture:** Hybrid approach using bird CLI or twitterapi.io for Twitter, and yt-dlp for YouTube.


# Part 1: Twitter Scraping


## Current State of Twitter Scraping

Twitter has implemented aggressive anti-scraping measures:

**February 2023:** Free API killed

**January 2024:** Cookie validation tightened

**January 2025:** Guest token fingerprint binding

**January 2025:** Datacenter IPs permanently banned

Guest tokens expire every 2-4 hours. Datacenter IPs (AWS, Azure, GitHub Actions) are blocked. Rate limits are 300 requests per hour per IP.


## Most Efficient Twitter Method: Hybrid bird CLI Approach

**Why this is the most efficient:**
- Uses cookie-based auth (inherits browser trust)
- Free for small scale testing
- Can scale with multiple accounts
- No API costs for Tier 2 and 3 content

**Architecture:**

Tier 1 (20 critical accounts): twitterapi.io at $0.90 per month
- Real-time updates for top influencers
- Guaranteed reliability

Tier 2 (80 important accounts): bird CLI at $0
- Uses 2-3 Twitter accounts with cookie rotation
- 600-800 tweets per day per account
- Covers 80 accounts every 2-3 days

Tier 3 (200 general accounts): RSS aggregators at $0
- Techmeme, Hacker News, Reddit
- 70-80% coverage of tech news

**Total Twitter Cost:** $0.90-5 per month

**Daily Volume:** 3,000-4,000 tweets

**Coverage:** All 300 accounts in 1-2 days


## bird CLI Technical Details

**Authentication:** Cookie-based using auth_token and ct0 from browser

**Rate Limits:** 300 requests per hour per account

**Realistic Output:**
- 1 account: 600-800 tweets per day
- 2 accounts: 1,200-1,600 tweets per day
- 3 accounts: 1,800-2,400 tweets per day

**Automation:** Python wrapper with SQLite for tracking, cron for scheduling

**Account Lifespan:** 2-4 months with conservative delays


# Part 2: YouTube Scraping


## Proposed YouTube Flow

**Step 1: Keyword Search**
- Search YouTube using yt-dlp or RSS feeds
- Keywords: "AI news", "tech updates", "machine learning", "college placements"
- Grab top 10-15 or up to 50 videos

**Step 2: Metadata Extraction**
- Title, description, publish date
- Channel name, subscriber count
- View count, like count, comment count
- Video duration, thumbnail URL
- Video ID, URL

**Step 3: Subtitle Extraction**
- Download auto-generated or manual subtitles
- Extract text from SRT or VTT files
- Fallback: Speech-to-text if no subtitles

**Step 4: NLP Processing**
- Text cleaning (remove timestamps, speaker labels)
- Named Entity Recognition (companies, people, technologies)
- Keyword extraction
- Sentiment analysis
- Topic modeling

**Step 5: Vectorization and Scoring**
- Convert content to embeddings (OpenAI, Hugging Face)
- Generate relevance score for newsletter
- Cluster similar videos
- Rank by importance for students


## Is This the Most Efficient Approach?

**Analysis of current flow:**

**Strengths:**
- yt-dlp is free and reliable
- RSS feeds work without authentication
- Subtitles provide rich text content
- NLP can extract structured insights

**Weaknesses:**
- Downloading 50 videos is slow and bandwidth-heavy
- Subtitle extraction adds latency
- NLP processing is compute-intensive
- Vectorization requires API costs


## Improvements to the Approach

**Improvement 1: Skip Video Download, Use RSS First**

YouTube RSS feeds provide:
- Title and description (no download needed)
- Publish date and channel info
- Video ID for direct link

RSS is instant and requires zero bandwidth.

**Improved Flow:**

Step 1: RSS Search (instant)
- Query YouTube RSS for keywords
- Get 50 video metadata in 1-2 seconds
- Store in database

Step 2: Metadata Filtering (fast)
- Filter by view count (min 1,000 views)
- Filter by publish date (last 7 days)
- Filter by channel reputation
- Rank by relevance score

Step 3: Selective Subtitle Download (slow, but only for top 10)
- Download subtitles for top 10 videos only
- Not all 50 videos

Step 4: NLP Processing (compute only for top 10)
- Process 10 videos instead of 50
- Reduce API costs by 80%

Step 5: Vectorization (only for selected content)
- Generate embeddings for top 5-10 videos
- Create newsletter summary

**Result:** 80% reduction in processing time and cost


**Improvement 2: Use YouTube Data API v3 for Metadata**

YouTube Data API v3 free tier:
- 10,000 quota units per day
- Search: 100 units per call
- Video details: 1 unit per call

Daily allowance:
- 100 searches per day
- 1,000 video detail calls per day

**Cost:** $0 for metadata

**Limitation:** Does not provide subtitles

**Hybrid Approach:**
- Use API for metadata (fast, free)
- Use yt-dlp only for subtitles (slow, but selective)


**Improvement 3: Caching and Incremental Updates**

Instead of searching all keywords daily:

- Cache RSS feeds for 6 hours
- Track which videos already processed
- Only download new videos since last run
- Update scores incrementally

**Result:** 90% reduction in API calls after first run


**Improvement 4: Scoring Before NLP**

Create simple scoring before expensive NLP:

Pre-score using metadata:
- View count (0-30 points)
- Like ratio (0-20 points)
- Channel subscriber count (0-20 points)
- Keyword match in title (0-20 points)
- Recency (0-10 points)

Only process top 10-15 videos with NLP.

**Result:** Skip NLP for 70% of videos


## Most Efficient YouTube Method

**Recommended Architecture: Three-Tier Approach**

**Tier 1: RSS Feed Monitoring (Free, Continuous)**
- Subscribe to 30-50 tech channel RSS feeds
- yt-dlp can extract channel RSS: `yt-dlp --get-id --playlist-end 10 "channel URL"`
- Check every 2 hours
- Get new video notifications instantly

**Tier 2: Keyword Search via API (Free, Daily)**
- Use YouTube Data API v3
- Search 20 keywords daily
- Get 50 results per keyword
- Store metadata
- Filter and rank

**Tier 3: Subtitle NLP (Selective, Top 10 Only)**
- Download subtitles for top 10 videos daily
- Run NLP: NER, sentiment, keyword extraction
- Generate vector embeddings
- Create relevance score

**Daily Workflow:**

Morning (6 AM):
- Check RSS feeds (1 minute)
- Run keyword searches via API (5 minutes)
- Filter and rank top 15 videos (1 minute)

Afternoon (2 PM):
- Download subtitles for top 10 (10 minutes)
- Run NLP processing (5 minutes)
- Generate newsletter content (5 minutes)

**Total Processing Time:** 27 minutes per day

**Total Cost:** $0 (API free tier + yt-dlp)

**Daily Output:** 10-15 high-quality videos with NLP analysis


## Technical Stack for YouTube

**Tools:**
- yt-dlp: Video metadata and subtitles
- YouTube Data API v3: Search and metadata
- feedparser: RSS feed parsing
- spaCy or NLTK: NLP processing
- sentence-transformers: Vector embeddings (local, free)
- SQLite or PostgreSQL: Data storage

**No API Costs Option:**
- Skip OpenAI embeddings
- Use local Hugging Face models
- Use free NLTK or spaCy
- Total cost: $0

**With Minor API Costs ($5-10 per month):**
- Use OpenAI for embeddings (better quality)
- Use OpenAI for summarization
- Faster processing


## Comparison: Original vs Improved Approach

**Original Approach:**
- Download 50 videos: 50 minutes
- Extract subtitles: 25 minutes
- NLP all 50: 20 minutes
- Vectorize all 50: 15 minutes
- Total: 110 minutes per day
- Cost: $10-20 per month (API costs)

**Improved Approach:**
- RSS check: 1 minute
- API search: 5 minutes
- Filter metadata: 1 minute
- Download 10 subtitles: 5 minutes
- NLP top 10: 4 minutes
- Vectorize top 10: 3 minutes
- Total: 19 minutes per day
- Cost: $0 per month

**Improvement:** 83% faster, 100% cheaper


# Part 3: Integrated Newsletter Pipeline


## Combined Twitter + YouTube Flow

**Data Sources:**
- Twitter: 3,000 tweets per day (hybrid approach)
- YouTube: 10-15 videos per day (improved approach)
- RSS News: 50-100 articles per day

**Processing Pipeline:**

Step 1: Ingest (Morning 6 AM)
- Twitter: bird CLI and twitterapi.io
- YouTube: RSS and API search
- News: RSS aggregators

Step 2: Filter and Score (Morning 7 AM)
- Metadata scoring (quick)
- Remove duplicates
- Select top 50 items

Step 3: Deep Processing (Afternoon 2 PM)
- NLP on Twitter threads
- Subtitles for YouTube top 10
- Sentiment analysis
- Entity extraction

Step 4: Vectorization (Afternoon 3 PM)
- Generate embeddings
- Cluster similar content
- Rank by department relevance

Step 5: Newsletter Generation (Evening 6 PM)
- Summarize top 20 items
- Create 2-3 minute summaries
- Generate visualizations
- Queue for delivery


## Cost Summary

**Twitter:**
- twitterapi.io: $0.90-5 per month
- bird CLI: $0 (accounts cost only)

**YouTube:**
- yt-dlp: $0
- YouTube API: $0 (free tier)
- NLP (local): $0
- Embeddings (local): $0

**Infrastructure:**
- GitHub Actions: $0 (free tier)
- Supabase: $0 (free tier)
- Local machine: $0

**Total Monthly Cost:** $0.90-5


## Timeline and Next Steps

**Week 1: Setup**
- Set up Supabase database
- Configure bird CLI with 1-2 accounts
- Set up YouTube API key
- Test RSS feeds

**Week 2: Twitter Testing**
- Test bird CLI with 20 accounts
- Sign up for twitterapi.io
- Compare reliability
- Decide on hybrid ratio

**Week 3: YouTube Testing**
- Test RSS monitoring
- Test API search
- Test subtitle download
- Test NLP pipeline

**Week 4: Integration**
- Combine Twitter and YouTube flows
- Set up GitHub Actions scheduler
- Test end-to-end pipeline
- Generate first newsletter

**Week 5: Optimization**
- Tune scoring algorithms
- Optimize API usage
- Reduce processing time
- Scale to full 300 accounts


# Final Recommendations

**For Twitter:**
Use hybrid bird CLI approach. Test with 10-20 accounts first. If stable, scale to 80 accounts for Tier 2. Use twitterapi.io for 20 critical accounts (Tier 1).

**For YouTube:**
Use improved three-tier approach. RSS for continuous monitoring. API for keyword search. Selective subtitle NLP only for top 10 videos.

**For Overall Pipeline:**
Process Twitter and YouTube in parallel. Use metadata scoring first. Apply expensive NLP only to top content. Cache aggressively. Run on schedule twice daily.

**Expected Output:**
- 3,000 tweets processed daily
- 10-15 YouTube videos with full NLP analysis
- 50 news articles
- 20 final newsletter items
- Cost under $5 per month
- Processing time under 30 minutes per day


# Document End
