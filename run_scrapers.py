"""Run general scrapers — delegates to scrapers/run_general.py."""
import asyncio, sys, os

_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, os.path.join(_root, "scraper_platform"))

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from scrapers.run_general import main
from scrapers.refresh_cache import refresh_all

if __name__ == "__main__":
    asyncio.run(main())
    print("\nRefreshing feed cache...")
    asyncio.run(refresh_all())
