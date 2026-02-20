# NEWS DAY — College Newsletter Platform

A department-aware news aggregation platform for engineering college students in India. Scrapes 200+ sources via RSS feeds, processes content with AI, and delivers curated news, trending stories, and research papers — all filtered by department.

**Stack:** FastAPI + PostgreSQL + Vanilla JS  
**Target:** Engineering colleges in Tamil Nadu / South India  
**Cost:** $0/month (self-hosted + free AI via Pollinations)

---

## Features

- **10 Engineering Departments** — CSE, IT, AI&DS, ECE, EEE, Mechanical, Civil, Biotech, Chemical, Aerospace
- **200+ Curated Sources** — Global tech + 38 India-specific RSS feeds (TOI, The Hindu, NDTV, ET, The Wire, etc.)
- **Research Papers** — Top picks from Semantic Scholar, Crossref, OpenAlex, and PubMed
- **Breaking News** — AI-scored attractiveness ranking with source-type bonuses
- **Instant Loading** — Pre-computed feed cache (4ms response) + localStorage caching
- **AI Processing** — Summarization, headline generation via Pollinations (free, no API key)
- **Department Filtering** — Content tagged and filtered per department
- **Auth System** — JWT-based signup/login with department selection
- **Parallel Scraping** — Async RSS scraping with semaphore-controlled concurrency

---

## Project Structure

```
newsletter/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/v1/             # Routes: auth, ai, feed, pipeline, scrapers, departments
│   │   ├── core/               # Security (JWT, bcrypt)
│   │   ├── models/             # SQLAlchemy models (User, Source, Content, CachedFeed)
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic (auth, feed, pipeline, content processor)
│   │   ├── integrations/       # AI providers (Pollinations, Groq, OpenAI, Ollama, HF)
│   │   ├── departments.py      # Department registry + source mappings
│   │   └── config.py           # Pydantic settings (.env loader)
│   ├── alembic/                # Database migrations
│   ├── requirements.txt
│   └── .env.example            # Configuration template
│
├── frontend/                   # Web UI (vanilla HTML/CSS/JS)
│   ├── index.html              # Home — breaking news, trending, research picks
│   ├── stories.html            # All stories feed
│   ├── insights.html           # AI-generated insights
│   ├── research.html           # Dedicated research papers page
│   ├── department.html         # Department-specific feed
│   ├── auth.html               # Login/signup with department selector
│   └── reader.html             # Article reader view
│
├── scrapers/                   # Scraper pipeline (main entry points)
│   ├── run_all.py              # Unified pipeline: seed → scrape → process → cache
│   ├── run_rss.py              # Parallel RSS scraper (asyncio + semaphore)
│   ├── run_research.py         # Research paper scraper (4 APIs)
│   ├── run_general.py          # HN, Reddit, GitHub, Medium, ProductHunt scrapers
│   ├── seed_sources.py         # Seed department sources to DB
│   └── refresh_cache.py        # Pre-compute cached feeds for all departments
│
├── scraper_platform/           # Scraper implementations
│   ├── main.py                 # Orchestrator
│   └── src/
│       ├── base_scraper.py     # Async base class with retry + dedup
│       └── scrapers/           # Individual scrapers (RSS, HN, Reddit, etc.)
│
├── docs/                       # Setup & reference guides
├── reports/                    # Architecture design docs
├── context/                    # PRD & planning references
├── start_server.py             # Start the FastAPI server
└── .github/workflows/ci.yml   # CI pipeline
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+

### Setup

```bash
# Clone and install
git clone <your-repo-url>
cd newsletter
pip install -r backend/requirements.txt
pip install -r scraper_platform/requirements.txt

# Configure
cp backend/.env.example backend/.env
# Edit backend/.env with your PostgreSQL credentials

# Database setup
cd backend
alembic upgrade head
cd ..

# Seed sources and scrape content
python scrapers/run_all.py

# Start server
python start_server.py
```

Open **http://localhost:8000** in your browser.

API docs: **http://localhost:8000/docs**

---

## Scraping Pipeline

Run the full pipeline (seed → scrape RSS → scrape research → process → cache):

```bash
python scrapers/run_all.py
```

Or run individual steps:

```bash
python scrapers/seed_sources.py       # Seed sources from department registry
python scrapers/run_rss.py            # Scrape all RSS feeds (parallel)
python scrapers/run_research.py       # Fetch research papers
python scrapers/refresh_cache.py      # Rebuild feed cache for all departments
```

Root-level wrapper scripts (`run_rss_scrapers.py`, `run_scrapers.py`, etc.) are kept for backward compatibility.

---

## AI Configuration

| Provider | Cost | Speed | Setup |
|----------|------|-------|-------|
| **Pollinations** (default) | Free | Medium | None — works out of the box |
| **Groq** | Free tier | Fast | Add `GROQ_API_KEY` to `.env` |
| **OpenAI** | Paid | Fast | Add `OPENAI_API_KEY` to `.env` |
| **Ollama** | Free | Slow | Install locally |
| **HuggingFace** | Free tier | Medium | Add `HF_API_KEY` to `.env` |

The system auto-selects the best available provider. Pollinations requires no API key.

---

## API Endpoints

### Auth (`/api/v1/auth`)
`POST /register` · `POST /login` · `POST /refresh` · `GET /me` · `PUT /me` · `POST /change-password`

### Feed (`/api/v1/feed`)
`GET /all-sections` · `GET /personalized` · `GET /trending` · `GET /breaking` · `GET /daily-digest` · `GET /search` · `GET /category/{cat}`

### Departments (`/api/v1/departments`)
`GET /` · `GET /{key}`

### AI (`/api/v1/ai`)
`GET /status` · `GET /providers` · `POST /summarize` · `POST /headline`

### Pipeline (`/api/v1/pipeline`)
`POST /run` · `GET /status` · `POST /process`

### Scrapers (`/api/v1/scrapers`)
`GET /status` · `POST /run/{name}` · `POST /run-all` · `POST /process-pending`

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Alembic |
| **Database** | PostgreSQL 15 |
| **Auth** | JWT (python-jose), bcrypt |
| **AI** | Pollinations (free default), Groq, OpenAI, HuggingFace, Ollama |
| **Scrapers** | httpx (async), feedparser, BeautifulSoup |
| **Research APIs** | Semantic Scholar, Crossref, OpenAlex, PubMed |
| **Frontend** | HTML/CSS/JS (no build step) |
| **CI/CD** | GitHub Actions |

---

## License

This project is proprietary. See [LICENSE](LICENSE) for details.
