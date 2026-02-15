# College Newsletter - Frontend

Production-ready single-page frontend for the College Newsletter platform. Pure HTML/CSS/JS — no build step required.

## Quick Start

### Option 1: Direct Open
Double-click `index.html` to open in browser. Requires backend running at `http://localhost:8000`.

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

### 📰 News Feed
- Personalized, trending, breaking, and daily digest feeds
- Category filtering (AI, Tech, Career, Startups, Security, Events)
- Search articles by keyword
- Infinite scroll with "load more" support

### 🔐 Authentication
- User registration and login modals
- JWT token storage with auto-login on refresh
- User profile dropdown with stats (streak, reads)
- Protected features (save/bookmark) require auth

### 📖 Article Reader
- Modal-based article viewer with content blocks (Hook, Why It Matters, Key Points, Action Step)
- Save/bookmark articles
- Share via Web Share API or clipboard
- Link to original source

### 🎨 UI/UX
- 3-column layout: categories sidebar, main feed, trending/stats sidebar
- Dark/light theme toggle with persistence
- Responsive design with mobile bottom navigation
- Toast notifications
- Skeleton loading states
- Attractiveness score badges on cards

---

## Backend Connection

Connects to `http://localhost:8000`. Start the backend first:
```bash
cd D:\newsletter\backend
uvicorn app.main:app --reload
```

### API Endpoints Used
| Endpoint | Purpose |
|---|---|
| `GET /api/v1/feed/personalized` | Main feed |
| `GET /api/v1/feed/trending` | Trending sidebar + feed |
| `GET /api/v1/feed/breaking` | Breaking news |
| `GET /api/v1/feed/daily-digest` | Daily digest |
| `GET /api/v1/feed/search` | Search articles |
| `GET /api/v1/feed/category/{cat}` | Category filter |
| `GET /api/v1/feed/stats` | Feed statistics |
| `GET /api/v1/feed/saved` | Saved articles |
| `POST /api/v1/feed/{id}/save` | Save article |
| `DELETE /api/v1/feed/{id}/save` | Unsave article |
| `POST /api/v1/feed/{id}/read` | Record read |
| `POST /api/v1/auth/login` | Login |
| `POST /api/v1/auth/register` | Register |
| `GET /api/v1/auth/me` | Current user |

---

## Troubleshooting

### "Could not load feed" error
**Fix:** Start the backend server and ensure the database has content.

### CORS errors in console
**Fix:** Backend CORS is configured for localhost and file:// origins. If using a different port, add it to `.env`:
```env
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:5500"]
```

### No articles showing
**Fix:** Run the scrapers to populate content, or check that the database has ProcessedContent entries.

---

## File Structure

```
frontend/
├── index.html      # Production UI (single-page app)
├── reader.html     # Standalone article reader (legacy)
└── README.md       # This file
```
