import sqlite3
import json

db = sqlite3.connect('newsletter.db')
cursor = db.cursor()

print("=" * 80)
print("PROCESSED_CONTENT STATS")
print("=" * 80)
cursor.execute("SELECT COUNT(*) as total FROM processed_content")
total = cursor.fetchone()[0]
print(f"Total processed_content items: {total}")

cursor.execute("SELECT status, COUNT(*) FROM processed_content GROUP BY status")
for status, count in cursor.fetchall():
    print(f"  {status}: {count}")

print("\n" + "=" * 80)
print("RAW_CONTENT STATUS SPLIT")
print("=" * 80)
cursor.execute("SELECT status, COUNT(*) as count FROM raw_content GROUP BY status ORDER BY count DESC")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

print("\n" + "=" * 80)
print("PROCESSED_CONTENT BY CATEGORY")
print("=" * 80)
cursor.execute("SELECT category, COUNT(*) FROM processed_content GROUP BY category ORDER BY COUNT(*) DESC")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

print("\n" + "=" * 80)
print("DEPARTMENT_TAGS COVERAGE")
print("=" * 80)
cursor.execute("SELECT DISTINCT department_tags FROM processed_content LIMIT 5")
sample = cursor.fetchone()
if sample:
    try:
        tags = json.loads(sample[0])
        print("Sample department_tags structure:")
        print(f"  {tags}")
    except:
        print(f"  Raw: {sample[0]}")

# Get department counts
cursor.execute("""
    SELECT department_tags FROM processed_content
    WHERE department_tags != '{}' AND department_tags != ''
""")
all_dept_tags = cursor.fetchall()
dept_counts = {}
for row in all_dept_tags:
    try:
        tags = json.loads(row[0])
        for dept in tags:
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
    except:
        pass

print("\nDepartment tag counts across processed_content:")
for dept in sorted(dept_counts.keys(), key=lambda x: dept_counts[x], reverse=True):
    print(f"  {dept}: {dept_counts[dept]}")

print("\n" + "=" * 80)
print("CONTENT TYPE BREAKDOWN")
print("=" * 80)
cursor.execute("SELECT content_type, COUNT(*) FROM processed_content GROUP BY content_type ORDER BY COUNT(*) DESC")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

db.close()
