# Supabase Lite Feed Setup

This project supports a lightweight Supabase integration for feed input + ranked section cache.

## 1) Environment Variables (Backend)

Add these to `backend/.env` (do not commit this file):

```env
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>

SUPABASE_SCRAPED_TABLE=scraped_items
SUPABASE_RANKED_CACHE_TABLE=ranked_sections_cache
SUPABASE_CACHE_KEY=lite-all-sections
SUPABASE_CACHE_TTL_MINUTES=15
SUPABASE_FETCH_LIMIT=400
```

Notes:
- Keep `SUPABASE_SERVICE_ROLE_KEY` backend-only.
- Never expose service keys in frontend code.
- If Supabase is unreachable, backend automatically falls back to local scraped JSON.

## 2) Default Table Schema

Run SQL from `backend/supabase_lite_schema.sql` in Supabase SQL Editor.

## 3) Runtime Behavior

- `GET /api/v1/feed/*` endpoints try Supabase table `scraped_items` first.
- On miss/failure, they fallback to `scraper_platform/data/scraped_*.json`.
- `GET /api/v1/feed/all-sections` attempts cached ranked payload from `ranked_sections_cache`.
- If cache is stale or missing, backend ranks fresh and writes a new cache row.

## 4) Security Checklist

- Rotate keys immediately if leaked.
- Use `anon` key only for public read scenarios.
- Use `service_role` only on trusted backend.
- Add table RLS policies appropriate to your production posture.
