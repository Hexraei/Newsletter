"""
setup_local.py — One-shot local setup against Supabase or SQLite.

Run this once to:
  1. Create all DB tables (create_all for SQLite, alembic for cloud Postgres)
  2. Seed all department sources
  3. Optionally run the RSS scraper once

Usage:
  python setup_local.py
"""

import asyncio
import os
import subprocess
import sys

_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, _root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

DB_URL = os.environ.get("DATABASE_URL", "")
IS_SQLITE = DB_URL.startswith("sqlite")

def banner(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")

def run(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd or _root, env=os.environ)
    if result.returncode != 0:
        print(f"\n❌  Command failed: {cmd}")
        sys.exit(result.returncode)

async def create_tables_sqlite():
    """Use SQLAlchemy create_all for SQLite (skips Alembic migration quirks)."""
    from app.models.base import engine, Base
    import app.models  # ensure all models are imported/registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  ✅  All tables created via create_all()")

async def test_connection():
    from app.models.base import engine
    from sqlalchemy import text
    try:
        async with engine.connect() as c:
            await c.execute(text("SELECT 1"))
        print("  ✅  Database connection OK")
    except Exception as e:
        print(f"  ❌  Cannot connect to DB: {e}")
        print(f"\n  DATABASE_URL = {DB_URL[:70]}...")
        sys.exit(1)


if __name__ == "__main__":
    db_type = "SQLite (local file)" if IS_SQLITE else "Cloud Postgres"
    banner(f"LOCAL SETUP: {db_type}")
    print(f"  DB: {DB_URL[:70]}...")

    print("\n[1/3] Testing DB connection...")
    asyncio.run(test_connection())

    if IS_SQLITE:
        print("\n[2/3] Creating tables via SQLAlchemy create_all (SQLite mode)...")
        asyncio.run(create_tables_sqlite())
    else:
        print("\n[2/3] Running migrations (alembic upgrade head)...")
        run("alembic upgrade head", cwd=os.path.join(_root, "backend"))

    print("\n[3/3] Seeding sources...")
    run("python scrapers/seed_sources.py")

    banner("Setup complete! You can now run scrapers:")
    print("  python scrapers/run_rss.py")
    print("  python scrapers/run_general.py")
    print("  python scrapers/run_research.py\n")
