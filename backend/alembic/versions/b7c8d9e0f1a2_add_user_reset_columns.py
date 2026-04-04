"""add reset token columns to users

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-03-31 14:35:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='reset_token'"
    ))
    if result.fetchone() is None:
        op.add_column("users", sa.Column("reset_token", sa.String(length=128), nullable=True))

    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='reset_token_expiry'"
    ))
    if result.fetchone() is None:
        op.add_column("users", sa.Column("reset_token_expiry", sa.DateTime(timezone=True), nullable=True))

    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes "
        "WHERE tablename='users' AND indexname='ix_users_reset_token'"
    ))
    if result.fetchone() is None:
        op.create_index("ix_users_reset_token", "users", ["reset_token"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_reset_token", table_name="users")
    op.drop_column("users", "reset_token_expiry")
    op.drop_column("users", "reset_token")
