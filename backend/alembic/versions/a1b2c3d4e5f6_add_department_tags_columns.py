"""add department_tags to sources and raw_content

Revision ID: a1b2c3d4e5f6
Revises: 779d1e6be265
Create Date: 2026-03-01 10:35:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '779d1e6be265'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Add department_tags to sources if missing
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='sources' AND column_name='department_tags'"
    ))
    if result.fetchone() is None:
        op.add_column('sources', sa.Column(
            'department_tags', sa.JSON(), server_default='{}',
            nullable=False
        ))

    # Add department_tags to raw_content if missing
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='raw_content' AND column_name='department_tags'"
    ))
    if result.fetchone() is None:
        op.add_column('raw_content', sa.Column(
            'department_tags', sa.JSON(), server_default='{}',
            nullable=False
        ))


def downgrade() -> None:
    op.drop_column('raw_content', 'department_tags')
    op.drop_column('sources', 'department_tags')
