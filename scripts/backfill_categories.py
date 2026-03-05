"""Backfill article categories using the improved detect_category() function.

Only updates articles currently categorized as "general".
Prints before/after distribution.
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
detect_category = _mod.detect_category


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "newsletter.db")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Before distribution
    cur.execute(
        "SELECT category, COUNT(*) as cnt FROM processed_content GROUP BY category ORDER BY cnt DESC"
    )
    before = {row["category"]: row["cnt"] for row in cur.fetchall()}
    total = sum(before.values())
    print("=== BEFORE ===")
    for cat, cnt in sorted(before.items(), key=lambda x: -x[1]):
        print(f"  {cat:15s}: {cnt:4d}  ({cnt * 100 / total:.1f}%)")
    print(f"  {'TOTAL':15s}: {total}")

    # Fetch all "general" articles joined with raw_content for full text
    cur.execute("""
        SELECT pc.id, pc.title, COALESCE(rc.original_content, '') as full_content
        FROM processed_content pc
        LEFT JOIN raw_content rc ON pc.raw_content_id = rc.id
        WHERE pc.category = 'general'
    """)
    rows = cur.fetchall()
    print(f"\nProcessing {len(rows)} 'general' articles...")

    updated = 0
    reclassified = {}
    for row in rows:
        title = row["title"] or ""
        content = row["full_content"] or ""
        new_cat = detect_category(title, content)
        if new_cat != "general":
            cur.execute(
                "UPDATE processed_content SET category = ? WHERE id = ?",
                (new_cat, row["id"]),
            )
            updated += 1
            reclassified[new_cat] = reclassified.get(new_cat, 0) + 1

    conn.commit()

    print(f"\nReclassified {updated} articles:")
    for cat, cnt in sorted(reclassified.items(), key=lambda x: -x[1]):
        print(f"  -> {cat}: {cnt}")

    # After distribution
    cur.execute(
        "SELECT category, COUNT(*) as cnt FROM processed_content GROUP BY category ORDER BY cnt DESC"
    )
    after = {row["category"]: row["cnt"] for row in cur.fetchall()}
    print("\n=== AFTER ===")
    for cat, cnt in sorted(after.items(), key=lambda x: -x[1]):
        print(f"  {cat:15s}: {cnt:4d}  ({cnt * 100 / total:.1f}%)")
    print(f"  {'TOTAL':15s}: {total}")

    general_pct = after.get("general", 0) * 100 / total
    print(f"\n'general' reduced: {before.get('general', 0)} -> {after.get('general', 0)} ({general_pct:.1f}%)")

    conn.close()


if __name__ == "__main__":
    main()
