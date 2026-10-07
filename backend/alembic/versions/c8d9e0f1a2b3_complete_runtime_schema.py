"""Add missing user department key and persistent feed cache.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
"""
from alembic import op
import sqlalchemy as sa
revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "department_key" not in {c["name"] for c in inspector.get_columns("users")}:
        op.add_column("users", sa.Column("department_key", sa.String(10), nullable=True))
        op.create_index("ix_users_department_key", "users", ["department_key"])
    if "cached_feeds" not in inspector.get_table_names():
        op.create_table("cached_feeds",
            sa.Column("department", sa.String(20), primary_key=True),
            sa.Column("data", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

def downgrade():
    op.drop_table("cached_feeds")
    op.drop_index("ix_users_department_key", table_name="users")
    op.drop_column("users", "department_key")
