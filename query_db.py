import sqlite3
import json

conn = sqlite3.connect('D:/newsletter/newsletter.db')
cursor = conn.cursor()

print('\n5. DEPARTMENT/SECTION ANALYSIS')
print('-' * 40)

# Get department tags from processed content
cursor.execute("SELECT department_tags FROM processed_content LIMIT 1")
sample = cursor.fetchone()
print(f"Sample department_tags structure: {sample[0][:100] if sample[0] else 'null'}")

# Get the actual data from cached_feeds to understand sections
cursor.execute("SELECT department, LENGTH(data) as data_size FROM cached_feeds ORDER BY department")
feeds_data = cursor.fetchall()
print("\nCached feeds by department:")
for dept, size in feeds_data:
    print(f"  {dept}: data size ~{size} bytes")

# Parse JSON to count sections
print("\n6. SECTION BREAKDOWN IN CACHED_FEEDS")
print('-' * 40)
cursor.execute("SELECT department, data FROM cached_feeds")
feeds = cursor.fetchall()

section_counts = {}
for dept, data in feeds:
    try:
        json_data = json.loads(data)
        if isinstance(json_data, dict):
            for section_key in ['breaking', 'trending', 'department', 'career']:
                if section_key in json_data:
                    items = json_data[section_key]
                    if isinstance(items, list):
                        if section_key not in section_counts:
                            section_counts[section_key] = {}
                        section_counts[section_key][dept] = len(items)
    except:
        pass

for section in ['breaking', 'trending', 'department', 'career']:
    if section in section_counts:
        print(f"\n{section.upper()} section by department:")
        total = 0
        for dept in sorted(section_counts[section].keys()):
            count = section_counts[section][dept]
            total += count
            status = "⚠️  ZERO" if count == 0 else f"OK ({count})"
            print(f"  {dept}: {status}")
        print(f"  TOTAL {section}: {total}")
    else:
        print(f"\n{section.upper()}: No data")

conn.close()
