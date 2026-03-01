# College Newsletter Platform - AI Agent Guide

> **Project Type**: Documentation & Specification Repository  
> **Purpose**: Product Requirements Document (PRD) and Scraping Architecture for a college newsletter platform  
> **Language**: English  
> **Last Updated**: 2026-01-31

---

## Project Overview

This repository contains the **specification and architecture documentation** for a College Newsletter Platform - a calm, premium, low-noise content aggregation system designed for college students.

### What This Project Is

- **NOT a codebase** - This is a documentation repository containing product specifications
- **Architecture design** - Comprehensive scraping strategy for 750+ content sources
- **PRD documentation** - Product requirements and feature specifications

### Core Concept

A newsletter platform that delivers department-relevant learning content in **2-3 minute summaries**, organized by:
- **Home**: Important news only (5-7 "must-read" items)
- **Industrial Insights**: Trends, skills, jobs, company moves
- **Departments**: Department-specific hubs with weekly content
- **Student Stories**: Success stories and career journeys

### Target Audience
College students who struggle with long content due to time constraints and attention spans.

---

## Repository Structure

```
d:\newsletter/
├── AGENTS.md                          # This file - AI agent guide
├── scraping_logic.md                  # Main technical specification (33KB)
│                                    # Comprehensive scraping architecture
├── Scraping_Logic_Architecture.pdf    # PDF version of scraping architecture
└── context/                           # Supporting context documents
    ├── College_Newsletter_PRD_v1.docx # Product Requirements Document (source)
    ├── docx_content.txt               # Extracted PRD text
    ├── Untitled 21.pdf                # Additional design document
    ├── pdf_content.txt                # Semantic category mapping (text)
    └── pdf_tables.json                # Semantic category table (JSON)
```

---

## Key Documents Reference

### 1. `scraping_logic.md` - Technical Architecture

The primary technical document containing:

| Section | Content |
|---------|---------|
| Executive Summary | The challenge: scrape 750+ sources daily, zero API costs |
| Source Categories | Social media, event platforms, news sites, academic sources |
| Platform-Specific Logic | LinkedIn, Instagram, X/Twitter, YouTube, events, news, academic |
| Anti-Detection | Rate limiting, proxy rotation, headers & fingerprinting |
| Data Schema | PostgreSQL + Redis schema design |
| Orchestration | GitHub Actions vs n8n workflows |
| Error Handling | Retry logic, monitoring, alerting |
| Scalability | Current design (750 sources) → scaling to 2000+ |

### 2. `context/docx_content.txt` - Product Requirements Document (PRD)

Contains product specifications including:
- Problem statement and goals
- Information architecture (pages, navigation)
- Content processing pipeline
- Read format standard (2-3 minute format)
- Visualizer specifications (charts + explainers)
- Gamification elements
- Success metrics and risks

### 3. `context/pdf_tables.json` - Content Classification Matrix

Semantic category mapping across platforms (LinkedIn, Instagram, X, YouTube):
- Freshness / Now (breaking news)
- Utility / Skill (how-to content)
- Proof / Credibility (case studies)
- Problem / Pain (pain points)
- Identity / Narrative (personal stories)
- Belonging / Relatability (community content)
- Spectacle / Tension → Payoff
- Aspirational / Motivation

---

## Technology Stack (Planned/Proposed)

### Scraping Tools (from `scraping_logic.md`)

| Purpose | Recommended Tool |
|---------|------------------|
| HTTP Requests | `httpx` (async) |
| HTML Parsing | `BeautifulSoup4` |
| Browser Automation | `playwright` |
| RSS Parsing | `feedparser` |
| YouTube Metadata | `yt-dlp` |
| Instagram | `instaloader` |
| Twitter/X | `snscrape` + Nitter RSS |
| Rate Limiting | `ratelimit` library |
| Database ORM | `SQLAlchemy` |
| Task Queue | `Celery` |

### Database Architecture
- **PostgreSQL**: Primary storage, relational queries, full-text search
- **Redis**: URL deduplication cache, rate-limit tracking, job queues
- **Free tier options**: Supabase (PostgreSQL) + Upstash (Redis)

### Orchestration
- **Primary**: GitHub Actions (free, scheduled execution)
- **Secondary**: n8n on Railway (for long-running browser-based scrapers)

---

## Scraping Strategy Summary

### Source Distribution (~750 Sources)

| Source Type | Count | Method | Difficulty |
|-------------|-------|--------|------------|
| LinkedIn | 100-150 | Google search + aggregators | Hard |
| Instagram | 100-150 | Instaloader (anonymous) | Hard |
| X/Twitter | 100-150 | Nitter RSS bridges | Medium |
| YouTube | 50-100 | RSS + yt-dlp | Easy |
| Event Platforms | 50-100 | Direct API/scraping | Medium |
| Tech News Sites | 100-200 | RSS feeds | Easy |
| College Websites | 50-100 | Web scraping | Medium |
| Research/Journals | 50-100 | RSS/OAI-PMH | Easy |

### Key Scraping Principles
1. **RSS-first**: ~60% of sources use RSS (fast, reliable)
2. **Third-party proxies**: LinkedIn/Instagram via Google/aggregators
3. **Nitter for X**: Free RSS bridge (no API needed)
4. **YouTube RSS + yt-dlp**: Completely free, no limits
5. **Respectful scraping**: Rate limits, delays between requests

---

## Content Processing Pipeline

```
Scrape & Ingest → Clean & Extract → Deduplicate → Classify → Summarize → Publish
```

### Stages:
1. **Scrape & Ingest**: ~1000 sources → standard raw format
2. **Clean & Extract**: Remove nav/footer/subscribe blocks
3. **Deduplicate**: Exact + near-duplicate detection
4. **Classify**: Department, category, difficulty, priority score
5. **Summarize**: 2-3 minute format (hook, bullets, action step)
6. **Generate Visuals**: Template charts, AI images for highlights
7. **Assign & Publish**: Weekly bucket (YYYY-W##), auto-publish

### Read Format Standard (2-3 Minutes)
- **Headline**: Max 8 words
- **Why it matters**: 1 line
- **3-6 bullets**: One idea per bullet
- **Optional example**: 1-2 lines
- **Action step**: 1 line

---

## Database Schema Overview

### Core Tables:
- `sources`: Source metadata, scraping method, status
- `raw_content`: Scraped content with content hash for dedup
- `processed_content`: Summarized, classified content
- `events`: Event-specific data (hackathons, workshops)
- `scrape_logs`: Execution logs for monitoring

### Redis Keys:
- `dedup:urls` → SET of content_hash (TTL: 30 days)
- `ratelimit:{domain}` → Counter for rate limiting
- `queue:scrape` → List of source_ids to scrape
- `failed:{source_id}` → Error count and timestamps

---

## Daily Execution Schedule

```
06:00 AM - Start
    ├── [PARALLEL] RSS Feeds (News, YouTube, arXiv) ~15 min
    ├── [PARALLEL] Event Platforms ~30 min
    ├── [SEQUENTIAL] X/Twitter via Nitter ~1 hour
    ├── [SEQUENTIAL] Instagram via Instaloader ~2 hours
    ├── [SEQUENTIAL] LinkedIn via Google Search ~45 min
09:30 AM - Scraping complete
    ├── Deduplication pass
    ├── Classification and tagging
    ├── Summary generation (AI)
11:00 AM - Content ready for review
    └── Daily report sent
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Instagram IP ban | High | Medium | Rotate proxies, aggressive delays |
| LinkedIn account ban | High | High | Never use logged-in scraping |
| Nitter instances down | Medium | Low | Maintain 5+ fallback instances |
| GitHub Actions limits | Low | High | Split workflows, optimize runtime |
| Database costs | Low | Medium | Use Supabase free tier |
| Parsing failures | Medium | Low | Robust error handling, alerts |

---

## Development Conventions

### When Working on This Repository:

1. **Maintain document consistency**: Changes to `scraping_logic.md` should be reflected in the PDF version
2. **Version control**: Documents have version numbers (e.g., PRD v1.0, Scraping Logic v1.0)
3. **Date tracking**: Update dates when making significant changes
4. **Keep format standards**: Follow the existing markdown structure

### Document Update Workflow:
1. Edit `.md` or `.txt` source files
2. Update version and date headers
3. If architecture changes significantly, update the PDF export
4. Update this `AGENTS.md` if structure or conventions change

---

## MVP Scope (First Release)

From the PRD:
- News-first homepage + category filters
- Industrial Insights page
- Departments hub + department detail page
- Student Stories page
- 2-3 minute summary cards
- Template charts + 1-3 AI visuals per week
- Right-side suggestions with 4 chips

---

## Roadmap (Next Iterations)

- Personalized onboarding goals and smarter ranking
- Saved library + collections
- Skill tree progression screen
- Email/WhatsApp weekly digest delivery
- Faculty/staff dashboard for department visibility

---

## Important Notes for AI Agents

1. **This is a spec repo, not a code repo** - There are no build commands, tests, or deployment scripts here
2. **Documents are the deliverables** - The markdown and PDF files ARE the project output
3. **Future implementation** - This repository documents what needs to be built, not working code
4. **Language**: All documentation is in English
5. **Audience**: College students (India-focused based on context like Unstop, Devfolio platforms)

---

## Summary

This repository contains comprehensive specifications for building a college newsletter aggregation platform. The main deliverable is the scraping architecture (`scraping_logic.md`) that outlines how to collect content from 750+ sources daily at zero cost, plus the product requirements (`context/docx_content.txt`) defining the user experience and content format.

When working with this repository, focus on maintaining accurate, well-structured documentation that can guide future implementation.
