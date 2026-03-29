import sqlite3

db = sqlite3.connect('newsletter.db')
cursor = db.cursor()

# Check table schemas
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='processed_content'")
print("PROCESSED_CONTENT SCHEMA:")
print(cursor.fetchone()[0])

cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='raw_content'")
print("\nRAW_CONTENT SCHEMA:")
print(cursor.fetchone()[0])

db.close()
