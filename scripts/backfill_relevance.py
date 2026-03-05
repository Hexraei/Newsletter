"""Backfill relevance_score for all processed_content rows.

Joins processed_content with raw_content (handling UUID dash mismatch)
and uses dept_relevance scoring to compute a 0-100 relevance score.
"""

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


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Before distribution
    cur.execute(
        "SELECT relevance_score, COUNT(*) as cnt FROM processed_content "
        "GROUP BY relevance_score ORDER BY cnt DESC"
    )
    print("=== BEFORE ===")
    before = cur.fetchall()
    for row in before:
        print(f"  score={str(row['relevance_score']):>4s}: {row['cnt']:4d}")

    # Fetch all articles joined with raw_content for full text
    # Handle UUID mismatch: raw_content.id has no dashes, processed_content.raw_content_id has dashes
    cur.execute("""
        SELECT pc.id, pc.title, COALESCE(rc.original_content, '') as full_content
        FROM processed_content pc
        LEFT JOIN raw_content rc ON REPLACE(pc.raw_content_id, '-', '') = rc.id
    """)
    rows = cur.fetchall()
    print(f"\nProcessing {len(rows)} articles...")

    updated = 0
    for row in rows:
        title = row["title"] or ""
        content = row["full_content"] or ""
        dept_scores = score_article_departments(title, content)
        max_score = dept_scores[0][1] if dept_scores else 0
        relevance = min(100, int(max_score * 10))

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
        "GROUP BY relevance_score ORDER BY cnt DESC"
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
        "COUNT(*) FILTER (WHERE relevance_score > 0) as nonzero "
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
