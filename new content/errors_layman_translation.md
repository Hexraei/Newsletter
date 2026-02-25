# NEWS DAY — Critical Errors (Actual) + Layman Meaning

This document is a **plain-English translation** of the production readiness audit you shared.

Source: implementation_plan.md

---

## Legend

- **P0 / Critical** = “One request can break or fully compromise the system.”
- **P1 / High** = “Will cause major outages/data issues or serious security risk under real use.”
- **P2 / Medium/Low** = “Not fatal now, but will bite later.”

---

# 🔴 P0 Security Blockers (Must fix before any launch)

## 1) Mass Assignment → Any user can become admin
**Actual error (what the code does):**  
The API updates user fields by looping over everything the client sends and doing `setattr(user, field, value)` (no whitelist).

**Real exploit example:**  
A normal logged-in user can call the update endpoint with:
```json
{"is_admin": true}
```
…and the system will set them as admin.

**Layman meaning:**  
This is like a website letting you edit your own profile — but accidentally letting you edit “I am the owner” too.  
**Anyone can promote themselves to admin.**

**Impact:**  
Full takeover of admin-only controls and sensitive endpoints.

---

## 2) Unauthenticated “Delete Everything” endpoint (`/dev/refresh`)
**Actual error (what the code does):**  
There is a route `/api/v1/scrapers/dev/refresh` with **no authentication check**.  
Also, the debug flag defaults to “on” if environment config is missing.

**Layman meaning:**  
There’s a public button on your site that says **“wipe all data and reset everything”**, and anyone on the internet can press it.

**Impact:**  
Complete data loss + immediate outage.

---

# 🔴 P0 Reliability Blockers (Will freeze/crash in production)

## 3) DB connection pool hard-blocks (max_overflow=0 + no timeout)
**Actual error:**  
Database engine is configured with `max_overflow=0` and no `pool_timeout`.  
When the pool is full, the next request **waits forever**.

**Layman meaning:**  
You have 20 service counters. If 21 people show up, you don’t make a new counter — you just lock the door and make everyone wait forever.

**Impact:**  
App appears “hung” under moderate load (scrapers + users).

---

## 4) Per-request/per-item creation of heavy clients (httpx, AI provider, image fetcher, model)
**Actual error:**  
Processing creates new HTTP clients / AI provider objects repeatedly (often per request and per content item).

**Layman meaning:**  
Instead of reusing one “internet connection + AI client,” you create a brand-new one again and again.  
That burns system resources fast.

**Impact signals:**  
- “Too many open files”
- Connection errors
- Random failures under load

---

## 5) Breaking news does Python-side sorting of 200 DB rows per request
**Actual error:**  
Endpoint loads ~200 rows and sorts them in Python, repeatedly, for each request.

**Layman meaning:**  
Every time a user opens the homepage, your server pulls a big stack of records and manually re-sorts them — instead of asking the database to return “top 5” directly.

**Impact:**  
Higher CPU + slower homepage as users increase.

---

# 🟡 P1 High-Risk Security & Reliability Issues

## 6) Logout doesn’t revoke tokens
**Actual error:**  
Logout returns success, but issued tokens remain valid until expiry.

**Layman meaning:**  
If someone steals your login token, “logging out” doesn’t kick them out. They still have access until the token expires.

---

## 7) LIKE-based search can be abused to force full scans
**Actual error:**  
User input is used in a LIKE pattern (`%...%`) without escaping wildcard characters.

**Layman meaning:**  
Someone can search in a way that forces your database to scan everything repeatedly.  
Not classic SQL injection, but **easy performance abuse**.

---

## 8) SSRF risk via image URLs from external sources
**Actual error:**  
Image URLs from Openverse/Wikimedia are stored/served without strict validation (scheme, private IPs, etc.).

**Layman meaning:**  
If an upstream source returns a “weird” URL, your system might store it and later request something it shouldn’t (like internal cloud metadata).  
This can leak sensitive infrastructure data.

---

## 9) Content de-dup has a race condition (TOCTOU)
**Actual error:**  
Check-if-exists (SELECT) then insert (INSERT) — two workers can insert the same content simultaneously.

**Layman meaning:**  
Two people check “is this already added?” at the same time, both see “no,” then both add it.  
You get duplicates.

---

## 10) Read counter increment is not atomic
**Actual error:**  
`read_count += 1` in ORM memory instead of `UPDATE read_count = read_count + 1`.

**Layman meaning:**  
If 10 people open an article at the same time, you might record only 1 view instead of 10.  
Stats become wrong.

---

## 11) Celery task swallows errors (no retry, no alert)
**Actual error:**  
Exceptions are caught and returned as a success-like dict. No retry/raise.

**Layman meaning:**  
When processing fails, it quietly says “ok here’s an error string” and keeps going.  
No alarms. No automatic retry. Backlog grows silently.

---

# 🟡 Medium / Hygiene Issues (Not launch blockers, but important)

## 12) No cache TTL / invalidation
**Actual error:**  
Cached feeds can remain stale indefinitely.

**Layman meaning:**  
Users might keep seeing old content because cache never expires properly.

---

## 13) Uses `print()` instead of proper logging
**Actual error:**  
Several places use `print()`.

**Layman meaning:**  
In production, `print()` logs are messy and often disappear.  
You lose visibility when things break.

---

## 14) Secrets stored in plaintext file
**Actual error:**  
Openverse credentials written to `.openverse_creds.json`.

**Layman meaning:**  
It’s like leaving passwords in a text file inside the project folder. Easy to leak.

---

## 15) `/health` doesn’t check DB/Redis
**Actual error:**  
Health endpoint doesn’t validate dependencies.

**Layman meaning:**  
Your system might say “healthy” even when database is down.

---

# ✅ “What to fix first” (practical order)

1. **Block mass assignment** (whitelist allowed fields)
2. **Protect `/dev/refresh`** (admin-only + DEBUG default false)
3. **Fix DB pool** (`max_overflow`, `pool_timeout`)
4. **Reuse http clients / AI provider** (singletons / pooling)
5. **Add DB check to `/health`**
6. **Stop swallowing Celery errors** (retries + alert)
7. **Move breaking-news ranking to SQL**
8. **Atomic counters + dedup via ON CONFLICT**
9. **Image URL validation**
10. **Cache TTL**

---

## Notes
This file intentionally focuses on **“actual errors + what they mean in real life.”**
