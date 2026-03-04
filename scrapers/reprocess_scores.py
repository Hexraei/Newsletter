"""Reprocess all existing content with improved department relevance scoring.

Reads each raw_content item, recalculates department_tags, category,
and relevance_score using the new dept_relevance module.

Usage: python scrapers/reprocess_scores.py
"""
import asyncio
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, _root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

import sqlite3
import json
from app.services.dept_relevance import assign_departments, detect_category, score_article_departments


def main():
    db_path = os.path.join(_root, "newsletter.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Build source cache
    sources = {}
    for row in c.execute("SELECT id, department_tags, default_categories, source_type FROM sources"):
        dept_tags = json.loads(row["department_tags"]) if row["department_tags"] else []
        default_cats = json.loads(row["default_categories"]) if row["default_categories"] else []
        sources[row["id"]] = {
            "dept_tags": dept_tags or default_cats,
            "source_type": row["source_type"] or "",
        }

    # Join processed + raw content
    rows = c.execute("""
        SELECT p.id as pid, r.original_title, r.original_content, r.source_id
        FROM processed_content p
        JOIN raw_content r ON REPLACE(p.raw_content_id, '-', '') = r.id
           OR p.raw_content_id = r.id
    """).fetchall()
    print(f"Found {len(rows)} items to re-score")

    dept_counts = {}
    cat_counts = {}
    updated = 0

    for row in rows:
        pid = row["pid"]
        title = row["original_title"] or ""
        content = row["original_content"] or ""
        source_id = row["source_id"]
        src = sources.get(source_id, {"dept_tags": [], "source_type": ""})

        # New department assignment
        new_depts = assign_departments(
            title, content,
            source_dept_tags=src["dept_tags"],
            source_type=src["source_type"],
        )
        if not new_depts:
            # For specific sources (academic, industry, research), fall back to source tags
            from app.services.dept_relevance import GENERAL_SOURCE_TYPES
            if src["source_type"] not in GENERAL_SOURCE_TYPES:
                new_depts = src["dept_tags"][:2] if src["dept_tags"] else []
            # If still empty, leave as empty list (general/untagged)

        # New category
        new_cat = detect_category(title, content)

        # Relevance score
        scored = score_article_departments(title, content, src["dept_tags"], src["source_type"])
        relevance = scored[0][1] if scored else 0
        relevance_normalized = min(100, int(relevance * 5))

        # Update
        c.execute("""
            UPDATE processed_content
            SET department_tags = ?, category = ?, relevance_score = ?
            WHERE id = ?
        """, (json.dumps(new_depts), new_cat, relevance_normalized, pid))

        for d in new_depts:
            dept_counts[d] = dept_counts.get(d, 0) + 1
        cat_counts[new_cat] = cat_counts.get(new_cat, 0) + 1
        updated += 1

    conn.commit()
    conn.close()

    print(f"\nUpdated {updated} items")
    print("\n=== DEPARTMENT DISTRIBUTION (new) ===")
    for dept, count in sorted(dept_counts.items(), key=lambda x: -x[1]):
        print(f"  {dept}: {count}")
    print("\n=== CATEGORY DISTRIBUTION (new) ===")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()

