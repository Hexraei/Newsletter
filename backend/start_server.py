#!/usr/bin/env python
"""Start the newsletter backend server."""

import sys
import os

# Add paths
sys.path.insert(0, r'D:\newsletter\backend')
sys.path.insert(0, r'D:\newsletter\scraper_platform')

# Set environment variables (fallback if .env not loaded)
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://postgres:newsletter123@localhost:5432/newsletter')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('SECRET_KEY', 'dev-secret-key-change-in-production')

import uvicorn

if __name__ == "__main__":
    print("="*60)
    print("🎓 COLLEGE NEWSLETTER PLATFORM")
    print("="*60)
    print("\nStarting server...")
    print("API Docs: http://localhost:8000/docs")
    print("Reader UI: http://localhost:8000/static/reader.html")
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
