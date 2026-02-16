# 📰 College Newsletter Platform — Product Reference

> **Version:** 1.0.0 · **PRD Date:** 26 Jan 2026 · **Stack:** FastAPI + PostgreSQL + Redis + Multi-AI  
> **Cost:** $0/month (self-hosted + free AI) · **License:** Proprietary

---

## Table of Contents

1. [Product Vision](#1-product-vision)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Model](#3-data-model)
4. [Backend Services](#4-backend-services)
5. [API Reference](#5-api-reference)
6. [Content Pipeline](#6-content-pipeline)
7. [Scraper Platform](#7-scraper-platform)
8. [AI Integration](#8-ai-integration)
9. [Frontend](#9-frontend)
10. [Authentication & Security](#10-authentication--security)
11. [Infrastructure & DevOps](#11-infrastructure--devops)
12. [Configuration Reference](#12-configuration-reference)
13. [Development Status](#13-development-status)
14. [Building Blocks Reference](#14-building-blocks-reference)

---

## 1. Product Vision

### What It Is
A **calm, premium, low-noise newsletter platform** for college students. Instead of long reads, every update is condensed into a **2–3 minute summary** and organised by department, industry insights, and student success stories.

### Problem Statement
- Students struggle to read long content due to poor attention and time constraints.
- Real competition is high-attention platforms (Instagram/YouTube), not other newsletters.
- If relevancy is slightly off or language feels difficult, students drop immediately.
- Students want visible growth (progress) to stay consistent.

### Core Principles
| Principle | Description |
|-----------|-------------|
| **Calm in a noisy world** | Minimal colours, controlled density, no clutter |
| **Nostalgic + Premium** | Editorial feel, consistent typography, predictable layouts |
| **High signal only** | Fewer items, better curation |
| **Readable by default** | Bullets over paragraphs, simple language |

### Target Read Format
Every article follows a strict "2–3 minute" card format:
1. **Headline** — max 8 words
2. **Why it matters** — 1 line
3. **3–6 bullets** — one idea per bullet, short lines
4. **Optional quick example** — 1–2 lines
5. **Action step** — 1 line

### Success Metrics
| Metric | Target |
|--------|--------|
| Weekly Active Users (WAU) | Growing |
| Average session length | 2–6 minutes |
| Completion rate per read | > 60% |
| Save/share rate | High |
| Relevancy feedback (downvotes) | Low |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                 │
│   Frontend SPA (HTML/CSS/JS)  ·  API Consumers  ·  Admin        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / REST
┌───────────────────────────▼─────────────────────────────────────┐
│                     FastAPI Backend (app/)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Auth API │  │ Feed API │  │ AI API   │  │ Pipeline/      │  │
│  │ /auth/*  │  │ /feed/*  │  │ /ai/*    │  │ Scraper API    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬────────┘  │
│       │              │             │                │            │
│  ┌────▼──────────────▼─────────────▼────────────────▼────────┐  │
│  │                    Services Layer                          │  │
│  │  AuthService · FeedService · ContentProcessor              │  │
│  │  PipelineService · ScraperService · VectorService          │  │
│  └────┬──────────────┬─────────────┬────────────────┬────────┘  │
│       │              │             │                │            │
│  ┌────▼────┐   ┌─────▼────┐  ┌────▼─────────────┐  │           │
│  │   JWT   │   │PostgreSQL│  │  AI Providers     │  │           │
│  │ bcrypt  │   │ 11 tables│  │  (5 providers)   │  │           │
│  └─────────┘   └──────────┘  └──────────────────┘  │           │
│                     │                                │           │
│               ┌─────▼────┐                    ┌─────▼────────┐  │
│               │  Redis   │                    │  Scraper     │  │
│               │  Cache   │                    │  Platform    │  │
│               └──────────┘                    │  (external)  │  │
│                                               └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Data Flow
```
Sources (7) ──► Scraper Platform ──► raw_content (DB)
                                          │
                                    ContentProcessor
                                    (score + AI summarise + tag)
                                          │
                                    processed_content (DB)
                                          │
                                    VectorService (embed)
                                          │
                                    vector_embeddings (DB)
                                          │
                                    FeedService ──► User Feed
```

---

## 3. Data Model

The platform uses **11 relational tables** managed by SQLAlchemy 2.0 (async) with Alembic migrations.

### Entity Relationship Summary

```
users ─────────┬─── user_reads ──────── processed_content
               ├─── user_saves ─────── processed_content
               └─── user_feedback ──── processed_content

sources ───────┬─── raw_content ──────► processed_content ──┬── vector_embeddings
               └─── velocity_metrics                        ├── hookline_queue
                                                            └── breaking_alerts
```

### Table Details

#### `users`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated via `Base` |
| `email` | String(255) | Unique, indexed |
| `password_hash` | String(255) | bcrypt hash |
| `full_name` | String(255) | Optional |
| `avatar_url` | Text | Optional |
| `department` | String(100) | Academic department |
| `year_of_study` | Integer | 1–4+ |
| `graduation_year` | Integer | Target year |
| `college_name` | String(255) | Institution name |
| `interests` | ARRAY(String) | User interest tags |
| `content_preferences` | JSONB | Content tuning prefs |
| `notification_settings` | JSONB | Email/breaking/weekly toggles |
| `streak_days` | Integer | Consecutive read days |
| `total_reads` | Integer | Lifetime article reads |
| `skill_badges` | ARRAY(String) | Earned badges |
| `weekly_goal` | Integer | Default 7 |
| `is_active` | Boolean | Account status |
| `is_admin` | Boolean | Admin flag |
| `email_verified` | Boolean | Verification status |
| `last_login_at` | DateTime | Last login timestamp |

#### `sources`
| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `name` | String(255) | Source name (e.g. "Hacker News") |
| `source_type` | String(50) | Type: rss, api, scraper |
| `url` | Text | Source URL |
| `scraper_class` | String(100) | Python class name |
| `is_active` | Boolean | Whether scraping is enabled |
| `scrape_frequency_minutes` | Integer | How often to scrape |
| `reliability_score` | Float | Source quality score |
| `default_categories` | ARRAY(String) | Auto-assigned categories |
| `default_tags` | ARRAY(String) | Auto-assigned tags |

#### `raw_content`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `source_id` | FK → sources | Origin source |
| `external_id` | String(500) | Original ID from source |
| `title` | Text | Original title |
| `url` | Text | Original URL |
| `author` | String(500) | Author name |
| `content_text` | Text | Full text body |
| `metadata_json` | JSONB | Extra metadata |
| `content_hash` | String(64) | SHA-256 dedup hash |
| `status` | String(20) | `pending` / `processed` / `failed` |
| `scraped_at` | DateTime | When scraped |
| `processed_at` | DateTime | When processing finished |

#### `processed_content`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `raw_content_id` | FK → raw_content | Source raw item |
| `title` | String(500) | Processed headline |
| `hook_line` | String(300) | Attention-grabbing hook |
| `summary` | Text | AI-generated summary |
| `bullets` | JSONB | 3–6 bullet key points |
| `action_step` | Text | Action step text |
| `category` | String(50) | Content category |
| `topics` | ARRAY(String) | Topic tags |
| `difficulty_level` | String(20) | Easy/Medium/Advanced |
| `attractiveness_score` | Integer | 0–100 quality score |
| `engagement_score` | Float | Engagement metric |
| `read_time_minutes` | Integer | Estimated read time |
| `source_name` | String(100) | Source attribution |
| `source_url` | Text | Link back to source |
| `published_at` | DateTime | Publication timestamp |
| `is_breaking` | Boolean | Breaking news flag |
| `is_featured` | Boolean | Featured/pinned flag |
| `weekly_bucket` | String(10) | YYYY-W## bucket |
| `department_relevance` | JSONB | Per-department relevance |
| `opportunity_*` | Various | Job/internship metadata |

#### `vector_embeddings`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `content_id` | FK → processed_content | Linked content |
| `embedding` | JSONB | Vector array |
| `model_version` | String(50) | Model identifier |

#### `hookline_queue`
Queue for AI hookline/headline generation jobs.

#### `breaking_alerts`
Breaking news alerts linked to processed content, with severity levels and auto-detection metadata.

#### `velocity_metrics`
Engagement velocity tracking per source for breaking news detection (BNDE system).

#### `user_reads` / `user_saves` / `user_feedback`
User interaction tables tracking read history (with completion %), bookmarks (with collections), and feedback (type + reason).

---

## 4. Backend Services

All services live in `backend/app/services/` and are async, taking an `AsyncSession` for DB access.

### `AuthService`
**File:** `auth_service.py` (3.9 KB)
- User registration with password hashing (bcrypt)
- Login with JWT access + refresh tokens
- Password change
- User profile CRUD
- User statistics

### `FeedService`
**File:** `feed_service.py` (11.3 KB)
- `get_personalized_feed()` — Filtered by user interests, department; sorted by attractiveness + freshness
- `get_trending_content()` — Ranked by engagement score
- `get_breaking_news()` — Breaking alerts only
- `get_content_by_category()` — Category filter
- `get_daily_digest()` — Top 5 curated items for the day
- `record_read()` — Track reading activity
- `get_feed_stats()` — Aggregate feed analytics

### `ContentProcessor`
**File:** `content_processor.py` (12.5 KB)
- `calculate_attractiveness_score()` — 0–100 scoring based on engagement, recency, content quality
- `process_pending_items()` — Batch-process raw → processed
- `process_single_item()` — Process one item
- `_process_with_nlp()` — Full AI processing (high-score items): summarisation, hookline, bullets
- `_process_basic()` — Snippet-only processing (low-score items)
- `_detect_category()` — Rule-based category assignment
- `_extract_topics()` — Topic tag extraction

### `PipelineService`
**File:** `pipeline_service.py` (4.8 KB)
- `run_full_pipeline()` — End-to-end: process raw → embed → update feed stats
- `process_single_item()` — Single item through full pipeline
- `get_pipeline_status()` — Status counts for raw/processed/pending embeddings

### `ScraperService`
**File:** `scraper_service.py` (12.9 KB)
- `ensure_sources_exist()` — Bootstraps source records in the database
- `run_scraper(name)` — Run a specific scraper by name
- `run_all_scrapers()` — Execute all scrapers sequentially
- `_scrape_hackernews()` / `_scrape_reddit()` / `_scrape_github()` / `_scrape_medium()` / `_scrape_producthunt()`
- `_store_raw_content()` — Dedup via content hash + store in `raw_content`
- `get_scraper_status()` — Per-source item counts

### `VectorService`
**File:** `vector_service.py` (6.8 KB)
- `embed_content()` — Generate vector embedding for a processed content item
- `embed_pending_content()` — Batch-embed items without embeddings
- `find_similar_content()` — Cosine similarity search (Python-based; pgvector for prod)
- `search_by_text()` — Text → embedding → similarity search, with ilike fallback

---

## 5. API Reference

**Base URL:** `http://localhost:8000`  
**API Prefix:** `/api/v1`  
**Docs:** `http://localhost:8000/docs` (Swagger UI)

### Health & Root

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (status, version) |
| `GET` | `/` | Root welcome message |

### Auth — `/api/v1/auth`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/register` | — | Create account |
| `POST` | `/login` | — | Login → access + refresh tokens |
| `POST` | `/refresh` | Bearer | Refresh access token |
| `GET` | `/me` | Bearer | Get current user profile |
| `PUT` | `/me` | Bearer | Update profile |
| `POST` | `/change-password` | Bearer | Change password |
| `GET` | `/stats` | Bearer | User engagement stats |

### AI — `/api/v1/ai`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/status` | Active AI provider status |
| `GET` | `/providers` | All available providers |
| `POST` | `/summarize` | Summarise text content |
| `POST` | `/headline` | Generate hookline/headline |
| `POST` | `/embed` | Generate text embedding |

### Feed — `/api/v1/feed`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/personalized` | Optional | Personalised feed (interests, dept) |
| `GET` | `/trending` | — | Trending by engagement |
| `GET` | `/breaking` | — | Breaking news alerts |
| `GET` | `/daily-digest` | — | Top daily picks |
| `GET` | `/search?q=` | — | Full-text + vector search |
| `GET` | `/saved` | Bearer | User's bookmarked articles |
| `GET` | `/category/{cat}` | — | Filter by category |
| `POST` | `/{id}/read` | — | Record read event |
| `POST` | `/{id}/save` | Bearer | Bookmark article |
| `DELETE` | `/{id}/save` | Bearer | Remove bookmark |
| `POST` | `/{id}/feedback` | Bearer | Submit feedback (like/dislike/report) |
| `GET` | `/stats` | — | Feed aggregate stats |

### Pipeline — `/api/v1/pipeline`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/run` | Execute full pipeline |
| `GET` | `/status` | Pipeline status (pending/processed counts) |
| `POST` | `/process` | Process pending raw items |
| `POST` | `/embed` | Generate pending embeddings |
| `GET` | `/stats` | Pipeline statistics |

### Scrapers — `/api/v1/scrapers` (Admin)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/status` | All scraper statuses |
| `POST` | `/run/{name}` | Run specific scraper |
| `POST` | `/run-all` | Run all scrapers |
| `POST` | `/process-pending` | Process pending raw items |
| `GET` | `/stats` | Scraping statistics |

---

## 6. Content Pipeline

The full content pipeline runs in 3 stages:

### Stage 1 — Scrape
```
ScraperService.run_scraper("hackernews")
    → HackerNewsScraper.scrape(limit=30)
    → _store_raw_content()  [dedup via SHA-256 hash]
    → raw_content (status="pending")
```

### Stage 2 — Process
```
ContentProcessor.process_pending_items(limit=10)
    → For each raw_content:
        1. calculate_attractiveness_score() → 0–100
        2. IF score >= 40: _process_with_nlp()
           - AI summarization (via AIProvider)
           - AI headline generation
           - Category detection + topic extraction
        3. ELSE: _process_basic()
           - Snippet truncation, basic metadata
        4. → processed_content
```

### Stage 3 — Embed & Deliver
```
VectorService.embed_pending_content(limit=10)
    → For each unembedded processed_content:
        1. Concatenate title + summary
        2. AIProvider.embed(text) → vector
        3. → vector_embeddings
    → FeedService delivers via personalized/trending/breaking endpoints
```

### Attractiveness Scoring (0–100)
The scoring algorithm factors in:
- **Engagement signals** — upvotes, comments, stars (scaled)
- **Source reliability** — platform-specific weights
- **Recency** — exponential decay from hours old
- **Content quality** — title length, body presence, metadata richness
- **Topic relevance** — keyword matching for tech/CS terms

---

## 7. Scraper Platform

**Location:** `scraper_platform/`  
**Orchestrator:** `main.py` → `ScraperOrchestrator`

### Base Architecture
- `BaseScraper` — Async base class with retry logic, dedup, structured logging
- `ExcelTracker` — Results tracking to Excel + JSON files
- All scrapers use `httpx` (async HTTP) + `BeautifulSoup` for parsing

### Scraper Status

| Scraper | File | Status | Method |
|---------|------|--------|--------|
| **Hacker News** | `hackernews_scraper.py` | ✅ Working | API (algolia) |
| **Reddit** | `reddit_scraper.py` | ✅ Working | JSON API (.json suffix) |
| **GitHub Trending** | `github_scraper.py` | ✅ Working | HTML scraping |
| **Medium** | `medium_scraper.py` | ✅ Working | RSS feeds |
| **Product Hunt** | `producthunt_scraper.py` | ✅ Working | HTML scraping |
| **Twitter/X** | `twitter_scraper.py` | ⚠️ Stub | Not implemented (API access barriers) |
| **YouTube** | `youtube_scraper.py` | ⚠️ Stub | Not implemented |

### Output Format (per item)
```json
{
  "title": "string",
  "url": "string",
  "author": "string",
  "source": "string",
  "content_text": "string",
  "engagement": {
    "upvotes": 0,
    "comments": 0,
    "stars": 0
  },
  "metadata": {},
  "scraped_at": "ISO-8601"
}
```

---

## 8. AI Integration

**Location:** `backend/app/integrations/`  
**Unified Interface:** `AIProvider` class (auto-selects best available provider)

### Provider Priority Chain
```
Groq (fast, free tier)
  → OpenAI (best quality, paid)
    → HuggingFace (free tier)
      → Pollinations AI (free default, no signup)
        → Mock (demo fallback)
```

### AI Capabilities

| Capability | Method | Used For |
|------------|--------|----------|
| **Summarize** | `AIProvider.summarize(title, content, category)` | 2–3 minute card summaries |
| **Headline** | `AIProvider.headline(title, content)` | Hookline generation |
| **Embed** | `AIProvider.embed(text)` | Vector embeddings for similarity |

### Provider Details

| Provider | File | API Key Env Var | Cost |
|----------|------|-----------------|------|
| Groq | `groq_service.py` | `GROQ_API_KEY` | Free tier (20 req/min) |
| OpenAI | `openai_service.py` | `OPENAI_API_KEY` | Paid (~$5–20/mo) |
| HuggingFace | `huggingface_service.py` | `HUGGINGFACE_API_KEY` | Free tier |
| Pollinations | `free_ai_service.py` | None | Free, no signup |
| Ollama | `ollama.py` | `USE_LOCAL_AI=true` | Free (local CPU/GPU) |

### Health Monitoring
- `GET /api/v1/ai/status` — Checks active provider health
- `GET /api/v1/ai/providers` — Lists all providers with config status
- `check_ai_status()` — Backend utility for provider diagnostics

---

## 9. Frontend

**Location:** `frontend/`  
**Type:** Vanilla SPA (HTML + CSS + JS) — no build step

### Pages

| File | Description |
|------|-------------|
| `index.html` (57 KB) | Main SPA: feed, auth, search, filters, dark mode, bookmarks |
| `reader.html` (31 KB) | Article reader view with full content display |

### Features
- **Responsive design** — Mobile-first layout
- **Dark mode** — Toggle support
- **Auth UI** — Login/register modals
- **Feed views** — Trending, personalised, breaking, category filter
- **Search** — Full-text query
- **Bookmarks** — Save/unsave articles
- **Article reader** — Full article with summary, bullets, metadata

### Serving
- In dev: open `frontend/index.html` directly in browser
- In production: served as static files via FastAPI (`/static/*` mount)

---

## 10. Authentication & Security

**Location:** `backend/app/core/security.py`

### Mechanism
- **Password hashing:** bcrypt (via `bcrypt` library)
- **JWT tokens:** `python-jose` with HS256
  - **Access token:** 30 min expiry (configurable)
  - **Refresh token:** 7 day expiry (configurable)
- **Token payload:** `{ exp, sub (user_id), type (access/refresh) }`

### API Protection
- `get_current_active_user` dependency — requires valid access token
- `get_optional_current_user` — authentication optional (for public + personalised feeds)
- Admin endpoints — checked via `user.is_admin` flag

### Key Functions
| Function | Purpose |
|----------|---------|
| `verify_password(plain, hash)` | Check password against bcrypt hash |
| `get_password_hash(password)` | Generate bcrypt hash |
| `create_access_token(subject)` | Issue short-lived JWT |
| `create_refresh_token(subject)` | Issue long-lived refresh JWT |
| `decode_token(token)` | Verify + decode JWT |
| `get_token_subject(token)` | Extract user ID from JWT |

---

## 11. Infrastructure & DevOps

### Docker Compose (`backend/docker-compose.yml`)

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `postgres` | postgres:15-alpine | 5432 | Primary database |
| `redis` | redis:7-alpine | 6379 | Cache + task queue |
| `api` | Custom Dockerfile | 8000 | Backend server (optional) |

### CI/CD (`.github/workflows/ci.yml`)

**Triggers:** Push to `main`/`develop`, PRs to `main`

| Job | Steps |
|-----|-------|
| `test` | Install deps → pytest → black/isort check → mypy |
| `lint` | flake8 (critical errors + style) |

CI spins up PostgreSQL 15 + Redis 7 as service containers.

### Database Migrations
```bash
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

---

## 12. Configuration Reference

All config is via environment variables, loaded through Pydantic `BaseSettings` in `backend/app/config.py`.

### Required Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `SECRET_KEY` | (change in production) | App secret key |
| `JWT_SECRET_KEY` | (change in production) | JWT signing key |

### Optional Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Debug mode flag |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `GROQ_API_KEY` | None | Groq AI API key |
| `OPENAI_API_KEY` | None | OpenAI API key |
| `HUGGINGFACE_API_KEY` | None | HuggingFace API key |
| `USE_LOCAL_AI` | `false` | Enable Ollama |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `SENDGRID_API_KEY` | None | Email delivery |
| `DISCORD_WEBHOOK_URL` | None | Discord notifications |
| `CORS_ORIGINS` | `[localhost:3000, ...]` | Allowed CORS origins |
| `RATE_LIMIT_REQUESTS` | `100` | Requests per period |
| `RATE_LIMIT_PERIOD` | `60` | Rate limit window (seconds) |
| `STORAGE_TYPE` | `local` | File storage type (`local` / `s3`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token lifetime |

---

## 13. Development Status

### ✅ Complete — Phase 1: Foundation
- [x] FastAPI backend with async architecture
- [x] PostgreSQL + SQLAlchemy 2.0 async with 11 tables
- [x] Alembic database migrations
- [x] Redis integration (cache + queue)
- [x] JWT auth (access + refresh tokens) with bcrypt
- [x] User profiles: academic info, preferences, gamification
- [x] CI/CD pipeline (GitHub Actions)

### ✅ Complete — Phase 2: AI Integration
- [x] 5 AI providers with automatic fallback chain
- [x] Content summarisation, headline generation, embeddings
- [x] AI status monitoring + provider health checks
- [x] Provider auto-selection

### ✅ Complete — Phase 3: Content Pipeline
- [x] 5 of 7 scrapers working (HN, Reddit, GitHub, Medium, Product Hunt)
- [x] Scraper management API with admin controls
- [x] Content processing pipeline: scoring → AI summary → tag → dedup
- [x] Feed service: personalised, trending, breaking, digest, search, category
- [x] Full pipeline orchestration (scrape → process → embed → publish)
- [x] Frontend SPA: responsive, dark mode, article reader, bookmarks, auth, search

### ⚠️ Partially Done
- [ ] **Twitter scraper** — stub only (API access challenges)
- [ ] **YouTube scraper** — stub only
- [ ] **Celery task scheduler** — tasks defined, scheduler not running
- [ ] **Vector similarity search** — embeddings generated, search function built but not wired to endpoint

### ❌ Not Started (Future Roadmap)
- [ ] Email delivery (SendGrid config ready, logic not built)
- [ ] Discord webhook notifications
- [ ] Admin dashboard UI (API endpoints exist, no web panel)
- [ ] React/Vue production frontend (currently pure HTML/CSS/JS)
- [ ] Rate limiting enforcement
- [ ] Monitoring & observability (APM, logging aggregation)
- [ ] Information architecture pages: Industrial Insights, Departments Hub, Student Stories
- [ ] Recommendation engine with sidebar suggestions (4 chips, max 7 items)
- [ ] Gamification UI: weekly goal meter, streaks, badges, skill tree
- [ ] Template-based chart/visual generation for articles
- [ ] Personalised onboarding flow
- [ ] Saved library + collections
- [ ] Email/WhatsApp weekly digest delivery
- [ ] Faculty/staff dashboard

---

## 14. Building Blocks Reference

A quick-reference map of every module and its purpose, for navigation.

### Backend — `backend/app/`

| Path | Type | Purpose |
|------|------|---------|
| `main.py` | Entry | FastAPI app init, lifespan, CORS, static mount |
| `main_lite.py` | Entry | Lightweight server variant |
| `config.py` | Config | Pydantic `Settings` (env vars) |
| **`api/`** | | |
| `api/__init__.py` | Router | Master API router assembly |
| `api/deps.py` | Deps | `get_db`, `get_current_user`, dependency injection |
| `api/v1/auth.py` | Routes | Auth endpoints (register, login, refresh, profile) |
| `api/v1/ai.py` | Routes | AI endpoints (status, providers, summarise, headline, embed) |
| `api/v1/feed.py` | Routes | Feed endpoints (personalised, trending, breaking, search, CRUD) |
| `api/v1/pipeline.py` | Routes | Pipeline endpoints (run, status, process, embed) |
| `api/v1/scrapers.py` | Routes | Scraper admin endpoints (run, run-all, status) |
| **`core/`** | | |
| `core/security.py` | Security | JWT create/decode, bcrypt hash/verify |
| **`models/`** | | |
| `models/base.py` | ORM | Base model with UUID PK, timestamps |
| `models/user.py` | ORM | User, UserReads, UserSaves, UserFeedback |
| `models/content.py` | ORM | Source, RawContent, ProcessedContent, VectorEmbedding, HooklineQueue, BreakingAlert, VelocityMetrics |
| **`schemas/`** | | |
| `schemas/user.py` | Pydantic | User request/response schemas |
| `schemas/content.py` | Pydantic | Content + feedback schemas |
| `schemas/responses.py` | Pydantic | Standard API response wrappers |
| **`services/`** | | |
| `services/auth_service.py` | Logic | User registration, login, profile ops |
| `services/feed_service.py` | Logic | Feed curation, trending, breaking, digest |
| `services/content_processor.py` | Logic | Raw → processed (scoring, AI, tagging) |
| `services/pipeline_service.py` | Logic | End-to-end pipeline orchestration |
| `services/scraper_service.py` | Logic | Scraper execution + DB storage |
| `services/vector_service.py` | Logic | Embedding generation + similarity search |
| **`integrations/`** | | |
| `integrations/ai_provider.py` | AI | Unified AI interface + auto-select |
| `integrations/groq_service.py` | AI | Groq API wrapper |
| `integrations/openai_service.py` | AI | OpenAI API wrapper |
| `integrations/huggingface_service.py` | AI | HuggingFace Inference wrapper |
| `integrations/free_ai_service.py` | AI | Pollinations (free) + Mock fallback |
| `integrations/ollama.py` | AI | Local Ollama wrapper |
| **`tasks/`** | | |
| `tasks/` | Celery | Task definitions (not yet scheduled) |

### Scraper Platform — `scraper_platform/`

| Path | Purpose |
|------|---------|
| `main.py` | Orchestrator: runs all scrapers, saves results, generates newsletter summary |
| `src/base_scraper.py` | Async base class with retry, dedup, logging |
| `src/excel_tracker.py` | Excel + JSON results tracking |
| `src/scrapers/hackernews_scraper.py` | Hacker News (Algolia API) |
| `src/scrapers/reddit_scraper.py` | Reddit (.json API) |
| `src/scrapers/github_scraper.py` | GitHub Trending (HTML) |
| `src/scrapers/medium_scraper.py` | Medium (RSS) |
| `src/scrapers/producthunt_scraper.py` | Product Hunt (HTML) |
| `src/scrapers/twitter_scraper.py` | Twitter/X (stub) |
| `src/scrapers/youtube_scraper.py` | YouTube (stub) |

### Frontend — `frontend/`

| Path | Purpose |
|------|---------|
| `index.html` | Main SPA — feed, auth, search, filters, dark mode |
| `reader.html` | Article reader — full content, summary, metadata |

### Docs & Reports

| Path | Purpose |
|------|---------|
| `docs/QUICKSTART.md` | 5-minute setup guide |
| `docs/FREE_AI_OPTIONS.md` | Free AI provider comparison |
| `docs/GROQ_SETUP.md` | Groq API key setup |
| `docs/OLLAMA_SETUP.md` | Local Ollama setup |
| `docs/OPENAI_SETUP.md` | OpenAI API key setup |
| `docs/REPO_SUMMARY.md` | Repository overview |
| `reports/AGENTS.md` | Agent architecture docs |
| `reports/Master_Scraping_Logic.md` | Detailed scraping logic design |
| `reports/Source_Categories.md` | Source categorisation scheme |
| `reports/scraping_logic.md` | Scraping implementation notes |
| `reports/Ultimate_Free_Scraping_Architecture.md` | Free scraping architecture design |
| `reports/Twitter_Scraping_Options.md` | Twitter API alternatives analysis |
| `context/College_Newsletter_PRD_v1.docx` | Original PRD document |
| `context/docx_content.txt` | Extracted PRD text |

### Infrastructure

| Path | Purpose |
|------|---------|
| `backend/docker-compose.yml` | PostgreSQL + Redis + API containers |
| `backend/alembic/` | Database migration scripts |
| `backend/.env.example` | Environment variable template |
| `backend/requirements.txt` | Python dependencies (FastAPI, SQLAlchemy, httpx, etc.) |
| `.github/workflows/ci.yml` | CI pipeline (pytest, flake8, black, mypy) |
| `start_server.py` | Root-level server startup script |

---

*Generated from codebase analysis on 16 Feb 2026.*
