# Quick Start Guide

## 🚀 Start Everything in 5 Minutes

### Step 1: Start Databases (if not running)
```powershell
# PostgreSQL
net start postgresql-x64-15

# Redis
redis-server --daemonize yes
```

### Step 2: Start Ollama (Local AI)
```powershell
# In first terminal
ollama serve

# In second terminal (test)
ollama run llama3.2 "Hello!"
```

### Step 3: Start Backend
```bash
cd D:\newsletter\backend
uvicorn app.main:app --reload
```

### Step 4: Open Frontend
```bash
cd D:\newsletter\frontend
start index.html
```

---

## 🌐 Access Points

| Service | URL | Status |
|---------|-----|--------|
| Backend API | http://localhost:8000 | Should show docs |
| Health Check | http://localhost:8000/health | Should show "healthy" |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Frontend | Open `index.html` | Test UI |
| PostgreSQL | localhost:5432 | Running |
| Redis | localhost:6379 | Running |
| Ollama | localhost:11434 | For AI features |

---

## 🧪 Test the Application

### 1. Health Check
Open browser: http://localhost:8000/health

Should see:
```json
{"status": "healthy", "version": "1.0.0"}
```

### 2. Register User (via Frontend)
1. Open `frontend/index.html`
2. Fill registration form
3. Click "Register"

### 3. Test AI (via Frontend)
1. Go to "AI Content Processor" section
2. Enter title and content
3. Click "Summarize"
4. Wait 10-30 seconds for response

---

## 📋 Service Status Commands

```powershell
# Check PostgreSQL
python -c "import socket; s=socket.socket(); print('PostgreSQL:', 'Running' if s.connect_ex(('localhost',5432))==0 else 'Stopped'); s.close()"

# Check Redis  
python -c "import socket; s=socket.socket(); print('Redis:', 'Running' if s.connect_ex(('localhost',6379))==0 else 'Stopped'); s.close()"

# Check Ollama
python -c "import socket; s=socket.socket(); print('Ollama:', 'Running' if s.connect_ex(('localhost',11434))==0 else 'Stopped'); s.close()"

# Check Backend
python -c "import httpx; r=httpx.get('http://localhost:8000/health'); print('Backend:', 'Running' if r.status_code==200 else 'Stopped')"
```

---

## ❌ Common Issues

### "Database connection refused"
```powershell
net start postgresql-x64-15
```

### "Redis connection refused"
```powershell
redis-server
```

### "Ollama not running"
```powershell
ollama serve
```

### "Model not found"
```powershell
ollama pull llama3.2
```

---

## 📁 File Structure

```
D:\newsletter\
├── backend\
│   ├── app	est_newsletter.py       # Backend code
│   ├── setup_db.ps1       # DB setup script
│   ├── setup_ollama.ps1   # Ollama setup script
│   └── .env               # Config
├── frontend	est_newsletter.py       # Test UI
│   └── index.html         # Frontend
├── OLLAMA_SETUP.md        # Ollama guide
└── QUICKSTART.md          # This file
```

---

## ✅ Verification Checklist

- [ ] PostgreSQL running on port 5432
- [ ] Redis running on port 6379
- [ ] Ollama running on port 11434
- [ ] Backend running on port 8000
- [ ] Frontend opens in browser
- [ ] Can register new user
- [ ] Can login
- [ ] AI summarization works (may take 30s)

---

## 🆘 Need Help?

1. Check service status with commands above
2. Review setup guides:
   - `OLLAMA_SETUP.md` - AI setup
   - `backend/DATABASE_SETUP.md` - Database setup
3. Check logs in terminal windows

---

**Ready to go!** Start the services and test the application.
