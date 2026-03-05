"""Batch re-process all articles with the content-first AI summarizer.

Run: python scripts/reprocess_summaries.py
Requires server running at localhost:8000.
"""

import asyncio
import json
import os
import re
import sqlite3
import sys
import time

import httpx


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'newsletter.db')
API_BASE = "http://localhost:8000"


def clean_rss_artifacts(text: str) -> str:
    """Strip RSS feed artifacts from summary text."""
    if not text:
        return text
    text = re.sub(r'\s*Continue Reading\s+Category:.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'\s*Tags:.*$', '', text, flags=re.DOTALL)
    return text.strip()


async def reprocess_article(client: httpx.AsyncClient, title: str, content: str, category: str, max_retries: int = 3) -> dict | None:
    """Call the AI summarize endpoint for one article with retry logic."""
    for attempt in range(max_retries):
        try:
            resp = await client.post(
                f"{API_BASE}/api/v1/ai/summarize",
                json={"title": title, "content": content, "category": category or "general"},
                timeout=60.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {}).get("summary", {})
            elif resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                await asyncio.sleep(wait)
                continue
            else:
                print(f"  HTTP {resp.status_code} for {title[:50]}: {resp.text[:100]}")
                return None
        except httpx.ConnectError:
            print(f"  Connection error (attempt {attempt+1}/{max_retries})")
            await asyncio.sleep(2)
        except httpx.ReadTimeout:
            print(f"  Timeout (attempt {attempt+1}/{max_retries})")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"  Error for {title[:50]}: {type(e).__name__}: {e}")
            return None
    return None


async def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT p.id, p.title, p.category, p.content_blocks, p.summary,
               r.original_content
        FROM processed_content p
        LEFT JOIN raw_content r ON REPLACE(p.raw_content_id, '-', '') = REPLACE(r.id, '-', '')
        ORDER BY p.attractiveness_score DESC
    """)
    articles = c.fetchall()
    total = len(articles)
    print(f"Found {total} articles to re-process")

    updated = 0
    skipped = 0
    errors = 0

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{API_BASE}/api/v1/ai/status", timeout=5)
            status = resp.json()
            print(f"AI Provider: {status.get('data', {}).get('provider', 'unknown')}")
        except Exception:
            print("ERROR: Server not running at localhost:8000. Start it first.")
            conn.close()
            return

        for i, (pid, title, category, content_blocks_json, summary, raw_content) in enumerate(articles):
            try:
                blocks = json.loads(content_blocks_json) if content_blocks_json else {}
            except Exception:
                blocks = {}

            kp = blocks.get("key_points", [])
            if kp and len(kp) >= 2 and blocks.get("hook") != title:
                skipped += 1
                continue

            content = raw_content or summary or title
            content = clean_rss_artifacts(content)

            if not content or len(content) < 20:
                skipped += 1
                continue

            result = await reprocess_article(client, title, content, category)

            if result and result.get("hook") and result.get("key_points"):
                new_blocks = {
                    "hook": result.get("hook", title),
                    "why_it_matters": result.get("why_it_matters", ""),
                    "key_points": result.get("key_points", []),
                    "action_step": result.get("action_step", ""),
                }
                new_summary = clean_rss_artifacts(result.get("why_it_matters", summary))
                if not new_summary:
                    new_summary = clean_rss_artifacts(summary)

                c.execute(
                    "UPDATE processed_content SET content_blocks = ?, summary = ? WHERE id = ?",
                    (json.dumps(new_blocks), new_summary, pid)
                )
                updated += 1
            else:
                clean_sum = clean_rss_artifacts(summary)
                if clean_sum != summary:
                    c.execute(
                        "UPDATE processed_content SET summary = ? WHERE id = ?",
                        (clean_sum, pid)
                    )
                errors += 1

            if (i + 1) % 10 == 0:
                conn.commit()
                print(f"  [{i+1}/{total}] updated={updated} skipped={skipped} errors={errors}")
                await asyncio.sleep(3.0)
            else:
                await asyncio.sleep(1.5)

    conn.commit()
    conn.close()

    print(f"\nDone! Updated: {updated}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    asyncio.run(main())
