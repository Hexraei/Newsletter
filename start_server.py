#!/usr/bin/env python
"""Start the newsletter backend server."""

import sys
import os

# Add paths
_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_root, 'backend'))
sys.path.insert(0, os.path.join(_root, 'scraper_platform'))

# Load .env from backend/ so pydantic Settings picks up DATABASE_URL etc.
from dotenv import load_dotenv
load_dotenv(os.path.join(_root, 'backend', '.env'))

os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
import uvicorn

if __name__ == "__main__":
    print("="*60)
    print("COLLEGE NEWSLETTER PLATFORM")
    print("="*60)
    print("\nStarting server...")
    print("API Docs: http://localhost:8000/docs")
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.environ.get("DEBUG", "false").lower() == "true",
        log_level="info"
    )
