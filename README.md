# NEWS DAY — College Newsletter Platform

A department-aware news aggregation platform built for engineering college students in India. Pulls live content from 200+ sources — global tech media, Indian news, academic feeds, Reddit communities, and research paper databases — then filters, scores, and surfaces the most relevant stories per department.

**Stack:** FastAPI + PostgreSQL + Vanilla JS  
**Target:** Engineering colleges in Tamil Nadu / South India  
**Cost:** $0/month (self-hosted + free AI)

---

## For Users

### What is NEWS DAY?

NEWS DAY is your department-specific daily briefing. Instead of scrolling through generic tech news, you get a curated feed of what matters most to **your** engineering branch — filtered from 200+ sources, scored by relevance, and updated continuously.

### Departments

| Department | Key | What you get |
|---|---|---|
| Computer Science & Engineering | CSE | Dev tools, algorithms, software engineering, open-source |
| Information Technology | IT | Cloud, networking, cybersecurity, DevOps, SaaS |
| Artificial Intelligence & Data Science | AIDS | ML papers, LLMs, computer vision, data engineering |
| Electronics & Communication Engineering | ECE | Embedded, VLSI, IoT, 5G, signal processing |
| Electrical & Electronics Engineering | EEE | Renewable energy, power electronics, smart grids, EVs |
| Mechanical Engineering | ME | Manufacturing, CAD/CAM, robotics, automotive |
| Civil Engineering | CE | Construction, infrastructure, smart cities, structural |
| Biotechnology Engineering | BT | CRISPR, genomics, biopharma, drug discovery |
| Chemical Engineering | CH | Process engineering, polymers, green chemistry |
| Aeronautical / Aerospace Engineering | AE | ISRO, space missions, UAVs, propulsion, defence |

### Features (User-facing)

- **Breaking News** — Top 3 high-impact stories surfaced from everything scraped that day
- **Trending** — Most engaging stories across your department's sources
- **Research Papers** — 2–3 highly-cited landmark papers at the top, followed by 10–15 additional suggestions on a dedicated research page
- **Department Feed** — Switch departments instantly from the navbar; content filters immediately
- **Stories & Insights** — Browse all recent stories and AI-generated summaries
- **Account** — Sign up with your department, log in to personalise your feed

---

## Sources

NEWS DAY pulls from **200+ sources** across five categories.

### Global RSS — per department

#### Computer Science & Engineering
Hacker News · TechCrunch · Ars Technica · The Verge · InfoQ · Dev.to · ACM TechNews · ArXiv CS · Google AI Blog · Microsoft Research

#### Information Technology
The Register · ZDNet · Bleeping Computer · Krebs on Security · Dark Reading · AWS Blog · Google Cloud Blog · NIST News

#### Artificial Intelligence & Data Science
MIT Technology Review · VentureBeat AI · ArXiv AI · ArXiv ML · ArXiv CV · ArXiv NLP · Google AI Blog · OpenAI Blog · Hugging Face Blog · Papers With Code

#### Electronics & Communication Engineering
IEEE Spectrum · EE Times · Embedded.com · Hackaday · All About Circuits · ArXiv Signal Processing · ArXiv Systems · Analog Devices Blog

#### Electrical & Electronics Engineering
IEEE Spectrum · Renewable Energy World · Utility Dive · ArXiv Systems · IEA News

#### Mechanical Engineering
Engineering.com · Machine Design · Design News · SAE International · New Atlas · 3D Printing Industry · ArXiv Fluid Dynamics

#### Civil Engineering
Construction Dive · The B1M · Smart Cities Dive · ArXiv Geophysics · ASCE News

#### Biotechnology Engineering
GEN News · STAT News · Fierce Biotech · Science Daily Biotech · ArXiv Quantitative Biology · BioPharma Dive · Labiotech.eu

#### Chemical Engineering
C&EN News · The Chemical Engineer · ArXiv Chemical Physics · Hydrocarbon Processing

#### Aeronautical / Aerospace Engineering
SpaceNews · NASA Spaceflight · Ars Technica Science · FlightGlobal · ArXiv Astrophysics · ArXiv Space Physics · NASA Blog · ISRO News · Space.com

---

### India Sources — all departments
These run on top of every department's feed to surface Indian industry news, career signals, and policy updates.

Times of India Tech · TOI Education · The Hindu Sci-Tech · The Hindu Education · NDTV Gadgets · Indian Express Technology · Hindustan Times Tech · Livemint Technology · Economic Times Tech · YourStory · Inc42 · The Wire Science · News18 Tech · Moneycontrol Tech · MediaNama · PIB India · ET Govt

### India Sources — department-specific

| Department | Sources |
|---|---|
| CSE | Trak.in · ET CIO |
| IT | ETTelecom · CIO India · ET HR |
| AI&DS | Analytics Vidhya Blog |
| ECE | Electronics For You |
| EEE | Mercom India Solar · ETEnergyWorld |
| ME | ETAuto · Manufacturing Today India · Autocar India |
| CE | ETInfra · EPC World |
| BT | BioVoice News · Express Pharma · ET Health |
| CH | Chemical Industry Digest · ETEnergyWorld |
| AE | Livefist Defence · Indian Defence Review · Defence Star |

---

### Community Sources (Reddit)

**Department-specific subs** — programming · compsci · Python · javascript · rust · learnprogramming · cscareerquestions · MachineLearning · LocalLLaMA · deeplearning · datascience · ECE · electronics · embedded · FPGA · arduino · electricalengineering · powerelectronics · renewable · MechanicalEngineering · 3Dprinting · CAD · civilengineering · StructuralEngineering · biotech · bioinformatics · genetics · ChemicalEngineering · aerospace · spacex · ISRO · and many more

**India subs (all departments)** — india · Indian_Academia · developersIndia · Btechtards · Indian_Startups · chennai · TamilNadu

### Other General Sources
Hacker News (top posts) · GitHub Trending (language-filtered) · Medium (publication-filtered) · Product Hunt (daily launches)

---

### Research Paper APIs
All free, no API key required.

| API | What it provides |
|---|---|
| **Semantic Scholar** | 200M+ papers, citation counts, abstracts |
| **Crossref** | DOI-linked published papers, journal metadata |
| **OpenAlex** | Open access papers with full bibliographic data |
| **PubMed** | Biomedical and life sciences literature |

Papers are queried with department-specific terms (e.g. "CRISPR gene editing" for BT, "VLSI design" for ECE) and scored by recency and citation count.

---

## For Developers

### Architecture

```
Browser → FastAPI (port 8000) → PostgreSQL
                ↓
         /api/v1/feed/all-sections
                ↓
         cached_feeds table (JSONB)  ← refresh_cache.py
         (4ms response)               (run after each scrape)
                ↓ (cache miss only)
         feed_service.py → ProcessedContent table
```

Content flows through three stages:

1. **Raw** — `raw_content` table; deduped by URL hash
2. **Processed** — `processed_content` table; AI-scored attractiveness (0–100), AI-generated headline + summary, department tags applied
3. **Cached** — `cached_feeds` table; one JSONB row per department, pre-computed for instant API responses

### Attractiveness Scoring

```
base 20
+ engagement signals (0–30)   ← share count, comment count
+ freshness (0–15)             ← exponential decay from publish time
+ content length (0–10)        ← richer article = higher score
+ source type bonus (0–10)     ← academic +8, industry +6, news +4
+ india type bonus (0–8)       ← india-career +8, india-education +7, india-tech +7
```

Breaking news threshold: score ≥ 55 (fillers ≥ 35).  
AI processing (Pollinations): triggered when score ≥ 60.

### Setup

```bash
# Clone and install
git clone <your-repo-url>
cd newsletter
pip install -r backend/requirements.txt
pip install -r scraper_platform/requirements.txt

# Configure environment
cp backend/.env.example backend/.env
# Set DATABASE_URL to your PostgreSQL instance

# Run database migrations
cd backend && alembic upgrade head && cd ..

# Seed all sources + run full pipeline
python scrapers/run_all.py

# Start server
python start_server.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Scraping Pipeline

```bash
python scrapers/run_all.py         # Full pipeline (recommended)
python scrapers/seed_sources.py    # Re-seed sources after department changes
python scrapers/run_rss.py         # RSS only (parallel, semaphore=5)
python scrapers/run_research.py    # Research papers only
python scrapers/run_general.py     # HN, Reddit, GitHub, Medium, ProductHunt
python scrapers/refresh_cache.py   # Rebuild cached_feeds (run after any scrape)
```

### AI Provider Configuration

| Provider | Setup |
|---|---|
| **Pollinations** (default) | None — zero config, free, no key |
| **Groq** | `GROQ_API_KEY=...` in `backend/.env` (free tier: 1M tokens/day) |
| **OpenAI** | `OPENAI_API_KEY=...` in `backend/.env` |
| **Ollama** | `USE_LOCAL_AI=true`, `OLLAMA_URL=http://localhost:11434` |
| **HuggingFace** | `HUGGINGFACE_API_KEY=...` in `backend/.env` |

The system auto-selects the best available provider at runtime with automatic fallback.

### API Reference

**Auth** (`/api/v1/auth`)  
`POST /register` · `POST /login` · `POST /refresh` · `GET /me` · `PUT /me` · `POST /change-password`

**Feed** (`/api/v1/feed`)  
`GET /all-sections` — main feed endpoint (cache-first, returns breaking + trending + research per dept)  
`GET /personalized` · `GET /trending` · `GET /breaking` · `GET /daily-digest` · `GET /search` · `GET /category/{cat}`

**Departments** (`/api/v1/departments`)  
`GET /` · `GET /{key}`

**AI** (`/api/v1/ai`)  
`GET /status` · `GET /providers` · `POST /summarize` · `POST /headline`

**Pipeline** (`/api/v1/pipeline`)  
`POST /run` · `GET /status` · `POST /process`

**Scrapers** (`/api/v1/scrapers`)  
`GET /status` · `POST /run/{name}` · `POST /run-all` · `POST /process-pending`

### Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Database | PostgreSQL 15 |
| Auth | JWT (python-jose), bcrypt |
| AI | Pollinations · Groq · OpenAI · HuggingFace · Ollama |
| Scraping | httpx (async), feedparser, BeautifulSoup, aiohttp |
| Research | Semantic Scholar API · Crossref API · OpenAlex API · PubMed API |
| Frontend | HTML/CSS/JS (no build step) |
| CI | GitHub Actions |

### Key Files

| File | Purpose |
|---|---|
| `backend/app/departments.py` | Single source of truth for all departments and their source URLs |
| `backend/app/services/content_processor.py` | Attractiveness scoring, AI summarisation, tag assignment |
| `backend/app/services/feed_service.py` | Department-filtered feed queries, breaking/trending logic |
| `backend/app/api/v1/feed.py` | `/all-sections` endpoint — cache-first with research_papers |
| `scrapers/run_rss.py` | Parallel RSS scraper with `asyncio.gather` + `Semaphore(5)` |
| `scrapers/run_research.py` | Research paper fetcher (4 APIs, dept-specific queries) |
| `scrapers/refresh_cache.py` | Writes one JSONB row per department to `cached_feeds` |
| `scraper_platform/src/scrapers/rss_scraper.py` | RSS/Atom parser with IST timezone handling |

### Adding a New Source

1. Open `backend/app/departments.py`
2. Add an entry to `INDIA_COMMON_RSS`, `INDIA_DEPT_RSS[<DEPT>]`, or the `"rss"` list inside `DEPARTMENT_SOURCES[<DEPT>]`
3. Run `python scrapers/seed_sources.py` (safe to re-run, deduplicates by URL)
4. Run `python scrapers/run_rss.py` to scrape it
5. Run `python scrapers/refresh_cache.py` to update the cache

### Adding a New Department

1. Add a new entry to the `DEPARTMENTS` list in `backend/app/departments.py`
2. Add its sources to `DEPARTMENT_SOURCES`
3. Add dept-specific Indian sources to `INDIA_DEPT_RSS`
4. Add dept-specific research queries to `DEPT_QUERIES` in `scrapers/run_research.py`
5. Run the full pipeline: `python scrapers/run_all.py`

---

## License

This project is proprietary. See [LICENSE](LICENSE) for details.
