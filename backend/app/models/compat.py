"""Dialect-agnostic SQLAlchemy type helpers.

These helpers use SQLite-compatible base types with PostgreSQL-specific variants.
This avoids import-time coupling to DATABASE_URL and keeps tests/local SQLite usable.
"""

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


JSONB = JSON().with_variant(PG_JSONB, "postgresql")


def ARRAY(item_type):  # noqa: N802
    """Portable array type.

    SQLite stores arrays as JSON lists; PostgreSQL uses native ARRAY.
    """
    return JSON().with_variant(PG_ARRAY(item_type), "postgresql")


def UUID(as_uuid=False):  # noqa: N802
    """Portable UUID type.

    SQLite stores UUIDs as strings; PostgreSQL uses native UUID.
    """
    return String(36).with_variant(PG_UUID(as_uuid=as_uuid), "postgresql")


__all__ = ["JSONB", "ARRAY", "UUID"]
