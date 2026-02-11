# College Newsletter Backend

FastAPI-based backend for the College Newsletter Platform.

## 🎯 Current Status: Phase 2 Complete

- ✅ Authentication & User Management
- ✅ Multiple AI Providers (Pollinations, Groq, OpenAI, Ollama)
- ✅ Content Summarization & Headline Generation
- ✅ 11 Database Tables with Full Schema
- ✅ JWT Authentication with Refresh Tokens
- ✅ Test Suite & Verification Scripts

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (running)
- Redis (optional for testing)

### 1. Install Dependencies

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configure

Edit `.env`:
```env
# Database (required)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/newsletter

# AI (optional - uses free Pollinations AI by default)
# GROQ_API_KEY=gsk_xxx  # Optional, for faster AI
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Start Server

```bash
uvicorn app.main:app --reload
```

Server: http://localhost:8000  
API Docs: http://localhost:8000/docs

---

## 🤖 AI Configuration

### Option 1: Pollinations AI (DEFAULT) ⭐
**FREE** - No signup, works immediately!

Default option. Just start the backend.

### Option 2: Groq (Fastest Free)
```env
GROQ_API_KEY=gsk_your_key_here
```
Get key: https://console.groq.com/

### Option 3: Ollama (Local)
```env
USE_LOCAL_AI=true
```
Install: https://ollama.com/

### Option 4: OpenAI
```env
OPENAI_API_KEY=sk_your_key_here
```

---

## 📚 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, get tokens |
| GET | `/api/v1/auth/me` | Get current user |
| PUT | `/api/v1/auth/me` | Update profile |
| POST | `/api/v1/auth/change-password` | Change password |
| GET | `/api/v1/auth/stats` | User statistics |

### AI Services
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ai/status` | AI service status |
| GET | `/api/v1/ai/providers` | List AI providers |
| POST | `/api/v1/ai/summarize` | Summarize content |
| POST | `/api/v1/ai/headline` | Generate headline |
| POST | `/api/v1/ai/embed` | Generate embedding |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/` | Root info |

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest tests/ -v

# Auth tests only
pytest tests/test_auth.py -v

# AI diagnostics
python test_ai_system.py

# Check AI provider
python check_ai.py
```

### Verify Setup

```bash
# Phase 1 verification
python verify_phase1.py
```

---

## 🗄️ Database Schema

### Core Tables

```sql
users                    # User accounts
sources                  # Content sources
raw_content             # Scraped data
processed_content       # Curated content
vector_embeddings       # AI embeddings
hookline_queue          # Headline generation
breaking_alerts         # Breaking news
velocity_metrics        # BNDE tracking
user_reads              # Reading history
user_saves              # Bookmarks
user_feedback           # Ratings
```

### Run Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py          # Dependencies (DB, auth)
│   │   └── v1/
│   │       ├── ai.py        # AI endpoints
│   │       └── auth.py      # Auth endpoints
│   ├── core/
│   │   └── security.py      # JWT, password hashing
│   ├── integrations/
│   │   ├── ai_provider.py   # Unified AI provider
│   │   ├── free_ai_service.py  # Free AI (Pollinations)
│   │   ├── groq_service.py  # Groq integration
│   │   ├── huggingface_service.py
│   │   ├── ollama.py        # Local AI
│   │   └── openai_service.py
│   ├── models/
│   │   ├── base.py          # SQLAlchemy base
│   │   ├── content.py       # Content models
│   │   └── user.py          # User models
│   ├── schemas/
│   │   ├── responses.py     # API response wrappers
│   │   └── user.py          # User schemas
│   ├── services/
│   │   └── auth_service.py
│   ├── config.py            # Settings
│   └── main.py              # FastAPI app
├── alembic/                 # Migrations
├── tests/
│   ├── conftest.py
│   └── test_auth.py
├── check_ai.py              # AI status check
├── test_ai_system.py        # AI diagnostics
├── verify_phase1.py         # Phase 1 verification
└── requirements.txt
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection |
| `REDIS_URL` | No | - | Redis connection |
| `SECRET_KEY` | Yes | - | App secret |
| `JWT_SECRET_KEY` | Yes | - | JWT signing |
| `GROQ_API_KEY` | No | - | Groq AI |
| `OPENAI_API_KEY` | No | - | OpenAI |
| `OLLAMA_URL` | No | localhost:11434 | Local AI |

---

## 🐛 Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL
python -c "import socket; s=socket.socket(); print('Running' if s.connect_ex(('localhost',5432))==0 else 'Stopped'); s.close()"

# Start PostgreSQL (Windows)
net start postgresql-x64-15
```

### AI Not Working
```bash
# Check AI status
python test_ai_system.py

# Check available providers
python check_ai.py
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 📊 Cost

| Component | Cost |
|-----------|------|
| PostgreSQL (self-hosted) | $0 |
| Redis (self-hosted) | $0 |
| AI (Pollinations) | $0 |
| **Total** | **$0/month** |

---

## 🛣️ Roadmap

### Phase 3: Content Pipeline (Next)
- [ ] Scraper integration
- [ ] Vectorization service
- [ ] Attractiveness scoring
- [ ] Breaking news detection

### Phase 4: Feed & Delivery
- [ ] Feed generation API
- [ ] Newsletter creation
- [ ] Email delivery

See main README.md for full roadmap.

---

## 📄 License

Proprietary - See LICENSE file
