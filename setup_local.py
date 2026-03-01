"""
setup_local.py — One-shot local setup against Supabase (or any cloud DB).

Run this once to:
  1. Apply all Alembic migrations
  2. Seed all department sources
  3. Run the RSS scraper once

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

def banner(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")

def run(cmd, cwd=None, env=None):
    result = subprocess.run(
        cmd, shell=True, cwd=cwd or _root,
        env={**os.environ, **(env or {})},
    )
    if result.returncode != 0:
        print(f"\n❌  Command failed: {cmd}")
        sys.exit(result.returncode)

async def test_connection():
    """Quick ping to verify DB is reachable before running anything."""
    import ssl
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    url = DB_URL
    connect_args = {}
    for param in ["sslmode=require", "ssl=require", "channel_binding=require"]:
        url = url.replace(f"?{param}", "").replace(f"&{param}", "")
    url = url.rstrip("?&")
    if "supabase" in DB_URL or "neon" in DB_URL:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx

    engine = create_async_engine(url, connect_args=connect_args, pool_size=1)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("  ✅  Database connection OK")
    except Exception as e:
        print(f"  ❌  Cannot connect to DB: {e}")
        print(f"\n  DATABASE_URL = {DB_URL[:60]}...")
        print("  Make sure the URL in backend/.env is correct and reachable.")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    banner("LOCAL SETUP: Supabase DB")
    print(f"  DB: {DB_URL[:60]}...")

    print("\n[1/3] Testing DB connection...")
    asyncio.run(test_connection())

    print("\n[2/3] Running migrations (alembic upgrade head)...")
    run("alembic upgrade head", cwd=os.path.join(_root, "backend"))

    print("\n[3/3] Seeding sources...")
    run(f"python scrapers/seed_sources.py")

    banner("Setup complete! You can now run scrapers:")
    print("  python scrapers/run_rss.py")
    print("  python scrapers/run_general.py")
    print("  python scrapers/run_research.py\n")
