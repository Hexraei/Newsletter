# NEWS DAY Deployment Handoff (Render + Neon)

This guide is split into two parts:

- **Part A — Copilot/local prep (done or repo-based)**
- **Part B — Your cloud-console steps (Neon + Render + GitHub)**

---

## Part A — Copilot/local prep

Completed in repo:

- `render.yaml` updated with production-safe defaults:
  - `ENVIRONMENT=production`
  - `COOKIE_SECURE=true`
  - `COOKIE_SAMESITE=lax`
  - `LOG_FORMAT=json`
  - optional `UNSPLASH_ACCESS_KEY` env key included
- `backend/.env.example` updated with:
  - `COOKIE_SAMESITE`
  - strict supplement/diversity controls:
    - `RELEVANCE_STRICT_SUPPLEMENT_ENABLED`
    - `RELEVANCE_STRICT_SUPPLEMENT_MAX_ITEMS`
    - `RELEVANCE_STRICT_SUPPLEMENT_MIN_ATTRACTIVENESS`
    - `RELEVANCE_SOURCE_DIVERSITY_CAP`

What this means:

- Your Render Blueprint deploy has safer production defaults.
- Env examples now match current code/config expectations.

---

## Part B — Your steps in cloud consoles

## 1) Neon setup (database)

1. Create Neon project in nearest region (recommended: Singapore for India users).
2. Create a production database/branch.
3. Copy both connection strings:
   - **Pooled URL** (for Render app runtime)
   - **Direct URL** (for migrations and GitHub scraper workflow)
4. Ensure both URLs include `sslmode=require`.

Example format:

```text
postgresql+asyncpg://USER:PASSWORD@HOST/DB?sslmode=require
```

## 2) Render backend deploy

1. Render -> New -> Blueprint -> select this repo.
2. Confirm service from `render.yaml` (`newsday-backend`).
3. In Render service settings, set **Python Version = 3.11.0** explicitly.
   - This avoids Python 3.14 builds, which can fail on `pydantic-core` metadata/wheel resolution.
4. Set environment variables in Render:
   - Required:
     - `DATABASE_URL` = **Neon pooled URL**
     - `SECRET_KEY` (strong random)
     - `JWT_SECRET_KEY` (strong random)
     - `CORS_ORIGINS` = JSON array string, e.g. `["https://your-frontend-domain.com"]`
   - Recommended:
     - `UNSPLASH_ACCESS_KEY`
     - `GROQ_API_KEY` (or your preferred AI provider key)
   - Optional:
     - `COOKIE_DOMAIN` if using custom apex/subdomain cookie sharing
5. Deploy service.

## 3) Run migrations (one-time)

Use **Neon direct URL** for migration command:

```bash
cd backend
alembic upgrade head
```

If running from local shell, set `DATABASE_URL` to Neon direct URL for that command.

## 4) Seed + bootstrap content

Run once against production DB:

```bash
python scrapers/seed_sources.py
python scrapers/run_general.py --mode india_strict --include-global-fallback --process-limit 1200
python scrapers/refresh_cache.py
```

Repeat one more cycle if department counts are sparse.

## 5) GitHub Actions secrets (for ongoing scrapes)

Repo -> Settings -> Secrets and variables -> Actions. Add:

- `DATABASE_URL` = **Neon direct URL**
- `UNSPLASH_ACCESS_KEY`
- `GROQ_API_KEY` (if used)

Then run workflow manually once:

- Actions -> `Run Scrapers` -> Run workflow

---

## Post-deploy verification checklist

Backend:

- `GET /health` returns healthy
- `GET /api/v1/feed/all-sections?department=CSE` returns sections
- signup/login works
- department switch returns different department content

Data quality:

- no empty core sections (`breaking`, `trending`, `department`) for most departments
- low duplicate rate in cached sections

Security/cookies:

- auth cookies set over HTTPS
- CORS blocks unknown origins

---

## Production guardrails

- Keep `ENVIRONMENT=production`, `DEBUG=false`.
- Rotate `SECRET_KEY` and `JWT_SECRET_KEY` only with planned re-login window.
- Keep DB backups/snapshots enabled in Neon.
- Monitor:
  - Render logs for 5xx spikes
  - GitHub Actions failures
  - Neon compute/storage limits

