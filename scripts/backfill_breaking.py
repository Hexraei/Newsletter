"""Backfill breaking news flags for existing articles.

Re-evaluates all articles using the updated (lower) breaking thresholds.
Run: python scripts/backfill_breaking.py
"""

import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'newsletter.db')

URGENT_KEYWORDS = [
    "breaking", "just announced", "outage", "urgent", "security flaw",
    "data breach", "zero-day", "vulnerability", "exploit", "acquires",
    "banned", "lawsuit", "recall", "emergency", "shutdown", "offline",
    "hacked", "launch", "release", "unveils", "announces", "critical",
    "alert", "leaked", "disruption", "acquisition", "ipo", "layoff", "raises",
]


def has_urgent_keywords(title: str, content: str) -> bool:
    text = f"{title} {content}".lower()
    return any(k in text for k in URGENT_KEYWORDS)


def content_age_hours(published_at: str, scraped_at: str) -> float | None:
    dt_str = published_at or scraped_at
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 3600)
    except Exception:
        return None


def is_breaking(score: int, age_hours: float | None, has_keywords: bool) -> bool:
    if age_hours is None or age_hours > 48:
        return False
    if score >= 48 and age_hours <= 12:
        return True
    if score >= 40 and age_hours <= 6:
        return True
    if score >= 35 and age_hours <= 24 and has_keywords:
        return True
    return False


def calculate_breaking_score(score: int, age_hours: float | None, has_keywords: bool) -> int:
    boost = 0
    if age_hours is not None:
        if age_hours <= 1:
            boost += 25
        elif age_hours <= 3:
            boost += 20
        elif age_hours <= 6:
            boost += 15
        elif age_hours <= 12:
            boost += 10
        elif age_hours <= 24:
            boost += 5
    if has_keywords:
        boost += 10
    return min(100, score + boost)


def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT p.id, p.title, p.attractiveness_score, p.is_breaking,
               r.original_content, r.published_at, r.scraped_at
        FROM processed_content p
        LEFT JOIN raw_content r ON REPLACE(p.raw_content_id, '-', '') = REPLACE(r.id, '-', '')
    """)
    rows = c.fetchall()
    
    total = len(rows)
    was_breaking = sum(1 for r in rows if r[3])
    now_breaking = 0
    updated = 0

    for pid, title, score, old_breaking, content, pub_at, scrape_at in rows:
        age = content_age_hours(pub_at, scrape_at)
        keywords = has_urgent_keywords(title or "", content or "")
        new_breaking = is_breaking(score or 0, age, keywords)
        b_score = calculate_breaking_score(score or 0, age, keywords) if new_breaking else 0

        if new_breaking != bool(old_breaking):
            c.execute(
                "UPDATE processed_content SET is_breaking = ?, breaking_score = ? WHERE id = ?",
                (1 if new_breaking else 0, b_score, pid)
            )
            updated += 1

        if new_breaking:
            now_breaking += 1

    conn.commit()
    conn.close()

    print(f"Total articles: {total}")
    print(f"Previously breaking: {was_breaking}")
    print(f"Now breaking: {now_breaking}")
    print(f"Updated: {updated}")


if __name__ == "__main__":
    main()
