#!/usr/bin/env python
"""Seed sources — delegates to scrapers/seed_sources.py."""
import asyncio, sys, os

_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from scrapers.seed_sources import seed

if __name__ == "__main__":
    asyncio.run(seed())
