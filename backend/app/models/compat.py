"""
Dialect-agnostic column type aliases.

Uses PostgreSQL-native types (JSONB, ARRAY, UUID) when running against Postgres,
falls back to generic SQLAlchemy equivalents for SQLite local dev.
"""
import os
from pathlib import Path

# Load .env early so DATABASE_URL is available before models import
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

_DB_URL = os.environ.get("DATABASE_URL", "")
_IS_SQLITE = _DB_URL.startswith("sqlite")

if _IS_SQLITE:
    from sqlalchemy import JSON as JSONB
    from sqlalchemy import JSON as ARRAY  # store arrays as JSON lists
    from sqlalchemy import String as _Str

    def UUID(as_uuid=False):  # noqa: N802
        return _Str(36)
else:
    from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID  # noqa: F401

__all__ = ["JSONB", "ARRAY", "UUID"]
