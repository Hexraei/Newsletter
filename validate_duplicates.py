import sqlite3
import json

db = sqlite3.connect('newsletter.db')
cursor = db.cursor()

print("=" * 80)
print("DUPLICATE TITLE ANALYSIS")
print("=" * 80)

# Find duplicate titles in processed_content
cursor.execute("""
    SELECT title, COUNT(*) as cnt 
    FROM processed_content 
    GROUP BY title 
    HAVING cnt > 1
    ORDER BY cnt DESC
    LIMIT 20
""")

duplicates = cursor.fetchall()
if duplicates:
    print(f"Found {len(duplicates)} titles with duplicates:")
    for title, cnt in duplicates:
        print(f"  x{cnt}: '{title[:60]}...'")
else:
    print("No duplicate titles found.")

# Total duplicate count
cursor.execute("""
    SELECT COUNT(*) FROM processed_content 
    WHERE title IN (
        SELECT title FROM processed_content 
        GROUP BY title HAVING COUNT(*) > 1
    )
""")
total_dupes = cursor.fetchone()[0]
total_items = 413

print(f"\nGlobal duplicate analysis:")
print(f"  Total items: {total_items}")
print(f"  Items with duplicate titles: {total_dupes}")
if total_items > 0:
    print(f"  Duplicate ratio: {(total_dupes/total_items)*100:.2f}%")

print("\n" + "=" * 80)
print("CAREER COVERAGE BY DEPARTMENT")
print("=" * 80)

# Count career items per department
cursor.execute("""
    SELECT 
        department_tags,
        COUNT(CASE WHEN category='career' THEN 1 END) as career_count,
        COUNT(*) as total
    FROM processed_content
    GROUP BY department_tags
    ORDER BY department_tags
""")

dept_coverage = {}
for row in cursor.fetchall():
    try:
        dept_str = row[0]
        depts = json.loads(dept_str) if dept_str else []
        for dept in depts:
            if dept not in dept_coverage:
                dept_coverage[dept] = {'career': 0, 'total': 0}
            dept_coverage[dept]['career'] += row[1]
            dept_coverage[dept]['total'] += row[2]
    except:
        pass

# Ensure all known departments are in the dict
known_depts = ['CSE', 'ECE', 'AIDS', 'IT', 'AE', 'ME', 'EEE', 'CH', 'RAE', 'BT', 'CE', 'PT', 'general']
for dept in known_depts:
    if dept not in dept_coverage:
        dept_coverage[dept] = {'career': 0, 'total': 0}

print("\nDepartment Coverage:")
print(f"{'Dept':10} {'Career':8} {'Total':8} {'Ratio':8}")
print("-" * 35)

low_coverage = []
for dept in sorted(dept_coverage.keys()):
    data = dept_coverage[dept]
    career = data['career']
    total = data['total']
    ratio = (career / total * 100) if total > 0 else 0
    print(f"{dept:10} {career:8} {total:8} {ratio:7.1f}%")
    if career == 0 or ratio < 10:
        low_coverage.append((dept, career, total, ratio))

print("\n" + "=" * 80)
print("LOW/ZERO CAREER COVERAGE DEPARTMENTS")
print("=" * 80)
if low_coverage:
    print("Departments with zero or <10% career content:")
    for dept, career, total, ratio in sorted(low_coverage, key=lambda x: x[1]):
        print(f"  {dept}: {career} career items out of {total} total ({ratio:.1f}%)")
else:
    print("All departments have adequate career coverage.")

db.close()
