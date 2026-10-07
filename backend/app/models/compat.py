"""Types matching the shipped Alembic schema on PostgreSQL and SQLite."""
from sqlalchemy import JSON, String

JSONB = JSON

def ARRAY(item_type):
    """Store list fields as JSON, as the existing migrations do."""
    return JSON()

def UUID(as_uuid=False):
    """Keep UUID-like identifiers as strings, matching migrated foreign keys."""
    return String(36)

__all__ = ["JSONB", "ARRAY", "UUID"]
