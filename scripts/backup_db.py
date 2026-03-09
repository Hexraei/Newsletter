#!/usr/bin/env python3
"""Backup the local SQLite database.

Usage:
    python scripts/backup_db.py              # Backup to backups/ directory
    python scripts/backup_db.py --output /path/to/backup.db
"""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "newsletter.db"
BACKUP_DIR = Path(__file__).parent.parent / "backups"


def backup(output_path=None):
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return False

    if output_path is None:
        BACKUP_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = BACKUP_DIR / f"newsletter_{timestamp}.db"

    # Use SQLite's backup API for consistency
    src = sqlite3.connect(str(DB_PATH))
    dst = sqlite3.connect(str(output_path))
    src.backup(dst)
    dst.close()
    src.close()

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Backup created: {output_path} ({size_mb:.1f} MB)")

    # Keep only last 10 backups
    if BACKUP_DIR.exists():
        backups = sorted(BACKUP_DIR.glob("newsletter_*.db"), reverse=True)
        for old in backups[10:]:
            old.unlink()
            print(f"Removed old backup: {old.name}")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup newsletter database")
    parser.add_argument("--output", "-o", help="Output path for backup file")
    args = parser.parse_args()
    backup(args.output)
