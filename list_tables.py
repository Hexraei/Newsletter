import sqlite3

db = sqlite3.connect('newsletter.db')
c = db.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = c.fetchall()
for t in tables:
    print(t[0])
db.close()
