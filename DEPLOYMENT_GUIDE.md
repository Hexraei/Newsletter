# NEWS DAY — Deployment Guide

This guide covers deploying NEWS DAY to production using **Neon** (database), **Render** (backend), **Netlify** (frontend), and **GitHub Actions** (scrapers).

---

## What YOU Need to Do (Manual Steps)

### Step 1: Neon — Create Database

1. Go to [neon.tech](https://neon.tech) and sign in (free, no credit card)
2. Click **New Project** → choose a name (e.g. `newsday`) → select region **Singapore `ap-southeast-1`** (closest to India)
3. Wait ~10 seconds for provisioning
4. Go to **Dashboard → Connection Details** and copy TWO connection strings:
   - **Direct** (for migrations & scrapers)
   - **Pooled** (for the backend app at runtime — uses built-in PgBouncer)

Your URLs will look like:
```
# Direct (for migrations & scrapers — use this with alembic)
postgresql+asyncpg://user:pass@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require

# Pooled (for backend app — use this in Render env vars)
postgresql+asyncpg://user:pass@ep-xxx-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

> ✅ Neon never pauses your project. The compute auto-suspends after 5 min idle but **wakes in <500ms** on the next query — transparent to the application.
> ✅ Free tier: 512MB storage (~3+ years of this app's growth at current scraper rate).

### Step 2: Run Database Migrations (from your local machine)

```bash
# Set your Neon DIRECT connection URL
cd backend
set DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require

# Run migrations (creates all tables)
alembic upgrade head
```

Skills data auto-seeds on first API request — no manual step needed.
Article data is populated automatically by the GitHub Actions scrapers (Step 6).

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
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@ep-xxx-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require` (use **pooled** URL) |
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
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require` (use **direct** URL, not pooled) |
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
| **Neon** | 512MB storage, 1 project, free forever — never pauses |
| **Render** | 750 hours/month free (enough for 1 service), spins down after 15 min idle |
| **Netlify** | 100GB bandwidth/month, unlimited deploys |
| **GitHub Actions** | 2,000 minutes/month |
| **Total** | **$0/month** for typical college project traffic |

> ⚠️ Render free tier spins down after 15 min of inactivity. First request after sleep takes ~30s to wake up. Use [UptimeRobot](https://uptimerobot.com) to ping `/health` every 14 min to keep it alive.

---

## Troubleshooting

### "SSL connection required" errors
Ensure `?sslmode=require` is appended to your DATABASE_URL (Neon uses `sslmode=require`, not `ssl=require`).

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
