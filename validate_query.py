import sqlite3

db = sqlite3.connect('newsletter.db')
cursor = db.cursor()

print("=" * 80)
print("PROCESSED_CONTENT STATS")
print("=" * 80)
cursor.execute("SELECT COUNT(*) as total, COUNT(DISTINCT published_at) as published FROM processed_content;")
row = cursor.fetchone()
print(f"Total processed_content: {row[0]}")
print(f"Published (status='published'): {row[1]}")

cursor.execute("SELECT status, COUNT(*) FROM processed_content GROUP BY status;")
pc_status = cursor.fetchall()
print("processed_content status breakdown:")
for status, count in pc_status:
    print(f"  {status}: {count}")

print("\n" + "=" * 80)
print("RAW_CONTENT STATUS SPLIT")
print("=" * 80)
cursor.execute("SELECT status, COUNT(*) as count FROM raw_content GROUP BY status ORDER BY count DESC;")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

print("\n" + "=" * 80)
print("CACHED COUNTS PER DEPARTMENT (breaking/trending/department/career)")
print("=" * 80)

departments = ['ai', 'blockchain', 'cybersecurity', 'dev', 'devops', 'gamedev', 'infosec', 'mobile', 'robotics', 'security', 'startup', 'ux']

for dept in departments:
    cursor.execute(f"""
        SELECT 
            COUNT(CASE WHEN section='breaking' THEN 1 END) as breaking,
            COUNT(CASE WHEN section='trending' THEN 1 END) as trending,
            COUNT(CASE WHEN section='department' THEN 1 END) as department,
            COUNT(CASE WHEN section='career' THEN 1 END) as career
        FROM {dept}_cached;
    """)
    row = cursor.fetchone()
    print(f"{dept.upper():15} - breaking:{row[0]:3} trending:{row[1]:3} dept:{row[2]:3} career:{row[3]:3}")

print("\n" + "=" * 80)
print("DUPLICATE TITLE ANALYSIS")
print("=" * 80)

for dept in departments:
    cursor.execute(f"""
        SELECT section, title, COUNT(*) as cnt 
        FROM {dept}_cached 
        GROUP BY section, title 
        HAVING cnt > 1
        ORDER BY cnt DESC;
    """)
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"\n{dept.upper()}:")
        for row in duplicates:
            print(f"  {row[0]}: '{row[1][:50]}...' x{row[2]}")

# Global duplicate ratio
print("\n" + "=" * 80)
print("GLOBAL DUPLICATE RATIO")
print("=" * 80)
total_items = 0
duplicate_items = 0

for dept in departments:
    cursor.execute(f"SELECT COUNT(*) FROM {dept}_cached;")
    dept_total = cursor.fetchone()[0]
    total_items += dept_total
    
    cursor.execute(f"""
        SELECT COUNT(*) FROM {dept}_cached 
        WHERE title IN (
            SELECT title FROM {dept}_cached 
            GROUP BY title HAVING COUNT(*) > 1
        );
    """)
    dept_dupes = cursor.fetchone()[0]
    duplicate_items += dept_dupes

if total_items > 0:
    dup_ratio = (duplicate_items / total_items) * 100
    print(f"Total cached items: {total_items}")
    print(f"Items with duplicate titles: {duplicate_items}")
    print(f"Duplicate ratio: {dup_ratio:.2f}%")

db.close()
