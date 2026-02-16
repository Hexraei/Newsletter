# College Newsletter Platform

A content aggregation and newsletter platform for college students. Scrapes tech news from 7 sources, processes it with AI, and delivers curated insights in a 2-3 minute read format.

**Stack:** FastAPI + PostgreSQL + Redis + AI (Pollinations/Groq/OpenAI/Ollama)  
**Cost:** $0/month (self-hosted + free AI)

---

## Current Progress

### ✅ Phase 1: Foundation — Complete
- FastAPI backend with async architecture
- PostgreSQL database with 11 tables (SQLAlchemy 2.0 + Alembic migrations)
- Redis integration for caching and task queue
- JWT authentication (access + refresh tokens) with bcrypt password hashing
- User profiles with academic info, preferences, and gamification (streaks, badges)

### ✅ Phase 2: AI Integration — Complete
- 5 AI providers with automatic fallback: Pollinations (free default) → Groq → OpenAI → HuggingFace → Ollama
- Content summarization, headline generation, and text embeddings
- AI status monitoring and provider health checks

### ✅ Phase 3: Content Pipeline — Complete
- **6 of 7 scrapers working:** Hacker News, Reddit, Twitter/X (bird CLI), GitHub Trending, Medium, Product Hunt
- Scraper management API with admin controls (run individual/all, schedule, toggle sources)
- Content processing pipeline: attractiveness scoring, AI summarization, tag generation, dedup
- Feed service: personalized, trending, breaking news, daily digest, search, category filtering
- Full pipeline orchestration (scrape → process → embed → publish)
- Frontend UI: responsive SPA with dark mode, article reader, bookmarks, auth, search

### ⚠️ Partially Done
- **Twitter scraper** — works via bird CLI (requires credentials)
- **YouTube scraper** — stub only, not implemented
- **Celery task queue** — tasks defined, scheduler not running
- **Vector similarity search** — embeddings generated, search not wired up

### ❌ Not Started (Future)
- Email delivery (SendGrid config ready, logic not built)
- Discord webhook notifications
- Admin dashboard UI (API endpoints exist, no web panel)
- React/Vue production frontend (currently pure HTML/CSS/JS)
- Rate limiting enforcement
- Monitoring and observability

---

## Project Structure

```
newsletter/
├── backend/                  # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/           # Routes: auth, ai, feed, pipeline, scrapers
│   │   ├── core/             # Security (JWT, bcrypt)
│   │   ├── models/           # SQLAlchemy models (User, Content, Source, etc.)
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic (auth, feed, pipeline, scraper, content)
│   │   ├── integrations/     # AI providers (Groq, OpenAI, Pollinations, Ollama, HF)
│   │   ├── tasks/            # Celery task definitions
│   │   └── config.py         # App settings
│   ├── alembic/              # Database migrations
│   ├── tests/                # pytest test suite
│   ├── docker-compose.yml    # PostgreSQL + Redis
│   └── requirements.txt
│
├── frontend/                 # Web UI
│   ├── index.html            # Main SPA (feed, auth, search, dark mode)
│   └── reader.html           # Article reader view
│
├── scraper_platform/         # Content scrapers
│   ├── main.py               # Orchestrator (runs all scrapers in parallel)
│   └── src/
│       ├── base_scraper.py   # Async base with retry, dedup, logging
│       ├── excel_tracker.py  # Results tracking
│       └── scrapers/         # 7 scrapers (5 working, 2 stubs)
│
├── docs/                     # Setup guides & reference
│   ├── QUICKSTART.md         # 5-minute setup guide
│   ├── FREE_AI_OPTIONS.md    # Free AI provider comparison
│   ├── GROQ_SETUP.md         # Groq API setup
│   ├── OLLAMA_SETUP.md       # Local AI with Ollama
│   └── OPENAI_SETUP.md       # OpenAI setup
│
├── reports/                  # Architecture & design docs
│   ├── AGENTS.md
│   ├── Master_Scraping_Logic.md
│   └── ...
│
├── context/                  # PRD & design references
└── .github/workflows/ci.yml  # CI: pytest, flake8, black, mypy
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis (optional for dev)

### Setup

```bash
# Clone and install
git clone <your-repo-url>
cd newsletter/backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# Configure
cp .env.example .env         # Edit with your settings or keep defaults

# Database
docker-compose up -d postgres redis   # Option A: Docker
# .\setup_db.ps1                      # Option B: Local PostgreSQL

# Migrate and run
alembic upgrade head
uvicorn app.main:app --reload
```

Backend: `http://localhost:8000` · API docs: `http://localhost:8000/docs`

Open `frontend/index.html` in a browser for the UI.

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for the full walkthrough.

---

## AI Configuration

| Provider | Cost | Speed | Setup |
|----------|------|-------|-------|
| **Pollinations** (default) | Free | Medium | None — works out of the box |
| **Groq** | Free tier | Fast | Add `GROQ_API_KEY` (+ optional `GROQ_MODEL`) to `.env` ([guide](docs/GROQ_SETUP.md)) |
| **OpenAI** | Paid | Fast | Add `OPENAI_API_KEY` to `.env` ([guide](docs/OPENAI_SETUP.md)) |
| **Ollama** | Free | Slow | Install locally ([guide](docs/OLLAMA_SETUP.md)) |
| **HuggingFace** | Free tier | Medium | Add `HF_API_KEY` to `.env` |

The system auto-selects the best available provider.

---

## Twitter/X Scraper Setup (bird CLI)

Twitter scraping uses `bird` CLI and needs your own X auth credentials.

Set one of these credential methods:

```bash
# Method 1: Explicit credentials
set BIRD_AUTH_TOKEN=your_auth_token
set BIRD_CT0=your_ct0_token

# Method 2: bird default env names
set AUTH_TOKEN=your_auth_token
set CT0=your_ct0_token
```

Optional browser profile extraction:

```bash
set BIRD_CHROME_PROFILE=Default
# or
set BIRD_FIREFOX_PROFILE=default-release
```

Then run scraper jobs normally (`run/twitter` or `run-all`).

---

## API Endpoints

### Auth (`/api/v1/auth`)
`POST /register` · `POST /login` · `POST /refresh` · `GET /me` · `PUT /me` · `POST /change-password` · `GET /stats`

### AI (`/api/v1/ai`)
`GET /status` · `GET /providers` · `POST /summarize` · `POST /headline` · `POST /embed`

### Feed (`/api/v1/feed`)
`GET /personalized` · `GET /trending` · `GET /breaking` · `GET /daily-digest` · `GET /search` · `GET /category/{cat}` · `POST /{id}/read` · `POST /{id}/save` · `POST /{id}/feedback` · `GET /stats`

### Pipeline (`/api/v1/pipeline`)
`POST /run` · `GET /status` · `POST /process` · `POST /embed` · `GET /stats`

### Scrapers (`/api/v1/scrapers`) — Admin
`GET /status` · `POST /run/{name}` · `POST /run-all` · `POST /process-pending` · `GET /stats`

---

## Testing

```bash
cd backend

pytest tests/ -v              # Run test suite
python test_ai_system.py      # Diagnose AI providers
python verify_phase1.py       # Verify Phase 1 setup
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery |
| **Database** | PostgreSQL 15, Redis 7 |
| **Auth** | JWT (python-jose), bcrypt |
| **AI** | Pollinations, Groq, OpenAI, HuggingFace, Ollama |
| **Scrapers** | httpx (async), BeautifulSoup, RSS feeds |
| **Frontend** | HTML/CSS/JS (no build step) |
| **CI/CD** | GitHub Actions (pytest, flake8, black, mypy) |
| **Infra** | Docker Compose |

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | 5-minute setup guide |
| [docs/FREE_AI_OPTIONS.md](docs/FREE_AI_OPTIONS.md) | Free AI provider comparison |
| [docs/GROQ_SETUP.md](docs/GROQ_SETUP.md) | Groq setup |
| [docs/OLLAMA_SETUP.md](docs/OLLAMA_SETUP.md) | Local AI with Ollama |
| [docs/OPENAI_SETUP.md](docs/OPENAI_SETUP.md) | OpenAI setup |
| [backend/DATABASE_SETUP.md](backend/DATABASE_SETUP.md) | Database setup details |
| [reports/](reports/) | Architecture & scraping design docs |

---

## License

This project is proprietary. See [LICENSE](LICENSE) for details.
