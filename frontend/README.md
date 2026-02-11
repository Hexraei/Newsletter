# College Newsletter - Frontend Test UI

A simple HTML/JS frontend for testing the backend API.

## Quick Start

### Option 1: Direct Open
Simply double-click `index.html` to open in browser.

### Option 2: VS Code Live Server
1. Install "Live Server" extension in VS Code
2. Right-click `index.html` → "Open with Live Server"
3. Opens at `http://127.0.0.1:5500`

### Option 3: Python HTTP Server
```bash
cd D:\newsletter\frontend
python -m http.server 3000
```
Then open http://localhost:3000

---

## Features

### 🔐 Authentication
- User Registration
- User Login
- JWT Token storage
- Auto-login on refresh

### 🧪 API Tester
- Test any endpoint
- Custom HTTP methods
- Request body editor
- Response viewer

### 🤖 AI Content Processor
- Summarize news articles
- Generate catchy headlines
- Uses local Ollama AI

### 📰 News Feed Preview
- Sample news cards
- Breaking news tags
- Category tags

---

## Backend Connection

The frontend connects to:
```
http://localhost:8000
```

Make sure backend is running before testing!

---

## Testing Checklist

### Phase 1: Basic Auth
- [ ] Register a new user
- [ ] Login with credentials
- [ ] View user profile
- [ ] Check auth token stored

### Phase 2: API Testing
- [ ] Test GET /health
- [ ] Test GET /api/v1/auth/me
- [ ] Test other endpoints

### Phase 3: AI Features (requires Ollama)
- [ ] Check AI status shows "ready"
- [ ] Summarize content
- [ ] Generate headline
- [ ] View formatted output

---

## Troubleshooting

### "API Offline" in status bar
**Fix:** Start backend server
```bash
cd D:\newsletter\backend
uvicorn app.main:app --reload
```

### "CORS error" in console
**Fix:** Backend CORS already configured. If using Live Server on different port, add it to `.env`:
```env
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:5500"]
```

### AI features not working
**Fix:** Start Ollama
```powershell
ollama serve
# In another terminal:
ollama run llama3.2
```

---

## File Structure

```
frontend/
├── index.html      # Main UI
└── README.md       # This file
```

---

## Notes

- This is a **test UI** for development
- Not optimized for production
- No build step required
- Pure HTML/CSS/JS

For production frontend, consider:
- React/Vue/Angular
- TypeScript
- Tailwind CSS
- Vite/Next.js
