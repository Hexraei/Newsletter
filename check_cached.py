import sqlite3

db = sqlite3.connect('newsletter.db')
c = db.cursor()

# Check cached_feeds schema
c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='cached_feeds'")
print("CACHED_FEEDS SCHEMA:")
print(c.fetchone()[0])

# Check sample data
c.execute("SELECT DISTINCT department FROM cached_feeds LIMIT 20")
depts = c.fetchall()
print("\nUnique departments in cached_feeds:")
for d in depts:
    print(f"  {d[0]}")

db.close()
