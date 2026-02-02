# 🏗️ Ultimate Free Scraping Architecture

> **Last Updated**: February 2026  
> **Purpose**: 24/7 scraping infrastructure for 750+ sources at $0/month  
> **Philosophy**: Combine the best components from multiple approaches into one unified, scalable system

---

## Executive Summary

This architecture combines the **best elements** from multiple proven approaches:

| Component | Source of Inspiration | Why It Won |
|-----------|----------------------|------------|
| **Coolify** | Old Context | Self-hosted PaaS with Git deployment, easier than raw Docker Compose |
| **Single Instance** | My Previous | 4-core/24GB unified is simpler than 4x distributed VMs |
| **Ofelia** | Old Context | Purpose-built Docker cron scheduler, cleaner than custom code |
| **Crawlee** | My Previous | Modern scraping engine with built-in anti-detection |
| **Oracle Autonomous DB** | Old Context | Managed PostgreSQL, free forever, zero maintenance |
| **BullMQ + Redis** | Both | Simpler than RabbitMQ, sufficient for 750 sources |
| **Scrapoxy** | My Previous | Advanced proxy rotation vs basic Webshare |

**Result**: A professional-grade, 24/7 scraping platform that costs **$0/month** and can scale to 2000+ sources.

---

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ORACLE CLOUD INFRASTRUCTURE                              │
│                         (Always Free Tier)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    VM.Standard.A1.Flex                              │   │
│  │                     4 OCPU + 24 GB RAM                              │   │
│  │                      200 GB NVMe SSD                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         COOLIFY (PaaS)                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │  Crawlee    │  │   Ofelia    │  │   Scrapoxy  │  │  Uptime     │ │   │
│  │  │  Workers    │  │  Scheduler  │  │   Proxy     │  │   Kuma      │ │   │
│  │  │  (Docker)   │  │   (Cron)    │  │   Rotator   │  │  (Monitor)  │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  │  ┌─────────────┐  ┌─────────────┐                                    │   │
│  │  │   KeyDB     │  │  PostgreSQL │                                    │   │
│  │  │  (Redis)    │  │   (Queue)   │                                    │   │
│  │  └─────────────┘  └─────────────┘                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              ORACLE AUTONOMOUS DATABASE (Always Free)               │   │
│  │                    2 × 20GB PostgreSQL Databases                    │   │
│  │  ┌─────────────────────┐      ┌─────────────────────┐               │   │
│  │  │   scraper_queue_db  │      │   scraped_data_db   │               │   │
│  │  │  - job metadata     │      │  - raw_content      │               │   │
│  │  │  - schedules        │      │  - processed_content│               │   │
│  │  │  - logs             │      │  - deduplication    │               │   │
│  │  └─────────────────────┘      └─────────────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES (Free)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Webshare   │  │   Proxifly   │  │   ScraperAPI │  │    Nitter    │    │
│  │   (10 free   │  │  (Free proxy │  │ (1000 req/mo│  │  (Twitter    │    │
│  │   proxies)   │  │     list)    │  │     free)    │  │     RSS)     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Component Breakdown

### 1. 🖥️ Compute Layer: Oracle Cloud (Always Free)

**Why Oracle Cloud?**
- ✅ Truly always free (no 12-month limit)
- ✅ 4 ARM cores + 24GB RAM is unmatched
- ✅ 10TB outbound bandwidth/month
- ✅ 2 free managed PostgreSQL databases
- ✅ Never sleeps (unlike Render/Railway free tiers)

**Instance Configuration:**
```yaml
Name: scraper-master
Shape: VM.Standard.A1.Flex (ARM-based Ampere)
OCPUs: 4
Memory: 24 GB
Boot Volume: 200 GB NVMe SSD
OS: Canonical Ubuntu 22.04 (aarch64)
```

**Network Configuration:**
```
Required Open Ports:
- 22      → SSH
- 80/443  → HTTP/HTTPS (Coolify)
- 3001    → Uptime Kuma
- 5678    → n8n (optional)
- 8888    → Scrapoxy proxy endpoint
- 8890    → Scrapoxy dashboard
```

---

### 2. 🎛️ Orchestration Layer: Coolify

**What is Coolify?**
Open-source, self-hosted Platform-as-a-Service (PaaS) that runs on your server. Think of it as your own private Heroku/Render.

**Why Coolify over raw Docker Compose?**
| Feature | Docker Compose | Coolify |
|---------|---------------|---------|
| Git-based deployment | ❌ Manual | ✅ Auto-deploy on push |
| Web UI management | ❌ CLI only | ✅ Full dashboard |
| Secret management | ❌ .env files | ✅ Built-in UI |
| Database provisioning | ❌ Manual | ✅ One-click |
| SSL certificates | ❌ Manual | ✅ Auto Let's Encrypt |
| Multi-server support | ❌ | ✅ Scale to multiple VMs |

**Installation:**
```bash
# SSH into your Oracle instance
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash

# Access at: http://YOUR_IP:8000
# Complete setup wizard
```

**Services Managed by Coolify:**
- PostgreSQL (for BullMQ job metadata)
- KeyDB (Redis fork - job queues)
- Crawlee scraper workers (Docker)
- Ofelia (cron scheduler)
- Scrapoxy (proxy rotator)
- Uptime Kuma (monitoring)
- n8n (optional workflow editor)

---

### 3. ⏰ Scheduling: Ofelia (Docker Job Scheduler)

**Why Ofelia?**
- Purpose-built for Docker container cron jobs
- Native integration with Coolify
- No custom scheduler code needed
- Supports `@every` syntax (e.g., `@every 15m`)

**Configuration (Docker Compose labels):**
```yaml
services:
  twitter-scraper:
    image: crawlee-worker:latest
    labels:
      # Every 15 minutes - high priority
      ofelia.enabled: "true"
      ofelia.job-run.twitter.schedule: "@every 15m"
      ofelia.job-run.twitter.command: "npm run scrape:twitter"
      
      # Every 6 hours - low priority
      ofelia.job-run.twitter-batch.schedule: "0 */6 * * *"
      ofelia.job-run.twitter-batch.command: "npm run scrape:twitter:batch"

  hackernews-scraper:
    labels:
      ofelia.enabled: "true"
      ofelia.job-run.hackernews.schedule: "@every 15m"
      ofelia.job-run.hackernews.command: "npm run scrape:hackernews"

  reddit-scraper:
    labels:
      ofelia.enabled: "true"
      ofelia.job-run.reddit.schedule: "@every 30m"
      ofelia.job-run.reddit.command: "npm run scrape:reddit"
```

**Schedule Matrix for 750 Sources:**
| Frequency | Sources | Examples |
|-----------|---------|----------|
| 15 min | 50 (Critical) | Hacker News, breaking news RSS |
| 30 min | 200 (Breaking) | Twitter Tier 1, GitHub trending |
| 6 hours | 300 (Standard) | YouTube, Medium publications |
| 24 hours | 200 (Batch) | Full article extraction, archives |

---

### 4. 🤖 Scraping Engine: Crawlee

**Why Crawlee?**
- Modern TypeScript/Python library from Apify
- Built-in anti-detection (human-like fingerprints)
- Automatic proxy rotation and session management
- Handles both HTTP and headless browser scraping
- Built-in retries, error handling, rate limiting

**Worker Architecture:**
```typescript
// src/worker.ts
import { PlaywrightCrawler, Dataset } from 'crawlee';
import { Queue, Worker } from 'bullmq';
import { Redis } from 'ioredis';

const redis = new Redis({ 
  host: process.env.REDIS_HOST,
  port: 6379,
  maxRetriesPerRequest: null
});

// Job queue
const scrapeQueue = new Queue('scraping', { connection: redis });

// Worker processes jobs from queue
const worker = new Worker('scraping', async (job) => {
  const { sourceId, url, selectors, sourceType } = job.data;
  
  const crawler = new PlaywrightCrawler({
    proxyConfiguration: {
      proxyUrls: [process.env.PROXY_URL], // Scrapoxy endpoint
    },
    launchContext: {
      launchOptions: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
      },
    },
    maxRequestsPerMinute: getRateLimit(sourceType),
    requestHandler: async ({ page, request, log }) => {
      log.info(`Scraping ${sourceId}: ${request.url}`);
      
      // Extract content based on selectors
      const data = await page.evaluate((sel) => ({
        title: document.title,
        content: document.querySelector(sel.content)?.innerText,
        author: document.querySelector(sel.author)?.innerText,
        date: document.querySelector(sel.date)?.innerText,
        links: Array.from(document.querySelectorAll('a')).map(a => a.href),
      }), selectors);
      
      // Generate content hash for deduplication
      const contentHash = generateHash(data.content);
      
      // Save to Oracle Autonomous DB
      await saveToDatabase({
        source_id: sourceId,
        url: request.url,
        title: data.title,
        content: data.content,
        author: data.author,
        published_at: parseDate(data.date),
        scraped_at: new Date(),
        content_hash: contentHash,
        metadata: JSON.stringify({
          links: data.links,
          selector_version: selectors.version,
        }),
      });
      
      log.info(`✓ Saved: ${data.title?.substring(0, 50)}...`);
    },
    failedRequestHandler: async ({ request, log }) => {
      log.error(`✗ Failed ${request.url}: ${request.errorMessages}`);
      // BullMQ will auto-retry based on job options
    },
  });
  
  await crawler.run([url]);
  
}, { 
  connection: redis,
  concurrency: 4, // 4 concurrent pages per worker
  limiter: {
    max: 20, // 20 jobs per minute
    duration: 60000,
  }
});

// Rate limits by source type
function getRateLimit(sourceType: string): number {
  const limits: Record<string, number> = {
    'rss': 60,        // RSS feeds - generous
    'twitter': 10,    // Twitter - strict
    'linkedin': 5,    // LinkedIn - very strict
    'instagram': 5,   // Instagram - very strict
    'github': 30,     // GitHub - reasonable
    'reddit': 20,     // Reddit - moderate
    'youtube': 15,    // YouTube - moderate
    'default': 20,
  };
  return limits[sourceType] || limits.default;
}
```

---

### 5. 🔄 Proxy Rotation: Scrapoxy

**Why Scrapoxy?**
- Acts as single proxy endpoint for all scrapers
- Automatically rotates between multiple proxy sources
- Removes dead proxies automatically
- Sticky sessions for login flows
- Dashboard for monitoring proxy health

**Architecture:**
```
Crawlee Worker → Scrapoxy (localhost:8888) → [Rotates between]
                                                    │
    ┌───────────────┬───────────────┬───────────────┼───────────────┐
    │               │               │               │               │
    ▼               ▼               ▼               ▼               ▼
 Webshare.io    Proxifly Free   ScraperAPI      Nitter RSS    (More...)
 (10 proxies)   (3500+ proxies)  (1000 req/mo)   (Free Twitter)
```

**Configuration:**
```yaml
# scrapoxy.config.yaml
providers:
  # Tier 1: Webshare free proxies (reliable)
  - type: static
    name: webshare-tier1
    proxies:
      - http://user:pass@p.webshare.io:80
      # ... all 10 proxies

  # Tier 2: Proxifly free proxy list
  - type: proxifly
    name: proxifly-free
    url: https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.json
    refreshInterval: 300000  # 5 minutes
    filter:
      - country: US,GB,CA,AU,DE
      - protocol: https

  # Tier 3: ScraperAPI for tough targets
  - type: scraperapi
    name: scraperapi-backup
    apiKey: ${SCRAPERAPI_KEY}
    enabled: false  # Only use when others fail

server:
  port: 8888
  auth:
    username: admin
    password: ${PROXY_PASSWORD}

bypass:
  enabled: true
  testUrl: http://httpbin.org/ip
  interval: 60000  # Test every minute
```

**Usage in Crawlee:**
```typescript
const crawler = new PlaywrightCrawler({
  proxyConfiguration: {
    proxyUrls: ['http://admin:password@localhost:8888'],
  },
  // ... rest of config
});
```

---

### 6. 📊 Data Layer: Oracle Autonomous Database

**Why Oracle Autonomous DB?**
- Completely free (2 databases, 20GB each)
- Fully managed (auto-tuning, auto-backups, auto-patching)
- PostgreSQL compatible
- High availability built-in
- No maintenance overhead

**Database 1: `scraper_metadata`**
```sql
-- Job queue metadata
create table jobs (
    id bigserial primary key,
    source_id varchar(100) not null,
    url text not null,
    source_type varchar(50) not null,
    priority integer default 5,
    status varchar(20) default 'pending',
    scheduled_at timestamp default now(),
    started_at timestamp,
    completed_at timestamp,
    retry_count integer default 0,
    max_retries integer default 3,
    error_message text,
    worker_id varchar(100)
);

-- Source configuration
create table sources (
    id varchar(100) primary key,
    name varchar(200) not null,
    url_pattern text not null,
    source_type varchar(50) not null,
    scrape_method varchar(50), -- 'rss', 'api', 'browser', 'nitter'
    schedule_cron varchar(50),
    selectors jsonb,
    rate_limit integer default 10, -- requests per minute
    is_active boolean default true,
    last_scraped timestamp,
    last_success timestamp,
    success_rate decimal(5,2) default 100.0,
    failure_count integer default 0,
    proxy_tier varchar(20) default 'standard' -- 'premium' for tough sites
);

-- Scraping logs
create table scrape_logs (
    id bigserial primary key,
    job_id bigint references jobs(id),
    level varchar(10) not null, -- 'info', 'warn', 'error'
    message text not null,
    created_at timestamp default now()
);
```

**Database 2: `scraped_content`**
```sql
-- Main content storage
create table content (
    id bigserial primary key,
    source_id varchar(100) not null references sources(id),
    url text not null,
    title text,
    content text,
    summary text, -- Generated 2-3 minute summary
    author varchar(200),
    published_at timestamp,
    scraped_at timestamp default now(),
    content_hash varchar(64) unique not null,
    
    -- Classification
    department_tags varchar[] default '{}',
    category varchar(50),
    priority_score integer default 5,
    
    -- Processing status
    is_processed boolean default false,
    is_summarized boolean default false,
    is_published boolean default false,
    
    -- Metadata
    raw_html_size integer,
    word_count integer,
    read_time_minutes integer,
    metadata jsonb default '{}'
);

-- Deduplication index
create index idx_content_hash on content(content_hash);

-- Department/category queries
create index idx_content_dept on content using gin(department_tags);
create index idx_content_category on content(category);
create index idx_content_scraped_at on content(scraped_at desc);

-- Full-text search
create index idx_content_fts on content 
    using gin(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')));

-- Velocity tracking (for breaking news detection)
create table velocity_metrics (
    id bigserial primary key,
    source_id varchar(100) not null,
    hour_bucket timestamp not null,
    post_count integer default 0,
    avg_engagement decimal(10,2),
    velocity_score decimal(5,2), -- calculated: posts vs baseline
    is_breaking boolean default false
);
```

---

### 7. 📮 Queue System: BullMQ + KeyDB

**Why BullMQ over RabbitMQ?**
- Simpler architecture (just Redis)
- Better TypeScript/JavaScript integration
- Built-in job delays, retries, rate limiting
- Progress tracking
- Sufficient for 750 sources

**Why KeyDB over Redis?**
- KeyDB is a multi-threaded fork of Redis
- Better performance on multi-core systems
- Drop-in replacement (same protocol)
- Perfect for Oracle's ARM processors

**Docker Compose Configuration:**
```yaml
services:
  keydb:
    image: eqalpha/keydb:latest
    restart: always
    command: keydb-server --appendonly yes --maxmemory 4gb --maxmemory-policy allkeys-lru
    volumes:
      - keydb_data:/data
    ports:
      - "6379:6379"

  # BullMQ worker (Crawlee)
  scraper-worker:
    build: ./scraper
    environment:
      - REDIS_HOST=keydb
      - REDIS_PORT=6379
      - DATABASE_URL=postgresql://user:pass@autonomous-db/ scraped_content_db
    depends_on:
      - keydb
    deploy:
      replicas: 4  # 4 concurrent workers
```

---

### 8. 📈 Monitoring: Uptime Kuma

**What to Monitor:**
- Oracle VM availability
- Coolify dashboard
- Scrapoxy proxy health
- Database connectivity
- Individual scraper success rates

**Alert Channels:**
- Discord webhook (for breaking news)
- Email (for system failures)
- Telegram (for daily summaries)

---

## 🚀 Deployment Guide

### Phase 1: Oracle Cloud Setup (30 minutes)

1. **Create Oracle Cloud account** (or login to existing)

2. **Launch Instance:**
   ```
   Navigation: Compute → Instances → Create Instance
   
   Configuration:
   - Name: scraper-master
   - Shape: VM.Standard.A1.Flex
   - OCPUs: 4
   - Memory: 24 GB
   - Boot Volume: 200 GB
   - Image: Canonical Ubuntu 22.04 (aarch64)
   - Add SSH key
   ```

3. **Open Security List Ports:**
   ```
   Navigation: Networking → Virtual Cloud Networks → Security Lists
   
   Add Ingress Rules:
   - 22 (SSH)          - 0.0.0.0/0
   - 80 (HTTP)         - 0.0.0.0/0
   - 443 (HTTPS)       - 0.0.0.0/0
   - 3001 (Uptime Kuma) - Your IP only
   - 5678 (n8n)        - Your IP only
   - 8890 (Scrapoxy)   - Your IP only
   ```

4. **Create Autonomous Databases:**
   ```
   Navigation: Oracle Database → Autonomous Database → Create
   
   Create TWO databases:
   
   Database 1:
   - Name: scraper_metadata
   - Workload Type: Transaction Processing
   - OCPU: 0.25 (E3)
   - Storage: 20 GB
   
   Database 2:
   - Name: scraped_content
   - Workload Type: Transaction Processing
   - OCPU: 0.25 (E3)
   - Storage: 20 GB
   ```

### Phase 2: Install Coolify (10 minutes)

```bash
# SSH into instance
ssh -i ~/.ssh/your-key ubuntu@YOUR_INSTANCE_IP

# Update system
sudo apt update && sudo apt upgrade -y

# Install Coolify
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash

# Note the URL and credentials printed at the end
# Access at: http://YOUR_IP:8000
```

### Phase 3: Configure Services in Coolify (30 minutes)

1. **Add KeyDB (Redis):**
   - Services → Add → KeyDB
   - Name: `keydb-queue`
   - Port: 6379
   - Deploy

2. **Add PostgreSQL (for metadata):**
   - Services → Add → PostgreSQL
   - Name: `postgres-metadata`
   - Database: `bullmq_metadata`
   - Deploy

3. **Add Scrapoxy:**
   - Services → Add → Docker Compose
   - Use scrapoxy config
   - Deploy

4. **Add Uptime Kuma:**
   - Services → Add → Uptime Kuma
   - Port: 3001
   - Deploy

### Phase 4: Deploy Scrapers (20 minutes)

1. **Create GitHub repository** with scraper code

2. **Add Resource in Coolify:**
   - Resources → Add → GitHub App
   - Select repository
   - Type: Docker Compose
   - Deploy

3. **Configure Environment Variables:**
   ```
   DATABASE_URL=postgresql://user:pass@host/scraped_content
   METADATA_URL=postgresql://user:pass@host/scraper_metadata
   REDIS_HOST=keydb-queue
   REDIS_PORT=6379
   PROXY_URL=http://admin:password@scrapoxy:8888
   SCRAPERAPI_KEY=your_key_here
   ```

### Phase 5: Configure Scheduling (10 minutes)

Add Ofelia labels to your docker-compose:

```yaml
services:
  scraper-worker:
    labels:
      ofelia.enabled: "true"
      
      # Critical sources - every 15 min
      ofelia.job-run.critical.schedule: "@every 15m"
      ofelia.job-run.critical.command: "npm run scrape -- --priority=critical"
      
      # Breaking sources - every 30 min
      ofelia.job-run.breaking.schedule: "@every 30m"
      ofelia.job-run.breaking.command: "npm run scrape -- --priority=breaking"
      
      # Standard sources - every 6 hours
      ofelia.job-run.standard.schedule: "0 */6 * * *"
      ofelia.job-run.standard.command: "npm run scrape -- --priority=standard"
      
      # Batch - daily
      ofelia.job-run.batch.schedule: "0 2 * * *"  # 2 AM daily
      ofelia.job-run.batch.command: "npm run scrape -- --priority=batch --extract-full"
```

---

## 📊 Resource Allocation

### Oracle VM: 4 CPU / 24 GB RAM

| Service | CPU | RAM | Purpose |
|---------|-----|-----|---------|
| Coolify + System | 0.5 | 2 GB | Orchestration overhead |
| KeyDB (Redis) | 0.5 | 4 GB | Job queues, caching |
| PostgreSQL | 0.5 | 2 GB | Metadata, logs |
| Scrapoxy | 0.5 | 2 GB | Proxy rotation |
| Crawlee Workers (×4) | 2.0 | 12 GB | Main scraping (4× workers) |
| Uptime Kuma + n8n | 0.5 | 2 GB | Monitoring, workflows |
| **Total Reserved** | **4.5** | **24 GB** | Full utilization |

*Note: Use CPU oversubscription (containers share cores efficiently)*

---

## 💰 Cost Comparison

| Component | Traditional Cloud | This Architecture | Savings |
|-----------|------------------|-------------------|---------|
| Compute (24/7) | $50-100/mo | $0 | $600-1200/yr |
| Managed Database | $30-50/mo | $0 | $360-600/yr |
| Redis/Queue | $20-30/mo | $0 | $240-360/yr |
| PaaS/Orchestration | $20-50/mo | $0 | $240-600/yr |
| Monitoring | $10-20/mo | $0 | $120-240/yr |
| **TOTAL** | **$130-250/mo** | **$0** | **$1560-3000/yr** |

**If you need to scale beyond free tier:**
| Scale | Solution | Cost |
|-------|----------|------|
| Current (750 sources) | Oracle Free | $0 |
| Growth (1500 sources) | Add Hetzner CX22 | ~$5/mo |
| Scale (3000+ sources) | 2× Oracle Pay-as-you-go | ~$20/mo |
| Production | Kubernetes on Hetzner | ~$50/mo |

---

## 🎯 Advantages of This Architecture

### Over GitHub Actions:
- ✅ **No 6-hour timeout** - runs 24/7
- ✅ **No concurrency limits** - unlimited parallel jobs
- ✅ **Persistent storage** - 200GB local + databases
- ✅ **Custom proxy rotation** - Scrapoxy vs none
- ✅ **No egress limits** - 10TB free bandwidth

### Over n8n Cloud:
- ✅ **No execution limits** - unlimited workflows
- ✅ **Full code control** - TypeScript/Python vs visual only
- ✅ **Custom proxy support** - Scrapoxy integration
- ✅ **No rate limiting** - limited only by target sites
- ✅ **Data ownership** - data stays on your server

### Over Paid Services (ScrapingBee, Apify):
- ✅ **$0 cost** vs $49-500+/mo
- ✅ **No request limits** - limited only by hardware
- ✅ **Full customization** - any scraper logic
- ✅ **Multiple proxy sources** - not locked to one provider
- ✅ **Database included** - no extra storage costs

---

## ⚠️ Important Considerations

### 1. Oracle Cloud Limitations
- **Account verification**: Requires credit card (won't be charged)
- **Capacity issues**: Sometimes "out of capacity" for ARM instances
  - Solution: Try different region (US-East, US-West, EU)
  - Solution: Use auto-retry scripts
- **Idle reclamation**: VMs may be reclaimed if idle for 7 days
  - Solution: Keep CPU > 20% (scraping does this naturally)

### 2. Rate Limiting & Ethics
Even with free infrastructure, respect target sites:
```typescript
const rateLimits = {
  'linkedin': 5,    // 5 requests/minute
  'instagram': 5,   // 5 requests/minute
  'twitter': 10,    // 10 requests/minute
  'reddit': 30,     // 30 requests/minute
  'github': 60,     // 60 requests/minute
  'rss': 120,       // 2 requests/second
};
```

### 3. IP Reputation
- Oracle Cloud IPs are datacenter IPs
- Some sites (LinkedIn, Instagram) may block them
- Solution: Use Webshare/ScraperAPI for tough targets
- Solution: Residential proxies ($0.60-2/GB) for critical sites

### 4. Backup Strategy
```bash
# Daily backup to Oracle Object Storage (free 10GB)
oci os object put -bn scraper-backups --file backup.sql

# Or use rclone to backup to multiple free cloud storages:
# - Google Drive (15GB free)
# - Mega (20GB free)
# - Storj (25GB free)
```

---

## 🔄 Scaling Path

### Phase 1: Current (750 sources)
- Single Oracle instance (4 core/24GB)
- 4 Crawlee workers
- Handles ~1,000 pages/hour
- **Cost: $0**

### Phase 2: Growth (1500 sources)
- Add Hetzner CX22 (~$5/mo)
- Move some workers to Hetzner
- Use Coolify multi-server feature
- **Cost: ~$5/mo**

### Phase 3: Scale (3000+ sources)
- Upgrade Oracle to Pay-as-you-go
- 2× instances (8 core/48GB total)
- Add dedicated proxy servers
- **Cost: ~$20/mo**

### Phase 4: Production (10000+ sources)
- Kubernetes cluster (K3s)
- Multi-cloud (Oracle + Hetzner + AWS Lambda)
- Managed database (Neon/Supabase)
- **Cost: ~$50-100/mo**

---

## 📚 Quick Reference

### Coolify Dashboard
```
URL: http://YOUR_IP:8000
Purpose: Deploy services, manage databases, view logs
```

### Scrapoxy Dashboard
```
URL: http://YOUR_IP:8890
Purpose: Monitor proxy health, configure sources
```

### Uptime Kuma
```
URL: http://YOUR_IP:3001
Purpose: Monitor all services, alerts
```

### n8n (Optional)
```
URL: http://YOUR_IP:5678
Purpose: Visual workflow editing
```

### Database Connection
```
Host: (from Oracle Console)
Port: 1521
Database: scraper_metadata / scraped_content
Username: ADMIN
Password: (from Oracle Console)
```

---

## ✅ Deployment Checklist

### Day 1: Infrastructure
- [ ] Create Oracle Cloud account
- [ ] Launch 4-core/24GB ARM instance
- [ ] Create 2 Autonomous Databases
- [ ] Open required ports
- [ ] Install Coolify

### Day 2: Core Services
- [ ] Deploy KeyDB (Redis)
- [ ] Deploy PostgreSQL
- [ ] Deploy Scrapoxy
- [ ] Configure proxy sources
- [ ] Test proxy rotation

### Day 3: Scrapers
- [ ] Create GitHub repo
- [ ] Write Crawlee worker
- [ ] Connect repo to Coolify
- [ ] Deploy workers
- [ ] Test single source

### Day 4: Scheduling
- [ ] Configure Ofelia labels
- [ ] Set up cron schedules
- [ ] Test job queue
- [ ] Verify database writes

### Day 5: Monitoring
- [ ] Deploy Uptime Kuma
- [ ] Add health checks
- [ ] Configure Discord alerts
- [ ] Test notifications

### Day 6: Optimization
- [ ] Add all 750 sources
- [ ] Tune rate limits
- [ ] Monitor resource usage
- [ ] Optimize selectors

---

## 🎓 Learning Resources

- **Coolify Docs**: https://coolify.io/docs/
- **Crawlee Guide**: https://crawlee.dev/docs/guides/
- **BullMQ Patterns**: https://docs.bullmq.io/
- **Oracle Autonomous DB**: https://docs.oracle.com/en/cloud/paas/autonomous-database/

---

## 📝 Conclusion

This architecture gives you:
- ✅ **$0/month** operational cost
- ✅ **24/7/365** uptime
- ✅ **750+ sources** capacity (scalable to 2000+)
- ✅ **Professional-grade** infrastructure
- ✅ **Clear upgrade path** as you grow

**Start with Phase 1 today. Deploy your first scraper tomorrow.**

---

*Built by combining the best of: Oracle Cloud Always Free, Coolify PaaS, Crawlee scraping engine, BullMQ job queues, and Scrapoxy proxy rotation.*
