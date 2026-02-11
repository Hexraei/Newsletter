# College Newsletter Platform

A comprehensive content aggregation and newsletter platform designed for college students. Delivers curated tech news, opportunities, and insights in a 2-3 minute read format.

## 🎯 Project Overview

**Current Status:** Phase 2 Complete (AI Integration)  
**Stack:** FastAPI + PostgreSQL + Redis + Local AI  
**Cost:** $0/month (Self-hosted + Free AI)

### Key Features

- ✅ **Authentication System** - JWT-based auth with user profiles
- ✅ **AI Content Processing** - Automatic summarization and headline generation
- ✅ **Multiple AI Providers** - Pollinations AI (default), Groq, OpenAI, Ollama
- ✅ **Test Frontend** - HTML/JS UI for API testing
- ✅ **Breaking News Detection** - Architecture ready
- ⏳ **Content Pipeline** - Scraper integration (Phase 3)
- ⏳ **Personalized Feed** - Recommendation engine (Phase 3)

---

## 📁 Project Structure

```
newsletter/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/         # API routes (auth, ai)
│   │   ├── core/           # Security, config
│   │   ├── models/         # Database models (11 tables)
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── integrations/   # AI providers
│   ├── alembic/            # Database migrations
│   ├── tests/              # Test suite
│   ├── setup_db.ps1        # Database setup script
│   ├── setup_ollama.ps1    # Ollama setup script
│   ├── requirements.txt
│   └── .env                # Configuration
│
├── frontend/               # Test UI
│   └── index.html          # Complete test interface
│
├── scraper_platform/       # Existing scrapers
│   ├── main.py
│   └── src/
│       ├── base_scraper.py
│       └── scrapers/       # 7 working scrapers
│
├── reports/                # Documentation
│   ├── AGENTS.md
│   ├── Master_Scraping_Logic.md
│   └── ...
│
├── FREE_AI_OPTIONS.md      # Free AI setup guide
├── GROQ_SETUP.md          # Groq setup guide
├── OLLAMA_SETUP.md        # Ollama setup guide
├── QUICKSTART.md          # 5-minute start guide
└── README.md              # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or use SQLite for testing)
- Redis (optional for testing)

### 1. Clone & Setup

```bash
git clone <your-repo-url>
cd newsletter

# Backend setup
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example
cp .env.example .env

# Edit .env with your settings (or keep defaults for free AI)
```

### 3. Setup Database

**Option A: With Docker**
```bash
docker-compose up -d postgres redis
```

**Option B: Local PostgreSQL**
```powershell
# Windows - Run as Admin
.\setup_db.ps1

# Or manually:
# 1. Install PostgreSQL
# 2. Create database: newsletter
# 3. Update DATABASE_URL in .env
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start Backend

```bash
uvicorn app.main:app --reload
```

Backend will be at: `http://localhost:8000`

### 6. Open Frontend

```bash
cd ../frontend
# Simply open in browser
start index.html

# Or use Python server
python -m http.server 3000
```

---

## 🤖 AI Configuration

### Option 1: Pollinations AI (DEFAULT) ⭐
**FREE** - No signup required! Works immediately.

Just start the backend - it's already configured.

### Option 2: Groq (Fastest)
**FREE tier** - 20 requests/minute

1. Sign up: https://console.groq.com/
2. Get API key
3. Add to `.env`:
```env
GROQ_API_KEY=gsk_your_key_here
```

### Option 3: Ollama (Local)
**FREE** - Runs on your machine

```powershell
# Install Ollama
.\setup_ollama.ps1

# Or manually:
# 1. Download from https://ollama.com/
# 2. ollama pull llama3.2
# 3. ollama serve
```

See `OLLAMA_SETUP.md` for details.

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_auth.py -v

# AI system test
python test_ai_system.py
```

### API Testing

Open frontend at `frontend/index.html` and use the built-in API tester, or use curl:

```bash
# Health check
curl http://localhost:8000/health

# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"testpass","full_name":"Test User"}'

# AI Summarize
curl -X POST http://localhost:8000/api/v1/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"AI is transforming education..."}'
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| `QUICKSTART.md` | 5-minute setup guide |
| `FREE_AI_OPTIONS.md` | All free AI options |
| `GROQ_SETUP.md` | Groq setup (fastest free) |
| `OLLAMA_SETUP.md` | Local AI setup |
| `backend/DATABASE_SETUP.md` | Database setup details |
| `backend/README.md` | Backend-specific docs |
| `frontend/README.md` | Frontend test UI docs |
| `reports/` | Architecture & planning docs |

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI (async)
- **Database:** PostgreSQL 15+ (SQLAlchemy 2.0)
- **Cache:** Redis
- **Auth:** JWT (python-jose) + bcrypt
- **AI:** Pollinations AI (default), Groq, OpenAI, Ollama
- **Migrations:** Alembic
- **Testing:** pytest + pytest-asyncio

### Frontend (Test UI)
- Pure HTML/CSS/JS (no build step)
- Responsive design
- Real-time API testing

### Scrapers
- Python async (httpx)
- 7 sources: Hacker News, Reddit, GitHub, Medium, Product Hunt, YouTube, Twitter

---

## 🗺️ Roadmap

### Phase 1: Foundation ✅
- [x] FastAPI project structure
- [x] PostgreSQL + Redis setup
- [x] User authentication (JWT)
- [x] Database models (11 tables)
- [x] Alembic migrations

### Phase 2: AI Integration ✅
- [x] Multiple AI provider support
- [x] Content summarization
- [x] Headline generation
- [x] Free AI options (Pollinations, Groq)
- [x] Test frontend UI

### Phase 3: Content Pipeline ⏳ (Next)
- [ ] Integrate existing scrapers
- [ ] Content vectorization
- [ ] Attractiveness scoring
- [ ] Processing queue
- [ ] Breaking news detection (BNDE)

### Phase 4: Feed & Delivery ⏳
- [ ] Personalized feed generation
- [ ] Newsletter creation
- [ ] Email delivery (SendGrid)
- [ ] Discord notifications

### Phase 5: Production ⏳
- [ ] React/Vue frontend
- [ ] Docker deployment
- [ ] CI/CD pipeline
- [ ] Monitoring

---

## 💰 Cost Breakdown

| Component | Cost | Notes |
|-----------|------|-------|
| **PostgreSQL** | $0 | Self-hosted |
| **Redis** | $0 | Self-hosted |
| **AI (Pollinations)** | $0 | Free, no signup |
| **Backend** | $0 | Self-hosted |
| **Frontend** | $0 | Static HTML |
| **Total** | **$0/month** | Completely free! |

Optional upgrades:
- Groq: FREE tier available
- OpenAI: $5-20/month for heavy use
- Cloud hosting: $5-50/month

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

---

## 📝 License

This project is proprietary. See LICENSE file for details.

---

## 🆘 Support

Having issues?

1. Check `QUICKSTART.md` for common problems
2. Run `python test_ai_system.py` to diagnose AI issues
3. Check `backend/logs/` for error logs
4. Open an issue with error details

---

## 🎉 Acknowledgments

- FastAPI community for the excellent framework
- Pollinations AI for free AI services
- Ollama for local AI capabilities

---

**Ready to start?** See `QUICKSTART.md` for 5-minute setup!
