# NEWS DAY — Deployment Guide

This guide covers deploying NEWS DAY to production using **Supabase** (database), **Render** (backend), **Netlify** (frontend), and **GitHub Actions** (scrapers).

---

## What YOU Need to Do (Manual Steps)

### Step 1: Supabase Cloud — Create Database

1. Go to [supabase.com](https://supabase.com) and sign in / create account
2. Click **New Project** → choose a name (e.g. `newsday`) and region (**Mumbai `ap-south-1`** recommended)
3. Set a **strong database password** — save it somewhere safe
4. Wait for the project to provision (~2 minutes)
5. Go to **Project Settings → Database → Connection string → URI**
6. Copy TWO connection strings:
   - **Direct connection** (port `5432`) — used for migrations
   - **Transaction pooler** (port `6543`) — used by the app at runtime

Your URLs will look like:
```
# Direct (for migrations & scrapers)
postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres

# Pooler (for backend app)
postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

### Step 2: Run Database Migrations (from your local machine)

```bash
# Set your Supabase DIRECT connection URL (port 5432)
# Convert to asyncpg format by changing postgresql:// to postgresql+asyncpg://
# and appending ?ssl=require

cd backend
set DATABASE_URL=postgresql+asyncpg://postgres.[REF]:[PW]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?ssl=require

# Run migrations
alembic upgrade head

# Seed department sources
cd ..
python seed_department_sources.py
```

Skills data auto-seeds on first API request — no manual step needed.

### Step 3: Render — Deploy Backend

1. Go to [render.com](https://render.com) and sign in with GitHub
2. Click **New → Web Service** → select your `newsletter` repo
3. Render auto-detects Python. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
4. Go to **Environment** tab and add:

| Variable | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres.[REF]:[PW]@...pooler.supabase.com:6543/postgres?ssl=require` |
| `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `JWT_SECRET_KEY` | Generate another: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `CORS_ORIGINS` | `https://YOUR-SITE.netlify.app` (update after Netlify deploy) |
| `DEBUG` | `false` |
| `GROQ_API_KEY` | Your Groq API key |

5. Click **Create Web Service** — Render gives you a URL like `https://newsday-backend.onrender.com`
6. Test it: visit `https://YOUR-URL.onrender.com/health` — should return `{"status": "healthy"}`
7. Test API: visit `https://YOUR-URL.onrender.com/api/v1/skills/CSE`

> ⚠️ Render free tier spins down after 15 min of inactivity. First request after sleep takes ~30s to wake up.
> Alternatively, use the included `render.yaml` — click **New → Blueprint** in Render dashboard for one-click deploy.

### Step 4: Netlify — Deploy Frontend

1. Go to [netlify.com](https://netlify.com) and sign in with GitHub
2. Click **Add new site → Import an existing project** → select your `newsletter` repo
3. Configure build settings:
   - **Base directory:** `frontend`
   - **Build command:** *(leave empty)*
   - **Publish directory:** `frontend`
4. Click **Deploy site**
5. After deploy, go to **Site settings → Domain management** to set up a custom domain (optional)
6. Your site URL will be like `https://YOUR-SITE.netlify.app`

### Step 5: Update CORS on Render

Now that you have the Netlify URL, go back to Render → your service → **Environment** and update:
```
CORS_ORIGINS=https://YOUR-SITE.netlify.app
```

### Step 6: GitHub Actions — Add Secrets for Scrapers

1. Go to your GitHub repo → **Settings → Secrets and variables → Actions**
2. Add these **Repository secrets**:

| Secret Name | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres.[REF]:[PW]@...pooler.supabase.com:5432/postgres?ssl=require` (direct, port 5432) |
| `GROQ_API_KEY` | Your Groq API key |

3. Go to **Actions** tab → you should see the "Run Scrapers" workflow
4. Click **Run workflow** to trigger it manually the first time
5. After that, it runs automatically on schedule (every 6 hours for RSS/general, daily for research)

### Step 7: Verify Everything Works

- [ ] `https://YOUR-RENDER-URL/health` returns `{"status": "healthy"}`
- [ ] `https://YOUR-RENDER-URL/api/v1/skills/CSE` returns skill data
- [ ] `https://YOUR-NETLIFY-URL` loads the homepage
- [ ] Clicking "Skills" in navbar loads the skills page with data
- [ ] GitHub Actions scraper workflow runs successfully

---

## Cost Summary

| Service | Free Tier Limits |
|---|---|
| **Supabase** | 500MB database, 2 projects, unlimited API requests |
| **Render** | 750 hours/month free (enough for 1 service), spins down after 15 min idle |
| **Netlify** | 100GB bandwidth/month, unlimited deploys |
| **GitHub Actions** | 2,000 minutes/month |
| **Total** | **$0/month** for typical college project traffic |

> ⚠️ Render free tier spins down after 15 min of inactivity. First request after sleep takes ~30s to wake up. Use [UptimeRobot](https://uptimerobot.com) to ping `/health` every 14 min to keep it alive.

---

## Troubleshooting

### "SSL connection required" errors
Ensure `?ssl=require` is appended to your DATABASE_URL.

### CORS errors in browser console
Update `CORS_ORIGINS` on Render to match your exact Netlify URL (including `https://`).

### Scrapers fail in GitHub Actions
- Check the Actions logs for the specific error
- Ensure `DATABASE_URL` secret uses the **direct** connection (port `5432`), not the pooler
- `sentence-transformers` is large (~500MB) — the first run may be slow due to pip install

### Render deploy fails
- Check build logs — ensure `requirements.txt` is being picked up from the root
- If the build times out due to `sentence-transformers`, Render free tier has a 15-min build limit

### Alembic migration fails
- Make sure you're in the `backend/` directory when running `alembic upgrade head`
- Ensure `DATABASE_URL` env var is set before running
