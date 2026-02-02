# Master Scraping Logic

**Version:** 1.5  
**Date:** January 31, 2026  
**Purpose:** Comprehensive scraping architecture with Breaking News Detection Engine for real-time trending content across Twitter, YouTube, Reddit, GitHub, Hacker News, Medium, Product Hunt, and General Websites


# Overview

This document outlines the complete scraping architecture with a focus on **real-time trending detection** and **breaking news identification** across multiple platforms.

**Key Feature:** Breaking News Detection Engine (BNDE) - Identifies groundbreaking events within 15-30 minutes of occurrence

**Platforms covered:**
- Twitter (300 accounts) - Real-time breaking news
- YouTube (keyword-based) - Trending videos
- Reddit (20 subreddits) - Community hot topics
- GitHub (trending repos) - Viral projects and security alerts
- Hacker News - Tech news and startup launches
- Medium - Quality tutorials and career advice
- Product Hunt - New tools and product launches
- General Websites (department-specific) - Industry news

**Architecture Principles:**
- **Speed-first:** Check high-priority sources every 15-30 minutes
- **Trending detection:** Velocity-based scoring (not just volume)
- **Cross-platform validation:** Groundbreaking news appears on multiple platforms
- **Smart notifications:** Only alert on truly significant events
- **Zero or minimal cost**


# Part 1: Breaking News Detection Engine (BNDE)


## Core Concept

**Problem:** Students need to know about groundbreaking events ASAP (funding rounds, layoffs, new AI models, security vulnerabilities)

**Solution:** Multi-layered detection system that:
1. Monitors velocity (how fast something is spreading)
2. Cross-validates across platforms
3. Scores impact and relevance
4. Triggers notifications only for significant events


## Breaking News Indicators by Platform

### Twitter/X
**Indicators:**
- Tweet velocity: >100 engagements/hour from key accounts
- Trending hashtags: Appears in top 10 trending
- Verified accounts: Multiple verified accounts posting same topic
- Engagement spike: >500% normal engagement rate

**Examples of breaking news:**
- Major company layoffs announced
- New AI model released (GPT-5, Claude 4)
- Acquisition news ($1B+)
- Security vulnerability (CVE critical)

### YouTube
**Indicators:**
- View velocity: >10,000 views/hour in first 6 hours
- Like velocity: >1,000 likes/hour
- Comment sentiment shift: Negative/positive spike
- Creator tier: Major creator (1M+ subs) breaking news

**Examples:**
- Explainer video on breaking tech news
- Tutorial on new urgent vulnerability
- Reaction to major industry event

### Reddit
**Indicators:**
- Upvote velocity: >100 upvotes/hour
- Comment velocity: >50 comments/hour
- Awards: Multiple awards within short time
- Cross-posts: Posted to multiple subreddits

**Examples:**
- r/cscareerquestions: Mass layoff discussion
- r/MachineLearning: New paper with breakthrough results
- r/technology: Breaking regulatory news

### GitHub
**Indicators:**
- Star velocity: >500 stars/hour
- Fork velocity: >100 forks/hour
- Release downloads: Spike in release asset downloads
- Security advisory: Critical severity published

**Examples:**
- New viral AI tool (like AutoGPT)
- Critical vulnerability in popular package
- Major project acquisition/archival

### General Websites
**Indicators:**
- Multiple sites covering same story within 1 hour
- Major publication (TechCrunch, The Verge) breaking story
- Press release from Fortune 500 company
- Regulatory filing (SEC, etc.)


## Breaking News Scoring Algorithm

### Velocity Score (0-40 points)

Measures how fast content is spreading:

```
Velocity Score = (Current Engagement Rate / Baseline Rate) * Weight

Twitter: 
  - Normal: 10 engagements/hour
  - Breaking: >500 engagements/hour = 40 points

Reddit:
  - Normal: 5 upvotes/hour
  - Breaking: >200 upvotes/hour = 40 points

YouTube:
  - Normal: 100 views/hour
  - Breaking: >10,000 views/hour = 40 points

GitHub:
  - Normal: 10 stars/hour
  - Breaking: >500 stars/hour = 40 points
```

### Cross-Platform Validation (0-30 points)

Appearing on multiple platforms = higher significance:

```
Same topic appears on:
- 2 platforms: 10 points
- 3 platforms: 20 points
- 4+ platforms: 30 points
```

**Implementation:**
- Hash content keywords
- Compare within 6-hour window
- Cluster similar topics

### Source Authority (0-20 points)

Who is reporting it:

```
Tier 1 (20 points): CEO, official company account, major news (TechCrunch, Reuters)
Tier 2 (15 points): Verified influencers (100K+ followers), industry experts
Tier 3 (10 points): Active community members, smaller publications
Tier 4 (5 points): Regular users, unverified sources
```

### Content Category Multiplier

Some categories are inherently more breaking-worthy:

```
Critical Security (CVE): 2.0x multiplier
Major Layoffs (>1000): 1.8x multiplier
New AI Model Release: 1.5x multiplier
Funding ($100M+): 1.4x multiplier
Regulatory Changes: 1.3x multiplier
Product Launch: 1.2x multiplier
General News: 1.0x multiplier
```

### Final Breaking Score

```
Breaking Score = (Velocity + Cross-Platform + Authority) * Category Multiplier

Thresholds:
- 0-40: Normal content (daily digest)
- 41-70: Trending (highlight in newsletter)
- 71-90: Breaking (send notification within 1 hour)
- 91-100: CRITICAL (send immediate notification)
```


## Notification Triggers

### CRITICAL (Score 91-100) - Immediate
**Send within 15 minutes**

Examples:
- Major security vulnerability affecting student projects
- Mass layoffs at top tech companies
- New AI model that changes industry
- Regulatory change affecting tech workers

**Channels:**
- Email
- WhatsApp/SMS
- Push notification
- Discord webhook

### BREAKING (Score 71-90) - Within 1 hour
**Send within 1 hour**

Examples:
- Significant funding round ($100M+)
- Major product launches
- Important hiring freezes
- Viral GitHub project (>1000 stars/day)

**Channels:**
- Email
- Discord
- In-app notification

### TRENDING (Score 41-70) - Daily Digest
**Include in daily newsletter with highlight**

Examples:
- Interesting discussions gaining traction
- New tools gaining popularity
- Career advice threads
- Tutorial videos trending

**Channels:**
- Daily newsletter
- In-app feed


## Real-Time Monitoring Schedule

### Tier 1: Critical Sources (Every 15 minutes)

**Twitter:**
- 50 critical accounts (CEOs, major companies)
- Check for new tweets
- Calculate velocity immediately

**Reddit:**
- r/technology (hot)
- r/cscareerquestions (hot)
- r/MachineLearning (hot)

**GitHub:**
- Trending repositories (real-time API)
- Security advisories (critical/high)

**News Aggregators:**
- Techmeme (top stories)
- Hacker News (front page)

### Tier 2: Important Sources (Every 30 minutes)

**Twitter:**
- 150 important accounts
- Trending hashtags related to tech

**Reddit:**
- All 20 monitored subreddits (hot)

**YouTube:**
- Trending tab check
- 20 priority channels

### Tier 3: Regular Sources (Every 2 hours)

**All other sources**
- Remaining Twitter accounts
- RSS feeds
- General websites


## Breaking News Detection Pipeline

```
Step 1: Ingest (Every 15 min for Tier 1)
  ↓
Step 2: Calculate Velocity (Compare to baseline)
  ↓
Step 3: Cross-Platform Check (Same topic elsewhere?)
  ↓
Step 4: Score Calculation (Velocity + Authority + Category)
  ↓
Step 5: Threshold Check (Which tier?)
  ↓
Step 6: Notification Trigger (If CRITICAL or BREAKING)
  ↓
Step 7: Queue for Newsletter (All breaking news)
  ↓
Step 8: Store for Analysis (Improve detection over time)
```


## Technical Implementation

### Baseline Calculation (Adaptive)

Store 30-day rolling average for each source:

```python
# Baseline table in database
baselines = {
    'twitter_account': {
        'avg_engagements_per_hour': 15,
        'avg_tweets_per_day': 3,
        'updated_at': '2026-01-31'
    },
    'subreddit': {
        'avg_upvotes_per_hour': 25,
        'avg_posts_per_day': 50
    }
}
```

Recalculate weekly to adapt to changing patterns.

### Velocity Tracking

```python
class VelocityTracker:
    def __init__(self):
        self.recent_data = {}  # Last 6 hours
    
    def add_data_point(self, content_id, engagement_count, timestamp):
        self.recent_data[content_id] = {
            'count': engagement_count,
            'timestamp': timestamp
        }
    
    def calculate_velocity(self, content_id):
        # Get data points for last 1 hour
        hourly_data = self.get_last_hour(content_id)
        
        if len(hourly_data) < 2:
            return 0
        
        # Calculate rate of change
        first = hourly_data[0]
        last = hourly_data[-1]
        
        velocity = (last['count'] - first['count']) / 
                   (last['timestamp'] - first['timestamp']).hours
        
        return velocity
```

### Cross-Platform Topic Clustering

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN

def cluster_topics(content_list):
    # Extract keywords from all content
    vectorizer = TfidfVectorizer(max_features=100)
    X = vectorizer.fit_transform([c['text'] for c in content_list])
    
    # Cluster similar content
    clustering = DBSCAN(eps=0.3, min_samples=2).fit(X)
    
    # Group by cluster
    clusters = {}
    for idx, label in enumerate(clustering.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(content_list[idx])
    
    # Return clusters with content from multiple platforms
    cross_platform_clusters = []
    for cluster in clusters.values():
        platforms = set(c['platform'] for c in cluster)
        if len(platforms) >= 2:
            cross_platform_clusters.append(cluster)
    
    return cross_platform_clusters
```


## Notification System

### Immediate Notification (CRITICAL)

**Trigger:** Breaking Score >= 91

**Template:**
```
🚨 BREAKING: [Title]

Source: [Platform] - [Source Name]
Breaking Score: [Score]/100

Summary: [2-3 sentence summary]

Why it matters: [Impact explanation]

Action: [What students should do]

Links: [URL]

Time detected: [Timestamp]
```

**Example:**
```
🚨 BREAKING: OpenAI Announces GPT-5 with 10x Performance

Source: Twitter - @sama (Sam Altman)
Breaking Score: 95/100

Summary: OpenAI CEO Sam Altman announced GPT-5 with 10x improvement 
in reasoning capabilities, available today for ChatGPT Plus users.

Why it matters: This changes the AI landscape. Students using AI for 
projects need to understand new capabilities immediately.

Action: 
- Try GPT-5 for your current projects
- Update your AI tools knowledge
- Consider how this affects your job applications

Links: https://openai.com/blog/gpt-5

Time detected: 2026-01-31 14:23 IST (15 min ago)
```

### Hourly Digest (BREAKING)

**Trigger:** Breaking Score 71-90

Send hourly email with all breaking news:

```
Subject: Breaking Tech News - 3 Important Updates

1. [Title] - [Platform] - [Score]/100
   [2-line summary]
   [Link]

2. [Title] - [Platform] - [Score]/100
   [2-line summary]
   [Link]

3. [Title] - [Platform] - [Score]/100
   [2-line summary]
   [Link]
```


## Platform-Specific Breaking Detection


# Part 2: Twitter Scraping with Breaking Detection


## Data Requirements

**Target:** 300 Twitter accounts across college departments

**Breaking news priority:**
- Tier 1 (50 accounts): Every 15 minutes
- Tier 2 (100 accounts): Every 30 minutes
- Tier 3 (150 accounts): Every 2 hours


## Enhanced Three-Tier System

### Tier 1: Critical Breaking Accounts (Every 15 min)

**Accounts:**
- Major tech CEOs: @sama, @SatyaNadella, @tim_cook, @elonmusk
- Company official accounts: @OpenAI, @Google, @Meta, @Microsoft
- Breaking news: @TechCrunch, @TheVerge, @ BloombergTech
- Security: @cv_enrichment, @taviso

**Method:** twitterapi.io (fastest, most reliable)

**Detection:**
- New tweet check every 15 minutes
- Immediate velocity calculation
- Cross-check with other platforms
- Notify if Breaking Score > 70

### Tier 2: Important Tech Voices (Every 30 min)

**Accounts:**
- Influential developers and engineers
- VC accounts (a16z, Sequoia, YC)
- Popular tech commentators

**Method:** bird CLI

**Detection:**
- Check every 30 minutes
- Calculate engagement velocity
- Flag if velocity > 3x baseline

### Tier 3: General Tech Community (Every 2 hours)

**Accounts:**
- Remaining 150 accounts
- RSS aggregators as backup

**Detection:**
- Batch processing
- Trending topic identification
- Daily digest compilation


## Twitter Velocity Calculation

```python
def calculate_tweet_velocity(tweet, account_baseline):
    """
    Calculate how fast a tweet is gaining engagement
    """
    # Get engagement metrics
    likes = tweet['favorite_count']
    retweets = tweet['retweet_count']
    replies = tweet['reply_count']
    
    total_engagement = likes + (retweets * 2) + (replies * 3)
    
    # Calculate rate (engagements per hour since posted)
    hours_since_posted = (now - tweet['created_at']).hours
    if hours_since_posted < 0.25:  # Less than 15 min
        hours_since_posted = 0.25
    
    engagement_rate = total_engagement / hours_since_posted
    
    # Compare to baseline
    baseline_rate = account_baseline['avg_engagements_per_hour']
    velocity_ratio = engagement_rate / baseline_rate
    
    # Convert to score (0-40)
    velocity_score = min(40, velocity_ratio * 5)
    
    return {
        'score': velocity_score,
        'ratio': velocity_ratio,
        'rate': engagement_rate,
        'is_breaking': velocity_ratio > 10  # 10x normal = breaking
    }
```


## Twitter Breaking Score Calculation

```python
def calculate_breaking_score(tweet, source_tier):
    """
    Calculate breaking news score for a tweet
    """
    # 1. Velocity Score (0-40)
    velocity = calculate_tweet_velocity(tweet, baseline)
    velocity_score = velocity['score']
    
    # 2. Source Authority (0-20)
    authority_scores = {
        'ceo_founder': 20,
        'verified_major': 15,
        'verified_regular': 10,
        'unverified': 5
    }
    authority_score = authority_scores.get(source_tier, 5)
    
    # 3. Content Category Multiplier
    content = tweet['text'].lower()
    multiplier = 1.0
    
    if any(word in content for word in ['cve', 'vulnerability', 'exploit', 'security']):
        multiplier = 2.0  # Critical security
    elif any(word in content for word in ['layoff', 'firing', 'hiring freeze']):
        multiplier = 1.8  # Major layoffs
    elif any(word in content for word in ['gpt', 'llm', 'ai model', 'announce']):
        multiplier = 1.5  # AI news
    elif '$' in content and 'million' in content or 'billion' in content:
        multiplier = 1.4  # Funding news
    
    # 4. Cross-platform (checked separately, add later)
    cross_platform_score = 0  # Will be added if confirmed
    
    # Calculate preliminary score
    base_score = velocity_score + authority_score
    preliminary_score = base_score * multiplier
    
    return {
        'preliminary_score': preliminary_score,
        'velocity_score': velocity_score,
        'authority_score': authority_score,
        'multiplier': multiplier,
        'requires_cross_check': preliminary_score > 50
    }
```


## Twitter Automation Schedule with Breaking Detection

**Every 15 minutes (Critical Tier):**
- Fetch latest from 50 critical accounts
- Calculate breaking scores
- Cross-check with Reddit/HN
- Send CRITICAL notifications immediately
- Time: 2 minutes

**Every 30 minutes (Important Tier):**
- Fetch from 100 important accounts
- Calculate velocity
- Flag potential breaking news
- Time: 5 minutes

**Every 2 hours (General Tier):**
- Fetch remaining 150 accounts
- Batch processing
- Daily digest compilation
- Time: 15 minutes

**Daily total:** ~50 minutes for Twitter with breaking detection


# Part 3: YouTube Scraping with Trending Detection


## Enhanced Three-Tier Approach with Velocity

### Tier 1: Trending Tab + Priority Channels (Every 30 min)

**Method:** YouTube API + RSS

**Detection:**
- Check YouTube trending tab
- Monitor 20 priority channels
- Calculate view velocity in first 6 hours

**Breaking indicators:**
- >10,000 views/hour in first 6 hours
- Major creator (1M+ subs) breaking news
- Sudden comment spike

### Tier 2: Keyword Search with Velocity (Every 2 hours)

**Method:** YouTube API

**Enhanced with:**
- Track video performance over time
- Calculate view acceleration
- Identify "hockey stick" growth

### Tier 3: Deep Analysis (Daily)

**Method:** Selective subtitle NLP

**For breaking videos only:**
- Fast-track NLP for trending videos
- Summarize within 1 hour of detection


## YouTube Velocity Calculation

```python
def calculate_video_velocity(video_id, api_data):
    """
    Calculate how fast a video is gaining views
    """
    # Get current stats
    current_views = api_data['view_count']
    current_likes = api_data['like_count']
    publish_time = api_data['published_at']
    
    # Calculate hours since published
    hours_published = (now - publish_time).hours
    
    if hours_published == 0:
        hours_published = 1
    
    # Views per hour
    views_per_hour = current_views / hours_published
    
    # Engagement rate (likes per view)
    engagement_rate = current_likes / current_views if current_views > 0 else 0
    
    # Trending score (higher = more viral)
    # Normalize: 100,000 views in first 24h = good
    trending_score = (views_per_hour / 100000) * 40  # Max 40 points
    
    return {
        'views_per_hour': views_per_hour,
        'engagement_rate': engagement_rate,
        'trending_score': min(40, trending_score),
        'is_breaking': views_per_hour > 50000  # 50K/hour = breaking
    }
```


## YouTube Breaking Detection

**Breaking Score for YouTube:**
- Velocity Score (0-40): Views per hour
- Creator Authority (0-20): Subscriber count tier
- Engagement Quality (0-10): Like/comment ratio
- Cross-Platform (0-30): If also trending on Twitter/Reddit

**Example breaking video:**
- 3Blue1Brown releases video explaining breaking AI news
- 500K views in 6 hours
- Also trending on Hacker News
- Breaking Score: 85/100


# Part 4: Reddit Scraping with Hot Detection


## Real-Time Hot Post Detection

### Tier 1: Critical Subreddits (Every 15 minutes)

**Subreddits:**
- r/technology (hot)
- r/cscareerquestions (hot)
- r/MachineLearning (hot)

**Detection:**
- Check top 25 hot posts
- Calculate upvote velocity
- Monitor comment growth

### Tier 2: Important Subreddits (Every 30 minutes)

**All 20 subreddits (hot)**

**Detection:**
- Posts with >100 upvotes in first hour
- Multiple awards
- Cross-posted to other subreddits


## Reddit Velocity Calculation

```python
def calculate_reddit_velocity(post):
    """
    Calculate how fast a Reddit post is gaining traction
    """
    upvotes = post['score']
    comments = post['num_comments']
    awards = len(post.get('all_awardings', []))
    
    hours_since_post = (now - post['created_utc']).hours
    if hours_since_post < 0.5:
        hours_since_post = 0.5
    
    # Upvotes per hour
    upvote_velocity = upvotes / hours_since_post
    
    # Comments per hour (weighted higher)
    comment_velocity = comments / hours_since_post
    
    # Awards velocity
    award_velocity = awards / hours_since_post
    
    # Breaking indicators
    is_breaking = (
        upvote_velocity > 200 or  # 200 upvotes/hour
        comment_velocity > 100 or  # 100 comments/hour
        (upvotes > 1000 and hours_since_post < 2)  # 1K in 2 hours
    )
    
    # Score (0-40)
    velocity_score = min(40, (upvote_velocity / 500) * 40)
    
    return {
        'upvote_velocity': upvote_velocity,
        'comment_velocity': comment_velocity,
        'velocity_score': velocity_score,
        'is_breaking': is_breaking
    }
```


## Reddit Breaking Indicators

**Cross-post detection:**
- Same post in multiple subreddits = higher significance
- Use content similarity matching

**Award velocity:**
- Multiple awards in short time = community validation
- Gold/platinum awards = high significance

**Comment sentiment shift:**
- Sudden negative sentiment = crisis/bad news
- Sudden positive sentiment = exciting announcement


# Part 5: GitHub Scraping with Viral Detection


## Real-Time Trending Detection

### Tier 1: Trending Repositories (Every 30 minutes)

**API:** GitHub Search API

**Query:** Repositories created in last 7 days, sorted by stars

**Detection:**
- Star velocity: >100 stars/hour
- Fork velocity: >20 forks/hour
- Language trending

### Tier 2: Security Advisories (Every 15 minutes)

**Critical and High severity only**

**Immediate notification for:**
- CVE affecting popular student dependencies
- Critical vulnerabilities in widely used packages


## GitHub Star Velocity Calculation

```python
def calculate_repo_velocity(repo):
    """
    Calculate how fast a repository is gaining stars
    """
    current_stars = repo['stargazers_count']
    current_forks = repo['forks_count']
    created_at = repo['created_at']
    
    hours_since_creation = (now - created_at).hours
    if hours_since_creation < 1:
        hours_since_creation = 1
    
    # Stars per hour
    stars_per_hour = current_stars / hours_since_creation
    
    # Forks per hour (indicates usage, not just interest)
    forks_per_hour = current_forks / hours_since_creation
    
    # Viral indicators
    is_viral = stars_per_hour > 100  # 100 stars/hour = viral
    is_exploding = stars_per_hour > 500  # 500 stars/hour = exploding
    
    # Score (0-40)
    velocity_score = min(40, (stars_per_hour / 1000) * 40)
    
    return {
        'stars_per_hour': stars_per_hour,
        'forks_per_hour': forks_per_hour,
        'velocity_score': velocity_score,
        'is_viral': is_viral,
        'is_exploding': is_exploding
    }
```


## GitHub Security Breaking Detection

**Immediate notification for:**
```
Severity: CRITICAL
Affected package: [Popular package students use]
CVE ID: CVE-202X-XXXXX
Patched version: X.Y.Z
Action required: Update immediately

Summary: [Vulnerability description]
Impact: [How it affects student projects]
```

**Example:**
```
🚨 CRITICAL: Log4j-like vulnerability in popular Python library

CVE-2026-1234: Remote code execution in requests library < 2.31.0

Impact: 90% of student Python projects affected
Action: Update requirements.txt immediately
Patched: pip install requests>=2.31.0

More info: [GitHub Advisory Link]
```


# Part 6: Cross-Platform Breaking News Validation


## The 30-Minute Validation Window

When potential breaking news detected on one platform:

**Minute 0-5:** Detect on Source A (e.g., Twitter)
- Calculate preliminary score
- If > 50, trigger cross-check

**Minute 5-15:** Check Source B and C (e.g., Reddit, HN)
- Search for same keywords
- Check trending topics

**Minute 15-30:** Confirm or reject
- If found on 2+ platforms: Confirm breaking
- If only on 1 platform: Flag as "potential" (lower score)

**After 30 minutes:**
- Send notification if confirmed
- Include cross-platform evidence


## Cross-Platform Keyword Matching

```python
def extract_keywords(text):
    """Extract key entities from text"""
    # Use NER (spaCy) or simple keyword extraction
    doc = nlp(text)
    
    keywords = {
        'companies': [ent.text for ent in doc.ents if ent.label_ == 'ORG'],
        'products': [ent.text for ent in doc.ents if ent.label_ == 'PRODUCT'],
        'people': [ent.text for ent in doc.ents if ent.label_ == 'PERSON'],
        'technologies': extract_tech_keywords(text)  # Custom function
    }
    
    return keywords

def match_across_platforms(content_a, platform_b_content_list):
    """Check if same topic on another platform"""
    keywords_a = extract_keywords(content_a['text'])
    
    matches = []
    for content_b in platform_b_content_list:
        keywords_b = extract_keywords(content_b['text'])
        
        # Calculate overlap
        company_overlap = set(keywords_a['companies']) & set(keywords_b['companies'])
        product_overlap = set(keywords_a['products']) & set(keywords_b['products'])
        
        if len(company_overlap) > 0 or len(product_overlap) > 0:
            matches.append(content_b)
    
    return matches
```


## Breaking News Confidence Levels

**Single Platform (Tier 3):**
- Score: 0-50
- Action: Include in daily digest
- Confidence: Low

**Two Platforms (Tier 2):**
- Score: 51-70
- Action: Breaking notification within 1 hour
- Confidence: Medium

**Three+ Platforms (Tier 1):**
- Score: 71-100
- Action: Immediate notification
- Confidence: High


# Part 7: Complete Integration with Breaking Detection


## Updated Daily Master Schedule

### Every 15 Minutes (Critical Tier)

**Platforms:** Twitter Tier 1, Reddit Tier 1, GitHub Security

**Process:**
1. Fetch latest content (2 min)
2. Calculate velocity scores (1 min)
3. Cross-check platforms (5 min)
4. Calculate breaking scores (1 min)
5. Send CRITICAL notifications (1 min)

**Total per cycle:** 10 minutes
**Cycles per day:** 96 (24 hours × 4)
**Daily time:** 96 × 10 = 960 minutes = 16 hours

**Optimization:** Run 4 parallel workers
**Actual time:** 4 hours distributed across day

### Every 30 Minutes (Important Tier)

**Platforms:** Twitter Tier 2, YouTube Tier 1, Reddit Tier 2, GitHub Trending

**Process:**
1. Fetch content (5 min)
2. Calculate velocity (3 min)
3. Flag potential breaking (2 min)

**Daily time:** 48 × 10 = 480 minutes = 8 hours

**Optimization:** Parallel processing
**Actual time:** 2 hours

### Every 2 Hours (Regular Tier)

**Platforms:** All remaining sources

**Process:** Standard scraping

**Daily time:** 12 × 20 = 240 minutes = 4 hours

### Daily Deep Processing (Once per day)

**Process:**
- NLP for all collected content
- Newsletter generation
- Analytics and reporting

**Time:** 2 hours


## Total Resource Requirements

**With Breaking Detection:**
- Total processing time: ~8 hours/day (with parallelization)
- API calls: ~50,000/day (within free tiers)
- Storage: ~2GB/month
- Cost: $0.90-5/month

**Infrastructure:**
- GitHub Actions: Need longer runtime (paid or self-hosted runner)
- Alternative: Railway/Render VPS ($5/month) for continuous monitoring


## Notification Channels Setup

**CRITICAL (Immediate):**
- Email (SendGrid free: 100 emails/day)
- Discord webhook (instant)
- Telegram bot (instant)

**BREAKING (1 hour):**
- Email digest
- In-app notification
- Discord summary

**Daily:**
- Newsletter email
- In-app feed


## Example Breaking News Flow

**Scenario:** Major security vulnerability announced

**Minute 0:** @taviso tweets about CVE-2026-XXXX
- Velocity: 1000 likes in 10 minutes
- Preliminary score: 80
- Cross-check triggered

**Minute 5:** Check Reddit r/netsec
- Found: 3 posts about same CVE
- Cross-platform confirmed
- Score updated: 85

**Minute 10:** Check GitHub Advisories
- Found: Official advisory published
- Cross-platform: 3 platforms
- Final score: 92 (CRITICAL)

**Minute 12:** Notification sent
```
🚨 CRITICAL SECURITY ALERT

CVE-2026-XXXX: Remote code execution in [package]

Detected on: Twitter, Reddit, GitHub
Breaking Score: 92/100

Action: Update [package] to version X.Y.Z immediately

How to check if affected:
- Run: pip show [package]
- If version < X.Y.Z: VULNERABLE

Update command: pip install [package]>=X.Y.Z

More info: [Links]
```


# Part 8: General Website Scraping with News Detection


## The 3-Tier Free Pipeline with Velocity

### Tier 1: RSS with Priority Scoring (Every 30 min)

**Enhancement:** Track which RSS items are "blowing up"

**Detection:**
- Same story appearing in multiple RSS feeds within 1 hour
- Major publication (TechCrunch, etc.) breaking story
- Keywords trending

### Tier 2: Firecrawl with Urgency (On-demand)

**Trigger:** When RSS detects potential breaking news

**Use Firecrawl to:**
- Get full article quickly
- Extract key facts
- Summarize for notification

### Tier 3: Static Fallback (Daily batch)

**Regular monitoring:** Non-urgent sites


# Final Cost Summary with Breaking Detection

**Monthly costs:**
- Twitter (twitterapi.io): $0.90-5
- YouTube API: $0
- Reddit API: $0
- GitHub API: $0
- Firecrawl: $0 (500 pages free)
- Supabase: $0 (free tier)
- SendGrid (emails): $0 (100/day free)
- **Infrastructure:** $0-5 (if using VPS for continuous monitoring)

**Total: $0.90-10 per month**

**Without VPS:** Use GitHub Actions with scheduled triggers (free but less real-time)
**With VPS:** $5/month Railway/Render instance for true real-time monitoring


# Document End


---

# Part 9: Hacker News Scraping with Viral Detection


## Overview

**Why HN?** The front page of the tech internet. Best for:
- Breaking tech news before mainstream media
- Startup launches and funding announcements
- Technical deep-dives and tutorials
- Industry trend discussions

**HN Strengths:**
- Fast-moving (front page changes every 30-60 minutes)
- Technical audience = relevant for CS students
- Signal-to-noise ratio is high
- No API rate limits (generous to scrapers)


## Scraping Strategy

### Method 1: Official API (Primary)

**Firebase API** - Free, no auth required

```python
import httpx
import asyncio
from datetime import datetime, timedelta

class HNScraper:
    def __init__(self):
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.session = httpx.AsyncClient(timeout=30)
    
    async def get_top_stories(self, limit=30):
        """Get current front page stories"""
        response = await self.session.get(f"{self.base_url}/topstories.json")
        story_ids = response.json()[:limit]
        
        # Fetch story details in parallel
        stories = await asyncio.gather(*[
            self.get_story(sid) for sid in story_ids
        ])
        return [s for s in stories if s]
    
    async def get_new_stories(self, limit=50):
        """Get newest submissions"""
        response = await self.session.get(f"{self.base_url}/newstories.json")
        story_ids = response.json()[:limit]
        
        stories = await asyncio.gather(*[
            self.get_story(sid) for sid in story_ids
        ])
        return [s for s in stories if s]
    
    async def get_story(self, story_id):
        """Get full story details"""
        try:
            response = await self.session.get(
                f"{self.base_url}/item/{story_id}.json"
            )
            story = response.json()
            if story and story.get("type") == "story":
                return {
                    "id": story_id,
                    "title": story.get("title"),
                    "url": story.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                    "score": story.get("score", 0),
                    "comments": story.get("descendants", 0),
                    "author": story.get("by"),
                    "time": datetime.fromtimestamp(story.get("time", 0)),
                    "hn_url": f"https://news.ycombinator.com/item?id={story_id}"
                }
        except Exception as e:
            print(f"Error fetching story {story_id}: {e}")
        return None
    
    async def get_ask_hn(self):
        """Get Ask HN posts - great for career advice"""
        stories = await self.get_top_stories(limit=100)
        return [s for s in stories if s and s["title"].startswith("Ask HN:")]
    
    async def get_show_hn(self):
        """Get Show HN - new projects/tools"""
        stories = await self.get_top_stories(limit=100)
        return [s for s in stories if s and s["title"].startswith("Show HN:")]

# Usage
scraper = HNScraper()
top_stories = await scraper.get_top_stories(limit=30)
```


### Method 2: RSS Feeds (Backup)

```python
import feedparser

def get_hn_rss():
    """RSS as backup when API has issues"""
    feeds = {
        "front_page": "https://news.ycombinator.com/rss",
        "newest": "https://hnrss.org/newest",
        "jobs": "https://hnrss.org/jobs",  # Who is hiring
        "ask": "https://hnrss.org/ask",    # Ask HN
        "show": "https://hnrss.org/show",  # Show HN
    }
    
    stories = []
    for category, url in feeds.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:30]:
            stories.append({
                "title": entry.title,
                "url": entry.link,
                "category": category,
                "published": entry.published
            })
    return stories
```


## Breaking News Detection on HN

### Velocity Calculation

```python
class HNVelocityTracker:
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.velocity_window = 30  # minutes
    
    async def calculate_velocity(self, story_id):
        """Calculate points/hour for a story"""
        # Get current score
        current = await self.db.table("hn_stories").select("*").eq("id", story_id).single()
        
        # Get score from 30 min ago
        thirty_min_ago = datetime.now() - timedelta(minutes=30)
        previous = await self.db.table("hn_velocity_log").select("score").eq("story_id", story_id).gte("timestamp", thirty_min_ago).order("timestamp").limit(1).single()
        
        if not previous:
            return None
        
        score_diff = current["score"] - previous["score"]
        velocity_per_hour = score_diff * 2  # 30 min * 2 = 1 hour
        
        return {
            "story_id": story_id,
            "velocity_per_hour": velocity_per_hour,
            "comments_per_hour": self._estimate_comment_velocity(current),
            "breaking_score": self._calculate_breaking_score(velocity_per_hour, current)
        }
    
    def _estimate_comment_velocity(self, story):
        """Estimate comment velocity from engagement patterns"""
        age_hours = (datetime.now() - story["time"]).total_seconds() / 3600
        if age_hours < 1:
            return story.get("comments", 0) * 2  # Still hot
        return story.get("comments", 0) / age_hours
    
    def _calculate_breaking_score(self, velocity, story):
        """HN-specific breaking score"""
        score = 0
        
        # Velocity score (0-40)
        if velocity > 500: score += 40
        elif velocity > 300: score += 35
        elif velocity > 200: score += 30
        elif velocity > 100: score += 20
        elif velocity > 50: score += 10
        
        # Comment engagement (0-20)
        comment_ratio = story.get("comments", 0) / max(story.get("score", 1), 1)
        if comment_ratio > 0.5: score += 20  # Very controversial/discussed
        elif comment_ratio > 0.3: score += 15
        elif comment_ratio > 0.1: score += 10
        
        # Position bonus (0-15)
        if story.get("rank", 100) <= 3: score += 15
        elif story.get("rank", 100) <= 10: score += 10
        elif story.get("rank", 100) <= 30: score += 5
        
        # Content category multipliers
        multipliers = {
            "show_hn": 1.4,      # New tools/projects
            "layoffs": 1.8,      # Job market news
            "security": 2.0,     # CVEs, breaches
            "ai_ml": 1.5,        # AI breakthroughs
            "startup": 1.3,      # Funding, acquisitions
        }
        
        category = self._categorize_content(story["title"])
        return min(100, int(score * multipliers.get(category, 1.0)))
    
    def _categorize_content(self, title):
        """Categorize story by title keywords"""
        title_lower = title.lower()
        
        if any(k in title_lower for k in ["cve", "vulnerability", "security", "breach", "exploit"]):
            return "security"
        elif any(k in title_lower for k in ["layoff", "firing", "hiring freeze", "riff"]):
            return "layoffs"
        elif any(k in title_lower for k in ["gpt", "llm", "ai model", "machine learning", "openai", "anthropic"]):
            return "ai_ml"
        elif title_lower.startswith("show hn:"):
            return "show_hn"
        elif any(k in title_lower for k in ["raises", "funding", "acquired", "series a", "series b", "ipo"]):
            return "startup"
        return "general"
```


### Breaking News Indicators on HN

```python
HN_BREAKING_INDICATORS = {
    "velocity_thresholds": {
        "critical": 500,     # 500+ points/hour = front page instantly
        "high": 200,         # 200+ points/hour = rising fast
        "medium": 100        # 100+ points/hour = trending
    },
    "comment_thresholds": {
        "hot_discussion": 100,    # 100+ comments in first hour
        "controversial": 50       # High comment-to-vote ratio
    },
    "position_tracking": {
        "front_page_jump": "Reaches top 10 within 30 min of posting",
        "sticky_front": "Stays in top 3 for >2 hours"
    }
}

# HN-specific breaking news patterns
HN_BREAKING_PATTERNS = [
    ("major tech layoffs", ["google", "meta", "amazon", "microsoft", "layoff", "10%", "15%"]),
    ("security incidents", ["breach", "cve-202", "vulnerability", "exploit", "0-day"]),
    ("ai breakthroughs", ["gpt-5", "claude", "gemini", "new model", "sota", "benchmark"]),
    ("major outages", ["outage", "down", "aws", "cloudflare", "github down"]),
    ("startup unicorns", ["unicorn", "billion", "funding", "valuation", "ipo"]),
]
```


## Filtering for Student Relevance

```python
STUDENT_RELEVANT_FILTERS = {
    "include_patterns": [
        r"(?i)interview|career|salary|offer|negotiation",
        r"(?i)new grad|graduate|intern|internship",
        r"(?i)open source|github|tool|library",
        r"(?i)tutorial|learn|course|education",
        r"(?i)python|javascript|rust|go|typescript",
        r"(?i)machine learning|ai|llm|data science",
        r"(?i)startup|indie hacker|side project",
        r"(?i)who is hiring",
    ],
    "exclude_patterns": [
        r"(?i)crypto|bitcoin|ethereum|nft|web3",  # Unless major news
        r"(?i)political|election|trump|biden",     # Keep tech-focused
    ],
    "minimum_score": 50,      # At least 50 points
    "minimum_comments": 10,   # Some discussion
}

def is_student_relevant(story):
    """Filter HN stories for student newsletter"""
    title = story.get("title", "")
    score = story.get("score", 0)
    comments = story.get("comments", 0)
    
    # Skip low engagement
    if score < STUDENT_RELEVANT_FILTERS["minimum_score"]:
        return False
    if comments < STUDENT_RELEVANT_FILTERS["minimum_comments"]:
        return False
    
    # Check include patterns
    for pattern in STUDENT_RELEVANT_FILTERS["include_patterns"]:
        if re.search(pattern, title):
            # But not excluded
            for ex_pattern in STUDENT_RELEVANT_FILTERS["exclude_patterns"]:
                if re.search(ex_pattern, title):
                    return False
            return True
    
    return False
```


## HN Execution Schedule

```yaml
# GitHub Actions workflow
name: HN Breaking News

on:
  schedule:
    - cron: "*/15 * * * *"  # Every 15 minutes for velocity tracking
  workflow_dispatch:

jobs:
  scrape-hn:
    runs-on: ubuntu-latest
    steps:
      - name: Track front page
        run: |
          # Get current front page
          # Calculate velocity from previous snapshot
          # Alert if breaking score > 70
          
      - name: Deep scan every hour
        if: github.event.schedule == '0 * * * *'
        run: |
          # Scan Ask HN for career advice
          # Scan Show HN for new tools
          # Scan jobs for hiring trends
```


## HN + BNDE Integration

```python
async def check_hn_breaking_news():
    """Check HN for breaking news and trigger alerts"""
    scraper = HNScraper()
    tracker = HNVelocityTracker(supabase)
    
    # Get current front page
    stories = await scraper.get_top_stories(limit=50)
    
    breaking_items = []
    for story in stories:
        if not is_student_relevant(story):
            continue
        
        # Calculate velocity
        velocity_data = await tracker.calculate_velocity(story["id"])
        if not velocity_data:
            continue
        
        breaking_score = velocity_data["breaking_score"]
        
        # Store for cross-platform validation
        await store_for_validation({
            "platform": "hackernews",
            "id": story["id"],
            "title": story["title"],
            "url": story["url"],
            "breaking_score": breaking_score,
            "velocity": velocity_data,
            "timestamp": datetime.now()
        })
        
        if breaking_score >= 91:
            breaking_items.append({
                "urgency": "CRITICAL",
                "source": "Hacker News",
                "story": story,
                "score": breaking_score
            })
        elif breaking_score >= 71:
            breaking_items.append({
                "urgency": "BREAKING", 
                "source": "Hacker News",
                "story": story,
                "score": breaking_score
            })
    
    return breaking_items
```


## Expected Volume

| Frequency | Stories/Day | Breaking (71+) | Critical (91+) |
|-----------|-------------|----------------|----------------|
| Every 15 min | ~100 unique | 2-4 | 0-1 |

**Key HN Sections:**
- **Top Stories**: 30 items, refreshed continuously
- **New**: 50-100 items/day worth watching
- **Ask HN**: 5-10 career-relevant posts/week
- **Show HN**: 3-5 interesting tools/week
- **Jobs**: "Who is Hiring" monthly thread = goldmine


## Cost

**Free** - No API limits, no authentication required.

Firebase API is generously rate-limited (roughly 1000 requests/minute per IP).


---

# Part 10: Medium Scraping with Quality Detection


## Overview

**Why Medium?** Quality long-form content ideal for:
- Technical tutorials and deep-dives
- Career advice and soft skills
- Startup stories and founder journeys
- Industry analysis and trend reports

**Medium Strengths:**
- High-quality content (paywall filters out noise)
- Great for 5-10 minute reads (perfect for newsletter)
- Publications = curated content (better signal)
- Reading time estimates built-in

**Challenges:**
- Paywall after 3 free articles
- No official RSS for user feeds
- Dynamic loading (JavaScript required)


## Scraping Strategy

### Method 1: RSS Feeds (Free - Primary)

**Publications have RSS feeds:**

```python
import feedparser
from datetime import datetime

class MediumRSS:
    """Scrape Medium via publication RSS feeds"""
    
    # Student-relevant Medium publications
    PUBLICATIONS = {
        "better-programming": "https://betterprogramming.pub/feed",
        "towards-data-science": "https://towardsdatascience.com/feed",
        "javascript-scene": "https://javascript.plainenglish.io/feed",
        "python-in-plain-english": "https://python.plainenglish.io/feed",
        "geek-culture": "https://medium.com/geekculture/feed",
        "free-code-camp": "https://medium.freecodecamp.org/feed",
        "hackernoon": "https://hackernoon.com/feed",
        "the-startup": "https://medium.com/swlh/feed",  # Startup lessons
        "level-up-coding": "https://levelup.gitconnected.com/feed",
        "bits-and-pretzels": "https://bitsandpretzels.com/feed",  # Startup stories
    }
    
    # Tags for student interests
    TAGS = [
        "python", "javascript", "programming", "career",
        "machine-learning", "data-science", "startup",
        "interview", "leetcode", "software-engineering"
    ]
    
    def __init__(self):
        self.articles = []
    
    def fetch_publication(self, pub_name, url, limit=10):
        """Fetch articles from a publication"""
        try:
            feed = feedparser.parse(url)
            articles = []
            
            for entry in feed.entries[:limit]:
                article = {
                    "title": entry.title,
                    "url": entry.link.split("?")[0],  # Remove tracking params
                    "author": entry.get("author", "Unknown"),
                    "published": entry.published,
                    "summary": entry.get("summary", "")[:500],
                    "publication": pub_name,
                    "source_type": "publication"
                }
                articles.append(article)
            
            return articles
        except Exception as e:
            print(f"Error fetching {pub_name}: {e}")
            return []
    
    def fetch_tag(self, tag, limit=10):
        """Fetch articles by tag via Medium's tag RSS"""
        # Medium has unofficial tag feeds
        url = f"https://medium.com/feed/tag/{tag}"
        return self.fetch_publication(f"tag:{tag}", url, limit)
    
    def fetch_all(self, articles_per_source=5):
        """Fetch from all publications"""
        all_articles = []
        
        for pub_name, url in self.PUBLICATIONS.items():
            articles = self.fetch_publication(pub_name, url, articles_per_source)
            all_articles.extend(articles)
        
        # Fetch from key tags
        for tag in ["career", "interview", "python", "startup"][:3]:
            articles = self.fetch_tag(tag, 5)
            all_articles.extend(articles)
        
        return all_articles
```


### Method 2: Firecrawl for Full Content (Tier 2)

```python
from firecrawl import FirecrawlApp

class MediumContentExtractor:
    def __init__(self, api_key):
        self.firecrawl = FirecrawlApp(api_key=api_key)
    
    async def extract_article(self, url):
        """Extract full article content via Firecrawl"""
        try:
            # Firecrawl can handle Medium's dynamic loading
            result = self.firecrawl.scrape_url(
                url,
                params={
                    "formats": ["markdown", "html"],
                    "only_main_content": True  # Skip nav/header/footer
                }
            )
            
            content = result.get("markdown", "")
            
            # Extract reading time from Medium meta
            reading_time = self._estimate_reading_time(content)
            
            return {
                "full_content": content,
                "reading_time_minutes": reading_time,
                "word_count": len(content.split()),
                "is_paywalled": "member-only" in result.get("html", "").lower(),
                "claps": self._extract_claps(result.get("html", "")),
                "tags": self._extract_tags(result.get("html", ""))
            }
        except Exception as e:
            print(f"Error extracting {url}: {e}")
            return None
    
    def _estimate_reading_time(self, content):
        """Estimate reading time (avg 200 wpm)"""
        words = len(content.split())
        return max(1, round(words / 200))
    
    def _extract_claps(self, html):
        """Extract clap count if available"""
        # Medium shows clap count in meta or JS
        import re
        match = re.search(r'"clapCount":(\d+)', html)
        return int(match.group(1)) if match else None
    
    def _extract_tags(self, html):
        """Extract article tags"""
        import re
        tags = re.findall(r'"name":"([^"]+)","slug":"[^"]*","type":"Tag"', html)
        return list(set(tags))[:5]  # Top 5 unique tags
```


### Method 3: Medium API (Unofficial/Community)

```python
# Alternative: medium-api (community package)
# pip install medium-api

from medium_api import Medium

class MediumAPI:
    """Using community Medium API (rapidapi required)"""
    
    def __init__(self, rapidapi_key):
        # Note: This requires RapidAPI subscription
        # Free tier: 100 requests/day
        self.medium = Medium(rapidapi_key)
    
    def get_top_articles(self, tag="programming", count=10):
        """Get top articles by tag"""
        articles = self.medium.get_articles(tag=tag, count=count)
        return [{
            "title": a.title,
            "url": a.url,
            "author": a.author,
            "claps": a.claps,
            "reading_time": a.reading_time,
            "published": a.published_at
        } for a in articles]
```


## Quality Scoring (Not Velocity)

Medium is different - it's about **quality**, not speed. No "breaking news" here.

```python
class MediumQualityScorer:
    """Score Medium articles by quality, not velocity"""
    
    def calculate_quality_score(self, article, extracted_content):
        """
        Quality Score (0-100) based on:
        - Publication reputation
        - Engagement (claps)
        - Content depth
        - Reading time appropriateness
        - Recency
        """
        score = 0
        
        # Publication reputation (0-25)
        pub_scores = {
            "towards-data-science": 25,
            "better-programming": 22,
            "free-code-camp": 25,
            "hackernoon": 20,
            "level-up-coding": 18,
            "javascript-scene": 18,
            "geek-culture": 15,
            "the-startup": 20,
        }
        score += pub_scores.get(article["publication"], 10)
        
        # Engagement score (0-25)
        claps = extracted_content.get("claps", 0)
        if claps > 10000: score += 25
        elif claps > 5000: score += 20
        elif claps > 1000: score += 15
        elif claps > 500: score += 10
        elif claps > 100: score += 5
        
        # Content depth (0-25)
        word_count = extracted_content.get("word_count", 0)
        if word_count > 2000: score += 25      # Deep dive
        elif word_count > 1500: score += 20    # Comprehensive
        elif word_count > 1000: score += 15    # Good length
        elif word_count > 500: score += 10     # Quick read
        
        # Reading time sweet spot (0-15)
        # 3-8 minutes is ideal for newsletter
        reading_time = extracted_content.get("reading_time_minutes", 0)
        if 3 <= reading_time <= 8: score += 15
        elif 2 <= reading_time <= 10: score += 10
        elif reading_time <= 15: score += 5
        
        # Recency bonus (0-10)
        # Medium articles have longer shelf life than Twitter
        age_days = (datetime.now() - article["published"]).days
        if age_days <= 1: score += 10
        elif age_days <= 3: score += 7
        elif age_days <= 7: score += 5
        elif age_days <= 14: score += 3
        
        return min(100, score)
    
    def is_newsletter_worthy(self, quality_score, article):
        """Determine if article fits newsletter criteria"""
        return quality_score >= 60  # Only high-quality articles
```


## Content Categories for Medium

```python
MEDIUM_CATEGORIES = {
    "technical_tutorials": {
        "patterns": ["how to", "tutorial", "guide", "building", "implementing"],
        "weight": 1.3,
        "description": "Step-by-step technical guides"
    },
    "career_advice": {
        "patterns": ["career", "interview", "salary", "negotiation", "promotion"],
        "weight": 1.4,
        "description": "Professional development"
    },
    "industry_analysis": {
        "patterns": ["trends", "future of", "state of", "analysis", "landscape"],
        "weight": 1.2,
        "description": "Market and tech analysis"
    },
    "startup_stories": {
        "patterns": ["startup", "founder", "bootstrapping", "mvp", "launch"],
        "weight": 1.3,
        "description": "Entrepreneurship content"
    },
    "soft_skills": {
        "patterns": ["communication", "leadership", "productivity", "habits"],
        "weight": 1.1,
        "description": "Non-technical skills"
    }
}

def categorize_medium_article(title, tags):
    """Categorize article by title and tags"""
    text = (title + " " + " ".join(tags)).lower()
    
    scores = {}
    for category, config in MEDIUM_CATEGORIES.items():
        score = sum(1 for pattern in config["patterns"] if pattern in text)
        scores[category] = score * config["weight"]
    
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "general"
```


## Medium + Newsletter Integration

```python
async def curate_medium_content():
    """Curate top Medium articles for newsletter"""
    rss = MediumRSS()
    extractor = MediumContentExtractor(FIRECRAWL_API_KEY)
    scorer = MediumQualityScorer()
    
    # Fetch articles
    articles = rss.fetch_all(articles_per_source=5)
    
    curated = []
    for article in articles:
        # Extract full content (use Firecrawl quota wisely)
        content = await extractor.extract_article(article["url"])
        if not content:
            continue
        
        # Skip paywalled content for better UX
        if content.get("is_paywalled"):
            continue
        
        # Calculate quality score
        quality_score = scorer.calculate_quality_score(article, content)
        
        if scorer.is_newsletter_worthy(quality_score, article):
            category = categorize_medium_article(article["title"], content.get("tags", []))
            
            curated.append({
                "title": article["title"],
                "url": article["url"],
                "author": article["author"],
                "publication": article["publication"],
                "reading_time": content["reading_time_minutes"],
                "quality_score": quality_score,
                "category": category,
                "summary": generate_summary(content["full_content"]),
                "source": "Medium"
            })
    
    # Sort by quality score
    curated.sort(key=lambda x: x["quality_score"], reverse=True)
    
    # Return top 5 for newsletter
    return curated[:5]

def generate_summary(content, max_chars=300):
    """Generate 2-3 sentence summary"""
    # Simple extraction-based summary
    # In production, use LLM or better summarization
    sentences = content.split(".")[:3]
    summary = ". ".join(s.strip() for s in sentences if len(s.strip()) > 20)
    return summary[:max_chars] + "..." if len(summary) > max_chars else summary
```


## Medium Execution Schedule

```yaml
# GitHub Actions
name: Medium Content Curation

on:
  schedule:
    - cron: "0 */6 * * *"  # Every 6 hours
  workflow_dispatch:

jobs:
  curate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Fetch and score articles
        run: python medium_curator.py
        env:
          FIRECRAWL_API_KEY: ${{ secrets.FIRECRAWL_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
```


## Expected Volume

| Source | Articles/Day | Newsletter Worthy (60+) |
|--------|--------------|------------------------|
| RSS feeds | ~50 | 5-10 |
| Full extraction | ~20 | 3-5 |

**Medium Sweet Spot:**
- 2-3 high-quality articles per newsletter
- Focus on career advice + technical tutorials
- Avoid: paywalled content, very short (<2 min) reads


## Cost

| Component | Cost |
|-----------|------|
| RSS fetching | Free |
| Firecrawl extraction | 500 pages/month free |
| Supabase storage | Free tier |
| **Total** | **$0** |


---

# Part 11: Product Hunt Scraping with Launch Detection


## Overview

**Why Product Hunt?** Launch platform for:
- New developer tools and SaaS
- AI-powered products
- Productivity apps
- Open source projects
- Startup launches

**Product Hunt Strengths:**
- First to know about new tools
- Community votes = quality signal
- Founder often active in comments
- Perfect for "tool of the week" section

**Challenges:**
- No official API for free
- Requires authentication for full data
- Heavy JavaScript (SPA)


## Scraping Strategy

### Method 1: RSS Feeds (Free - Primary)

**Official RSS feeds exist:**

```python
import feedparser
from datetime import datetime

class ProductHuntRSS:
    """Scrape Product Hunt via RSS"""
    
    RSS_FEEDS = {
        "featured": "https://www.producthunt.com/feed",
        "newest": "https://www.producthunt.com/feed?category=undefined",
        "tech": "https://www.producthunt.com/feed?category=tech",
        "developer_tools": "https://www.producthunt.com/feed?category=developer-tools",
        "ai": "https://www.producthunt.com/feed?category=artificial-intelligence",
        "productivity": "https://www.producthunt.com/feed?category=productivity",
    }
    
    def __init__(self):
        self.products = []
    
    def fetch_feed(self, feed_name, url, limit=20):
        """Fetch products from RSS feed"""
        try:
            feed = feedparser.parse(url)
            products = []
            
            for entry in feed.entries[:limit]:
                product = {
                    "name": entry.title,
                    "tagline": entry.get("description", ""),
                    "url": entry.link,
                    "published": entry.published,
                    "category": feed_name,
                    "source": "producthunt"
                }
                products.append(product)
            
            return products
        except Exception as e:
            print(f"Error fetching {feed_name}: {e}")
            return []
    
    def fetch_all(self, limit_per_feed=10):
        """Fetch from all feeds"""
        all_products = []
        for feed_name, url in self.RSS_FEEDS.items():
            products = self.fetch_feed(feed_name, url, limit_per_feed)
            all_products.extend(products)
        return all_products
```


### Method 2: GraphQL API (Free Tier)

```python
import httpx

class ProductHuntGraphQL:
    """
    Product Hunt GraphQL API
    Free tier: 240 requests/hour
    """
    
    API_URL = "https://api.producthunt.com/v2/api/graphql"
    
    def __init__(self, api_token):
        self.token = api_token
        self.session = httpx.AsyncClient()
    
    async def get_today_featured(self, first=20):
        """Get today's featured products"""
        query = """
        query {
          posts(featured: true, first: %d) {
            edges {
              node {
                id
                name
                tagline
                description
                url
                votesCount
                commentsCount
                thumbnail {
                  url
                }
                topics {
                  edges {
                    node {
                      name
                    }
                  }
                }
                makers {
                  name
                  username
                }
                website
              }
            }
          }
        }
        """ % first
        
        response = await self.session.post(
            self.API_URL,
            json={"query": query},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        data = response.json()
        posts = data["data"]["posts"]["edges"]
        
        return [{
            "id": p["node"]["id"],
            "name": p["node"]["name"],
            "tagline": p["node"]["tagline"],
            "description": p["node"].get("description", ""),
            "url": p["node"]["url"],
            "votes": p["node"]["votesCount"],
            "comments": p["node"]["commentsCount"],
            "thumbnail": p["node"]["thumbnail"]["url"] if p["node"]["thumbnail"] else None,
            "topics": [t["node"]["name"] for t in p["node"]["topics"]["edges"]],
            "makers": [m["name"] for m in p["node"]["makers"]],
            "website": p["node"].get("website")
        } for p in posts]
    
    async def search_by_topic(self, topic_slug, first=20):
        """Search products by topic"""
        query = """
        query {
          posts(topic: "%s", first: %d) {
            edges {
              node {
                id
                name
                tagline
                votesCount
                commentsCount
                url
              }
            }
          }
        }
        """ % (topic_slug, first)
        
        response = await self.session.post(
            self.API_URL,
            json={"query": query},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        data = response.json()
        posts = data["data"]["posts"]["edges"]
        
        return [{
            "id": p["node"]["id"],
            "name": p["node"]["name"],
            "tagline": p["node"]["tagline"],
            "votes": p["node"]["votesCount"],
            "comments": p["node"]["commentsCount"],
            "url": p["node"]["url"]
        } for p in posts]

# Student-relevant topics
STUDENT_TOPICS = [
    "developer-tools",
    "productivity",
    "artificial-intelligence",
    "open-source",
    "education",
    "career",
    "programming",
    "note-taking"
]
```


### Method 3: Firecrawl for Deep Extraction

```python
class ProductHuntExtractor:
    """Extract full product details via Firecrawl"""
    
    def __init__(self, api_key):
        self.firecrawl = FirecrawlApp(api_key=api_key)
    
    async def extract_product_page(self, url):
        """Extract detailed product info"""
        try:
            result = self.firecrawl.scrape_url(
                url,
                params={"formats": ["markdown", "html"]}
            )
            
            html = result.get("html", "")
            
            # Extract structured data
            return {
                "full_description": result.get("markdown", ""),
                "hunter": self._extract_hunter(html),
                "makers": self._extract_makers(html),
                "gallery_urls": self._extract_gallery(html),
                "pricing": self._extract_pricing(html),
                "launched_at": self._extract_launch_time(html)
            }
        except Exception as e:
            print(f"Error extracting {url}: {e}")
            return None
    
    def _extract_hunter(self, html):
        """Extract who hunted the product"""
        import re
        match = re.search(r'hunter["\']?\s*:\s*["\']([^"\']+)', html)
        return match.group(1) if match else None
    
    def _extract_makers(self, html):
        """Extract product makers"""
        import re
        makers = re.findall(r'maker["\']?\s*:\s*["\']([^"\']+)', html)
        return list(set(makers))
    
    def _extract_gallery(self, html):
        """Extract product gallery images"""
        import re
        urls = re.findall(r'https://ph-files\.imgix\.net/[^"\'\s]+', html)
        return list(set(urls))[:5]  # Top 5 images
    
    def _extract_pricing(self, html):
        """Extract pricing info"""
        import re
        if re.search(r'free|open.source|github', html.lower()):
            return "free"
        elif re.search(r'\$\d+', html):
            return "paid"
        return "unknown"
    
    def _extract_launch_time(self, html):
        """Extract when product was launched"""
        import re
        match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', html)
        return match.group(1) if match else None
```


## Launch Velocity Detection

Product Hunt has a unique "launch day" pattern - products get most votes in first 24 hours.

```python
class ProductHuntVelocity:
    """Track product launch velocity on Product Hunt"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
    
    async def calculate_launch_score(self, product):
        """
        Launch Score (0-100):
        - How fast votes are coming in
        - Comment engagement
        - Category relevance
        - Time since launch
        """
        score = 0
        
        votes = product.get("votes", 0)
        comments = product.get("comments", 0)
        
        # Vote velocity (0-40)
        # Top products get 500+ votes on launch day
        if votes > 1000: score += 40
        elif votes > 500: score += 35
        elif votes > 300: score += 30
        elif votes > 200: score += 25
        elif votes > 100: score += 20
        elif votes > 50: score += 15
        
        # Comment engagement (0-25)
        # Comments indicate real interest
        if comments > 100: score += 25
        elif comments > 50: score += 20
        elif comments > 30: score += 15
        elif comments > 10: score += 10
        
        # Vote-to-comment ratio (0-15)
        # Healthy ratio = engaged community
        if votes > 0:
            ratio = comments / votes
            if ratio > 0.2: score += 15   # Very discussable
            elif ratio > 0.1: score += 10
            elif ratio > 0.05: score += 5
        
        # Category relevance (0-20)
        topics = product.get("topics", [])
        relevant_topics = ["developer-tools", "productivity", "artificial-intelligence", 
                          "open-source", "education", "programming"]
        matches = sum(1 for t in topics if any(rt in t.lower() for rt in relevant_topics))
        score += min(20, matches * 5)
        
        return min(100, score)
    
    def is_breaking_product(self, launch_score, product):
        """Determine if product is 'hot launch' worth featuring"""
        # Breaking = trending fast on launch day
        if launch_score >= 80:
            return "HOT_LAUNCH"
        elif launch_score >= 60:
            return "TRENDING"
        elif launch_score >= 40:
            return "NOTABLE"
        return "NORMAL"
```


## Product Hunt Breaking Patterns

```python
PH_BREAKING_PATTERNS = {
    "ai_tools": {
        "keywords": ["ai", "gpt", "llm", "chatbot", "automation"],
        "threshold": 300,  # votes
        "category": "AI Innovation"
    },
    "developer_tools": {
        "keywords": ["api", "sdk", "cli", "vscode", "plugin", "extension"],
        "threshold": 200,
        "category": "Dev Tool"
    },
    "productivity": {
        "keywords": ["notes", "todo", "calendar", "workflow"],
        "threshold": 250,
        "category": "Productivity"
    },
    "open_source": {
        "keywords": ["open source", "github", "self-hosted", "free"],
        "threshold": 150,
        "category": "Open Source"
    },
    "career_tools": {
        "keywords": ["resume", "portfolio", "interview", "job"],
        "threshold": 200,
        "category": "Career"
    }
}

def detect_breaking_launch(product):
    """Detect if a Product Hunt launch is breaking news"""
    name = product.get("name", "").lower()
    tagline = product.get("tagline", "").lower()
    text = f"{name} {tagline}"
    
    for pattern_type, config in PH_BREAKING_PATTERNS.items():
        if any(kw in text for kw in config["keywords"]):
            if product.get("votes", 0) >= config["threshold"]:
                return {
                    "is_breaking": True,
                    "type": pattern_type,
                    "category": config["category"]
                }
    
    return {"is_breaking": False}
```


## Student-Relevant Filtering

```python
STUDENT_RELEVANT_PRODUCTS = {
    "include_topics": [
        "developer-tools",
        "productivity",
        "artificial-intelligence",
        "education",
        "open-source",
        "programming",
        "career",
        "note-taking",
        "documentation"
    ],
    "include_keywords": [
        "free", "open source", "student", "github", "api",
        "vscode", "extension", "plugin", "cli", "automation"
    ],
    "exclude_keywords": [
        "enterprise", "b2b only", "sales team", "contact us"  # Too corporate
    ],
    "minimum_votes": 50,  # Must have some traction
}

def is_student_relevant_product(product):
    """Filter products for student newsletter"""
    topics = [t.lower() for t in product.get("topics", [])]
    text = f"{product.get('name', '')} {product.get('tagline', '')}".lower()
    votes = product.get("votes", 0)
    
    # Skip low traction
    if votes < STUDENT_RELEVANT_PRODUCTS["minimum_votes"]:
        return False
    
    # Check excluded keywords
    for kw in STUDENT_RELEVANT_PRODUCTS["exclude_keywords"]:
        if kw in text:
            return False
    
    # Check topics
    for topic in STUDENT_RELEVANT_PRODUCTS["include_topics"]:
        if topic in topics:
            return True
    
    # Check keywords
    for kw in STUDENT_RELEVANT_PRODUCTS["include_keywords"]:
        if kw in text:
            return True
    
    return False
```


## Product Hunt + Newsletter

```python
async def curate_product_hunt():
    """Curate Product Hunt launches for newsletter"""
    
    # Use RSS (free)
    rss = ProductHuntRSS()
    products = rss.fetch_all(limit_per_feed=10)
    
    # Or use API if you have token
    # api = ProductHuntGraphQL(PH_API_TOKEN)
    # products = await api.get_today_featured(first=20)
    
    curated = []
    for product in products:
        if not is_student_relevant_product(product):
            continue
        
        # Calculate launch score
        velocity = ProductHuntVelocity(supabase)
        launch_score = await velocity.calculate_launch_score(product)
        launch_tier = velocity.is_breaking_product(launch_score, product)
        
        # Check for breaking pattern
        breaking = detect_breaking_launch(product)
        
        if launch_tier in ["HOT_LAUNCH", "TRENDING"]:
            curated.append({
                "name": product["name"],
                "tagline": product["tagline"],
                "url": product["url"],
                "votes": product.get("votes", 0),
                "comments": product.get("comments", 0),
                "launch_score": launch_score,
                "tier": launch_tier,
                "category": breaking.get("category", "General"),
                "source": "Product Hunt"
            })
            
            # If HOT_LAUNCH, also trigger breaking news
            if launch_tier == "HOT_LAUNCH":
                await trigger_breaking_alert({
                    "platform": "producthunt",
                    "type": "hot_launch",
                    "product": product,
                    "score": launch_score
                })
    
    # Sort by launch score
    curated.sort(key=lambda x: x["launch_score"], reverse=True)
    
    return curated[:3]  # Top 3 products
```


## Execution Schedule

```yaml
name: Product Hunt Monitoring

on:
  schedule:
    - cron: "0 9,15,21 * * *"  # 9am, 3pm, 9pm UTC (covers launch day)
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - name: Fetch today's launches
        run: python ph_monitor.py
        env:
          PH_API_TOKEN: ${{ secrets.PH_API_TOKEN }}  # Optional
```


## Expected Volume

| Source | Products/Day | Student Relevant | Hot Launches (80+) |
|--------|--------------|------------------|-------------------|
| Featured | 20-30 | 3-5 | 0-1 |
| Newest | 50-100 | 5-10 | 1-2 |
| Tech/AI | 10-20 | 5-8 | 0-1 |

**Newsletter Integration:**
- "Tool of the Week" section
- Hot launches trigger breaking news alert
- 1-2 products per newsletter


## Cost

| Component | Cost |
|-----------|------|
| RSS feeds | Free |
| GraphQL API | Free (240 req/hour) |
| Firecrawl extraction | Included in 500 pages |
| **Total** | **$0** |


---

# Part 12: Updated Integration with All Platforms


## Complete Daily Execution Schedule

```
06:00 AM - Start Daily Cycle
  ├── [EVERY 15 MIN] Critical Sources (CRITICAL tier)
  │   ├── Twitter Tier 1 (20 accounts)
  │   ├── Hacker News front page
  │   └── GitHub Security Advisories
  │
  ├── [EVERY 30 MIN] Breaking Sources (BREAKING tier)  
  │   ├── Twitter Tier 2 (80 accounts)
  │   ├── Reddit Hot (20 subreddits)
  │   ├── YouTube Trending
  │   ├── GitHub Trending repos
  │   └── Product Hunt launches
  │
  ├── [EVERY 2 HOURS] Standard Sources
  │   ├── Twitter Tier 3 (200 accounts)
  │   ├── Reddit New posts
  │   ├── YouTube keyword search
  │   └── General websites RSS
  │
  ├── [EVERY 6 HOURS] Quality Sources
  │   ├── Medium publications
  │   └── GitHub new releases
  │
  └── [DAILY] Batch processing
      ├── General websites (Firecrawl)
      ├── Full article extraction
      └── Newsletter generation
```


## Updated Platform Summary

| Platform | Check Frequency | Daily Volume | Breaking Method |
|----------|-----------------|--------------|-----------------|
| **Twitter T1** | 15 min | ~200 tweets | Velocity + engagement |
| **Hacker News** | 15 min | ~100 stories | Points/hour velocity |
| **GitHub Security** | 15 min | 0-5 advisories | Critical severity |
| **Twitter T2** | 30 min | ~400 tweets | Verified + velocity |
| **Reddit Hot** | 30 min | ~300 posts | Upvote velocity |
| **YouTube** | 30 min | ~50 videos | View velocity |
| **GitHub Trending** | 30 min | ~25 repos | Star velocity |
| **Product Hunt** | 8 hours | ~30 products | Launch day votes |
| **Twitter T3** | 2 hours | ~400 tweets | Keywords only |
| **Reddit New** | 2 hours | ~500 posts | None |
| **General Websites** | 2-24 hours | ~200 articles | Cross-site overlap |
| **Medium** | 6 hours | ~50 articles | Quality score |


## Updated Final Cost

| Component | Monthly Cost |
|-----------|--------------|
| Twitter (twitterapi.io) | $0.90-5 |
| YouTube API | $0 |
| Reddit API | $0 |
| GitHub API | $0 |
| Hacker News API | $0 |
| Medium RSS | $0 |
| Product Hunt API | $0 |
| Firecrawl | $0 (500 pages) |
| Supabase | $0 (500MB) |
| SendGrid | $0 (100/day) |
| **Infrastructure** | $0-5 |
| **TOTAL** | **$0.90-10/month** |


## Breaking News Coverage by Platform

| Breaking Type | Primary Detection | Cross-Validation |
|---------------|-------------------|------------------|
| **Security (CVE)** | GitHub Security + Twitter | Hacker News + Reddit |
| **Major Layoffs** | Twitter T1 | Hacker News + Reddit |
| **New AI Models** | Twitter T1 + Hacker News | YouTube + Reddit |
| **Startup Funding** | Hacker News | Twitter + Product Hunt |
| **Hot Launches** | Product Hunt | Hacker News + Twitter |
| **Trending Repos** | GitHub | Hacker News + Twitter |
| **Career Advice** | Reddit + Medium | Twitter |
| **Technical Deep-dives** | Medium + Hacker News | - |


---

**Document Version:** 1.5  
**Last Updated:** January 31, 2026  
**Platforms:** Twitter, YouTube, Reddit, GitHub, General Websites, Hacker News, Medium, Product Hunt

