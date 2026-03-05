"""Backfill relevance_score for all processed_content rows.

Computes a composite 1-100 score based on:
  - Content quality (length, summary quality, key_points)
  - Category specificity (non-general = better)
  - Department relevance (keyword matching)
  - Source signal (attractiveness_score as proxy)
Every article gets a minimum score of 5 (no zeros).
"""

import json
import os
import sys
import sqlite3
import importlib.util

# Direct import of dept_relevance to avoid triggering backend __init__ chains
_mod_path = os.path.join(
    os.path.dirname(__file__), "..", "backend", "app", "services", "dept_relevance.py"
)
_spec = importlib.util.spec_from_file_location("dept_relevance", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
score_article_departments = _mod.score_article_departments

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "newsletter.db")


def compute_relevance(title, content, category, dept_tags_json, content_blocks_json, attractiveness_score):
    """Compute a composite relevance score (5-100) from multiple signals."""
    score = 0

    # 1. Content quality (0-30 points)
    content_len = len(content) if content else 0
    if content_len >= 500:
        score += 15
    elif content_len >= 200:
        score += 10
    elif content_len >= 50:
        score += 5

    # Has meaningful summary/key_points
    try:
        blocks = json.loads(content_blocks_json) if content_blocks_json else {}
    except Exception:
        blocks = {}
    kp = blocks.get("key_points", [])
    hook = blocks.get("hook", "")
    if kp and len(kp) >= 2:
        score += 10  # Has real key points from AI
    if hook and hook != title and len(hook) > 20:
        score += 5  # Has real AI-generated hook (not just title copy)

    # 2. Category specificity (0-15 points)
    if category and category != "general":
        score += 15
    elif category == "general":
        score += 3  # Still some content, just uncategorized

    # 3. Department relevance (0-35 points)
    dept_scores = score_article_departments(title or "", content or "")
    max_dept = dept_scores[0][1] if dept_scores else 0
    dept_points = min(35, int(max_dept * 3.5))
    score += dept_points

    # Also check if already assigned to departments
    try:
        dept_tags = json.loads(dept_tags_json) if dept_tags_json else []
    except Exception:
        dept_tags = []
    if dept_tags and not dept_scores:
        score += 10  # Has dept assignment even if keyword scoring is low

    # 4. Source quality / attractiveness (0-20 points)
    attr = attractiveness_score or 0
    if attr >= 50:
        score += 20
    elif attr >= 40:
        score += 15
    elif attr >= 30:
        score += 10
    elif attr >= 20:
        score += 5

    # Ensure minimum of 5, maximum of 100
    return max(5, min(100, score))


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Before distribution
    cur.execute(
        "SELECT relevance_score, COUNT(*) as cnt FROM processed_content "
        "GROUP BY relevance_score ORDER BY relevance_score"
    )
    print("=== BEFORE ===")
    before = cur.fetchall()
    for row in before:
        print(f"  score={str(row['relevance_score']):>4s}: {row['cnt']:4d}")

    # Fetch all articles joined with raw_content for full text
    cur.execute("""
        SELECT pc.id, pc.title, pc.category, pc.department_tags,
               pc.content_blocks, pc.attractiveness_score,
               COALESCE(rc.original_content, '') as full_content
        FROM processed_content pc
        LEFT JOIN raw_content rc ON REPLACE(pc.raw_content_id, '-', '') = rc.id
    """)
    rows = cur.fetchall()
    print(f"\nProcessing {len(rows)} articles...")

    updated = 0
    for row in rows:
        relevance = compute_relevance(
            row["title"],
            row["full_content"],
            row["category"],
            row["department_tags"],
            row["content_blocks"],
            row["attractiveness_score"],
        )
        cur.execute(
            "UPDATE processed_content SET relevance_score = ? WHERE id = ?",
            (relevance, row["id"]),
        )
        updated += 1

    conn.commit()
    print(f"Updated {updated} rows.")

    # After distribution
    cur.execute(
        "SELECT relevance_score, COUNT(*) as cnt FROM processed_content "
        "GROUP BY relevance_score ORDER BY relevance_score"
    )
    after = cur.fetchall()
    total = sum(r["cnt"] for r in after)
    print("\n=== AFTER ===")
    for row in after:
        score_val = row["relevance_score"]
        cnt = row["cnt"]
        pct = cnt * 100 / total if total else 0
        print(f"  score={str(score_val):>4s}: {cnt:4d}  ({pct:.1f}%)")
    print(f"  {'TOTAL':>10s}: {total}")

    # Summary stats
    cur.execute(
        "SELECT AVG(relevance_score) as avg_score, "
        "MIN(relevance_score) as min_score, MAX(relevance_score) as max_score, "
        "SUM(CASE WHEN relevance_score > 0 THEN 1 ELSE 0 END) as nonzero "
        "FROM processed_content"
    )
    stats = cur.fetchone()
    print(f"\n=== SUMMARY ===")
    print(f"  Average: {stats['avg_score']:.1f}")
    print(f"  Min: {stats['min_score']}, Max: {stats['max_score']}")
    print(f"  Non-zero: {stats['nonzero']} / {total} ({stats['nonzero'] * 100 / total:.1f}%)")

    conn.close()


if __name__ == "__main__":
    main()
